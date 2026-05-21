from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.interview import Interview, Scenario
from app.models.user import User, UserRole
from app.schemas.interview import InterviewCreateRequest, InterviewRead
from app.schemas.scenario import ScenarioRead
from app.services.scenario_generator import ScenarioGenerationResult, ScenarioGenerator

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_scenario_generator() -> ScenarioGenerator:
    return ScenarioGenerator()


def _organization_ids_for(user: User) -> list[UUID]:
    return [membership.organization_id for membership in user.memberships]


def _primary_organization_id(user: User) -> UUID:
    organization_ids = _organization_ids_for(user)
    if not organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not attached to an organization.",
        )
    return organization_ids[0]


def _get_interview_for_user(db: Session, interview_id: UUID, user: User) -> Interview:
    organization_ids = _organization_ids_for(user)
    if not organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not attached to an organization.",
        )

    try:
        interview = db.execute(
            select(Interview)
            .options(selectinload(Interview.scenario))
            .where(Interview.id == interview_id, Interview.organization_id.in_(organization_ids))
        ).scalar_one_or_none()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load interview.",
        ) from exc
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview was not found.")
    return interview


def _raise_schema_not_ready(exc: ProgrammingError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Interview database tables are not available. Run Alembic migrations with `alembic upgrade head`.",
    ) from exc


@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: InterviewCreateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRead:
    interview = Interview(
        organization_id=_primary_organization_id(current_user),
        created_by_id=current_user.id,
        role_title=payload.role_title,
        seniority=payload.seniority,
        stack=payload.stack,
        difficulty=payload.difficulty,
        interview_type=payload.interview_type,
        duration_minutes=payload.duration_minutes,
        allowed_ai_mode=payload.allowed_ai_mode,
        evaluation_criteria=payload.evaluation_criteria,
        status="DRAFT",
    )
    db.add(interview)
    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create interview.")
    db.refresh(interview)
    return InterviewRead.model_validate(interview)


@router.get("", response_model=list[InterviewRead])
def list_interviews(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> list[InterviewRead]:
    organization_ids = _organization_ids_for(current_user)
    if not organization_ids:
        return []

    try:
        interviews = db.execute(
            select(Interview)
            .options(selectinload(Interview.scenario))
            .where(Interview.organization_id.in_(organization_ids))
            .order_by(Interview.created_at.desc())
        ).scalars()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load interviews.",
        ) from exc
    return [InterviewRead.model_validate(interview) for interview in interviews]


@router.get("/{interview_id}", response_model=InterviewRead)
def get_interview(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRead:
    return InterviewRead.model_validate(_get_interview_for_user(db, interview_id, current_user))


@router.post("/{interview_id}/generate-scenario", response_model=ScenarioRead)
def generate_scenario(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
    generator: Annotated[ScenarioGenerator, Depends(get_scenario_generator)],
) -> ScenarioRead:
    interview = _get_interview_for_user(db, interview_id, current_user)
    result: ScenarioGenerationResult = generator.generate(interview)

    if interview.scenario is None:
        scenario = Scenario(interview_id=interview.id)
        db.add(scenario)
    else:
        scenario = interview.scenario

    scenario.title = result.scenario.title
    scenario.business_context = result.scenario.business_context
    scenario.technical_requirements = result.scenario.technical_requirements
    scenario.starter_code = result.scenario.starter_code
    scenario.expected_behavior = result.scenario.expected_behavior
    scenario.logs_or_bug_report = result.scenario.logs_or_bug_report
    scenario.hidden_evaluation_points = result.scenario.hidden_evaluation_points
    scenario.candidate_instructions = result.scenario.candidate_instructions
    scenario.interviewer_rubric = result.scenario.interviewer_rubric
    scenario.generation_source = result.source
    scenario.ai_model = result.model
    interview.status = "READY"

    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to store scenario.")
    db.refresh(scenario)
    return ScenarioRead.model_validate(scenario)

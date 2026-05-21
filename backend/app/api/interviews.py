from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.interview import Interview, InterviewSession, InterviewSessionStatus, InviteToken, Scenario
from app.models.organization import OrganizationMember
from app.models.user import User, UserRole
from app.schemas.invite import InviteCreateRequest, InviteTokenRead
from app.schemas.interview import InterviewCreateRequest, InterviewRead
from app.schemas.scenario import ScenarioRead
from app.services.invites import generate_invite_token, hash_invite_token
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


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _invite_url(raw_token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/invite/{raw_token}"


def _get_candidate_for_invite(db: Session, *, organization_id: UUID, candidate_email: str) -> User:
    candidate = db.execute(
        select(User)
        .join(OrganizationMember)
        .where(
            User.email == candidate_email,
            User.role == UserRole.CANDIDATE,
            User.is_active.is_(True),
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == UserRole.CANDIDATE,
        )
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active candidate account with that email exists in this organization.",
        )
    return candidate


def _get_or_create_invited_session(db: Session, *, interview: Interview, candidate: User) -> InterviewSession:
    session = db.execute(
        select(InterviewSession).where(
            InterviewSession.interview_id == interview.id,
            InterviewSession.candidate_id == candidate.id,
        )
    ).scalar_one_or_none()
    if session is None:
        session = InterviewSession(
            organization_id=interview.organization_id,
            interview_id=interview.id,
            candidate_id=candidate.id,
            status=InterviewSessionStatus.INVITED,
        )
        db.add(session)
        db.flush()
        return session

    if session.status != InterviewSessionStatus.INVITED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This candidate already has an active or completed session for the interview.",
        )
    return session


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


@router.post("/{interview_id}/invite", response_model=InviteTokenRead, status_code=status.HTTP_201_CREATED)
def create_candidate_invite(
    interview_id: UUID,
    payload: InviteCreateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InviteTokenRead:
    interview = _get_interview_for_user(db, interview_id, current_user)
    candidate_email = _normalize_email(payload.candidate_email)
    candidate = _get_candidate_for_invite(db, organization_id=interview.organization_id, candidate_email=candidate_email)
    session = _get_or_create_invited_session(db, interview=interview, candidate=candidate)
    raw_token = generate_invite_token()
    invite = InviteToken(
        organization_id=interview.organization_id,
        interview_id=interview.id,
        session_id=session.id,
        candidate_id=candidate.id,
        created_by_id=current_user.id,
        token_hash=hash_invite_token(raw_token),
        candidate_email=candidate_email,
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
    )
    db.add(invite)

    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create invite.",
        ) from exc

    db.refresh(invite)
    return InviteTokenRead(
        id=invite.id,
        interview_id=invite.interview_id,
        session_id=invite.session_id,
        candidate_email=invite.candidate_email,
        invite_url=_invite_url(raw_token),
        expires_at=invite.expires_at,
        used_at=invite.used_at,
    )


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

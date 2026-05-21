from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.interview import Interview, Scenario
from app.models.user import User, UserRole
from app.schemas.interview import InterviewCreate, InterviewListResponse, InterviewRead, InterviewUpdate

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _current_org_ids(current_user: User) -> set[UUID]:
    return {membership.organization_id for membership in current_user.memberships}


def _resolve_create_organization_id(current_user: User, organization_id: UUID | None) -> UUID:
    organization_ids = _current_org_ids(current_user)
    if not organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to an organization before creating interviews.",
        )

    if organization_id is None:
        if len(organization_ids) == 1:
            return next(iter(organization_ids))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="organization_id is required when the user belongs to multiple organizations.",
        )

    if organization_id not in organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot create interviews for this organization.",
        )
    return organization_id


def _interview_options() -> tuple:
    return (
        selectinload(Interview.organization),
        selectinload(Interview.created_by),
        selectinload(Interview.scenarios),
        selectinload(Interview.sessions),
    )


def _scoped_interview_query(current_user: User) -> Select[tuple[Interview]]:
    organization_ids = _current_org_ids(current_user)
    return select(Interview).options(*_interview_options()).where(Interview.organization_id.in_(organization_ids))


def _get_scoped_interview(db: Session, current_user: User, interview_id: UUID) -> Interview:
    interview = db.execute(_scoped_interview_query(current_user).where(Interview.id == interview_id)).scalar_one_or_none()
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview was not found.")
    return interview


def _serialize_interview(interview: Interview) -> InterviewRead:
    return InterviewRead(
        id=interview.id,
        organization=interview.organization,
        created_by=interview.created_by,
        title=interview.title,
        role_title=interview.role_title,
        seniority=interview.seniority,
        stack=interview.stack,
        interview_type=interview.interview_type,
        difficulty=interview.difficulty,
        duration_minutes=interview.duration_minutes,
        ai_mode=interview.ai_mode,
        status=interview.status,
        scenarios=list(interview.scenarios),
        session_count=len(interview.sessions),
        created_at=interview.created_at,
        updated_at=interview.updated_at,
    )


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewListResponse:
    organization_ids = _current_org_ids(current_user)
    if not organization_ids:
        return InterviewListResponse(interviews=[])

    interviews = db.execute(_scoped_interview_query(current_user).order_by(Interview.updated_at.desc())).scalars().all()
    return InterviewListResponse(interviews=[_serialize_interview(interview) for interview in interviews])


@router.post("", response_model=InterviewRead, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: InterviewCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRead:
    organization_id = _resolve_create_organization_id(current_user, payload.organization_id)
    interview = Interview(
        organization_id=organization_id,
        created_by_user_id=current_user.id,
        title=payload.title,
        role_title=payload.role_title,
        seniority=payload.seniority,
        stack=payload.stack,
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        duration_minutes=payload.duration_minutes,
        ai_mode=payload.ai_mode,
    )
    scenario = Scenario(
        interview=interview,
        created_by_user_id=current_user.id,
        title=payload.scenario.title,
        business_context=payload.scenario.business_context,
        candidate_instructions=payload.scenario.candidate_instructions,
        technical_requirements=payload.scenario.technical_requirements,
        evaluation_rubric=payload.scenario.evaluation_rubric,
    )
    db.add_all([interview, scenario])
    db.commit()

    return _serialize_interview(_get_scoped_interview(db, current_user, interview.id))


@router.get("/{interview_id}", response_model=InterviewRead)
def get_interview(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRead:
    return _serialize_interview(_get_scoped_interview(db, current_user, interview_id))


@router.patch("/{interview_id}", response_model=InterviewRead)
def update_interview(
    interview_id: UUID,
    payload: InterviewUpdate,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewRead:
    interview = _get_scoped_interview(db, current_user, interview_id)
    update_data = payload.model_dump(exclude_unset=True, exclude={"scenario"})
    for field_name, value in update_data.items():
        setattr(interview, field_name, value)

    if payload.scenario is not None:
        scenario_data = payload.scenario.model_dump(exclude_unset=True)
        scenario = interview.scenarios[0] if interview.scenarios else None
        if scenario is None:
            required_fields = {"title", "business_context", "candidate_instructions", "technical_requirements", "evaluation_rubric"}
            if required_fields - set(scenario_data):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A full scenario is required when the interview does not already have one.",
                )
            scenario = Scenario(interview=interview, created_by_user_id=current_user.id, **scenario_data)
            db.add(scenario)
        else:
            for field_name, value in scenario_data.items():
                setattr(scenario, field_name, value)

    db.commit()
    return _serialize_interview(_get_scoped_interview(db, current_user, interview.id))


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    interview = _get_scoped_interview(db, current_user, interview_id)
    db.delete(interview)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

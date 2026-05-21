from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.interview import Interview, InterviewSession, InterviewSessionStatus, InviteToken
from app.models.user import User, UserRole
from app.schemas.invite import (
    CandidateScenarioRead,
    CandidateSessionInterviewRead,
    InterviewSessionRead,
    InviteInterviewRead,
    PublicInviteRead,
)
from app.services.invites import hash_invite_token

router = APIRouter(prefix="/api", tags=["candidate"])


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= _now_utc()


def _get_invite_by_token(db: Session, raw_token: str) -> InviteToken:
    invite = db.execute(
        select(InviteToken)
        .options(
            selectinload(InviteToken.interview).selectinload(Interview.scenario),
            selectinload(InviteToken.session),
        )
        .where(InviteToken.token_hash == hash_invite_token(raw_token))
    ).scalar_one_or_none()
    if invite is None or invite.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite was not found.")
    if _is_expired(invite.expires_at):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite has expired.")
    return invite


def _public_invite_response(invite: InviteToken) -> PublicInviteRead:
    interview = invite.interview
    return PublicInviteRead(
        interview=InviteInterviewRead(
            id=interview.id,
            role_title=interview.role_title,
            seniority=interview.seniority,
            stack=interview.stack,
            difficulty=interview.difficulty,
            interview_type=interview.interview_type,
            duration_minutes=interview.duration_minutes,
            allowed_ai_mode=interview.allowed_ai_mode,
            scenario_title=interview.scenario.title if interview.scenario else None,
        ),
        candidate_email=invite.candidate_email,
        expires_at=invite.expires_at,
        status=invite.session.status,
    )


def _session_response(session: InterviewSession) -> InterviewSessionRead:
    interview = session.interview
    if interview.scenario is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview scenario has not been generated yet.",
        )

    return InterviewSessionRead(
        id=session.id,
        interview_id=session.interview_id,
        candidate_id=session.candidate_id,
        status=session.status,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        reviewed_at=session.reviewed_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        interview=CandidateSessionInterviewRead.model_validate(interview),
        scenario=CandidateScenarioRead.model_validate(interview.scenario),
    )


@router.get("/invite/{token}", response_model=PublicInviteRead)
def get_invite(token: str, db: Annotated[Session, Depends(get_db)]) -> PublicInviteRead:
    return _public_invite_response(_get_invite_by_token(db, token))


@router.post("/invite/{token}/start", response_model=InterviewSessionRead)
def start_session_from_invite(
    token: str,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewSessionRead:
    invite = _get_invite_by_token(db, token)
    if current_user.id != invite.candidate_id or current_user.email != invite.candidate_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invite belongs to a different candidate.",
        )
    if invite.interview.scenario is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview scenario has not been generated yet.",
        )
    if invite.session.status in {InterviewSessionStatus.SUBMITTED, InterviewSessionStatus.REVIEWED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview session has already been submitted.",
        )

    if invite.session.status == InterviewSessionStatus.INVITED:
        invite.session.status = InterviewSessionStatus.STARTED
        invite.session.started_at = _now_utc()
        invite.used_at = invite.used_at or _now_utc()

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to start interview session.",
        ) from exc

    db.refresh(invite.session)
    session = db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.interview).selectinload(Interview.scenario))
        .where(InterviewSession.id == invite.session_id)
    ).scalar_one()
    return _session_response(session)


@router.get("/sessions/{session_id}", response_model=InterviewSessionRead)
def get_candidate_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewSessionRead:
    session = db.execute(
        select(InterviewSession)
        .options(selectinload(InterviewSession.interview).selectinload(Interview.scenario))
        .where(
            InterviewSession.id == session_id,
            InterviewSession.candidate_id == current_user.id,
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session was not found.")
    return _session_response(session)

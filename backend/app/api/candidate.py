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
from app.models.interview import (
    AIMessage,
    AIMessageRole,
    Interview,
    InterviewSession,
    InterviewSessionStatus,
    InviteToken,
    Submission,
    TelemetryEvent,
    TelemetryEventType,
)
from app.models.user import User, UserRole
from app.schemas.invite import (
    AICopilotRequest,
    AICopilotResponse,
    AIMessageRead,
    CandidateScenarioRead,
    CandidateSessionInterviewRead,
    InterviewSessionRead,
    InviteInterviewRead,
    PublicInviteRead,
    SubmissionCreate,
    SubmissionRead,
    TelemetryEventCreate,
    TelemetryEventRead,
    TestCaseResult,
    TestRunRequest,
    TestRunResult,
)
from app.services.copilot import CandidateCopilot
from app.services.invites import hash_invite_token

router = APIRouter(prefix="/api", tags=["candidate"])


def get_candidate_copilot() -> CandidateCopilot:
    return CandidateCopilot()


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
    _ensure_scenario_ready(session)

    return InterviewSessionRead(
        id=session.id,
        interview_id=session.interview_id,
        candidate_id=session.candidate_id,
        status=session.status,
        started_at=session.started_at,
        submitted_at=session.submitted_at,
        reviewed_at=session.reviewed_at,
        latest_code=session.latest_code,
        notes=session.notes,
        last_autosaved_at=session.last_autosaved_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        interview=CandidateSessionInterviewRead.model_validate(interview),
        scenario=CandidateScenarioRead.model_validate(interview.scenario),
        submission=SubmissionRead.model_validate(session.submission) if session.submission else None,
        ai_messages=[
            AIMessageRead.model_validate(message)
            for message in sorted(session.ai_messages, key=lambda message: message.created_at)
        ],
    )


def _ensure_scenario_ready(session: InterviewSession) -> None:
    if session.interview.scenario is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview scenario has not been generated yet.",
        )


def _get_candidate_session_for_user(db: Session, *, session_id: UUID, current_user: User) -> InterviewSession:
    session = db.execute(
        select(InterviewSession)
        .options(
            selectinload(InterviewSession.interview).selectinload(Interview.scenario),
            selectinload(InterviewSession.submission),
            selectinload(InterviewSession.ai_messages),
        )
        .where(
            InterviewSession.id == session_id,
            InterviewSession.candidate_id == current_user.id,
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session was not found.")
    _ensure_scenario_ready(session)
    return session


def _ensure_session_accepts_work(session: InterviewSession) -> None:
    if session.status in {InterviewSessionStatus.SUBMITTED, InterviewSessionStatus.REVIEWED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This interview session is no longer accepting candidate changes.",
        )


def _create_event(
    db: Session,
    *,
    session: InterviewSession,
    event_type: TelemetryEventType,
    payload: dict[str, object],
) -> TelemetryEvent:
    event = TelemetryEvent(
        organization_id=session.organization_id,
        session_id=session.id,
        candidate_id=session.candidate_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    return event


def _payload_string(payload: dict[str, object], key: str, *, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"`{key}` must be a string.")
    if len(value) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"`{key}` must be {max_length} characters or fewer.",
        )
    return value


def _test_keywords(session: InterviewSession) -> list[str]:
    scenario = session.interview.scenario
    if scenario is None:
        return []
    source_text = " ".join(
        [
            scenario.title,
            scenario.business_context,
            " ".join(scenario.technical_requirements),
            " ".join(scenario.expected_behavior),
            scenario.logs_or_bug_report,
        ]
    )
    stopwords = {"about", "after", "being", "candidate", "should", "their", "there", "these", "where", "which", "with"}
    keywords: list[str] = []
    for raw_token in source_text.lower().split():
        token = "".join(character for character in raw_token if character.isalnum())
        if len(token) < 5 or token in stopwords or token in keywords:
            continue
        keywords.append(token)
        if len(keywords) == 12:
            break
    return keywords


def _simulate_test_run(session: InterviewSession, code: str) -> TestRunResult:
    stripped_code = code.strip()
    lowered_code = stripped_code.lower()
    keywords = _test_keywords(session)
    matching_keywords = [keyword for keyword in keywords if keyword in lowered_code]
    has_error_handling = any(marker in lowered_code for marker in ("try", "except", "catch", "raise", "throw", "error"))
    has_executable_shape = any(marker in lowered_code for marker in ("def ", "function ", "class ", "return ", "=>"))

    cases = [
        TestCaseResult(
            name="solution-not-empty",
            status="passed" if stripped_code else "failed",
            details="Code snapshot contains candidate changes." if stripped_code else "No code was provided.",
        ),
        TestCaseResult(
            name="task-context-addressed",
            status="passed" if matching_keywords else "failed",
            details=(
                f"References task concepts: {', '.join(matching_keywords[:4])}."
                if matching_keywords
                else "No task-specific terms were detected in the solution."
            ),
        ),
        TestCaseResult(
            name="implementation-shape",
            status="passed" if has_executable_shape else "failed",
            details=(
                "Implementation contains executable structure."
                if has_executable_shape
                else "Add concrete code structure such as a function, class, or return path."
            ),
        ),
        TestCaseResult(
            name="failure-path-awareness",
            status="passed" if has_error_handling else "failed",
            details=(
                "Solution appears to consider failure or error paths."
                if has_error_handling
                else "Consider how errors, retries, or invalid input should be handled."
            ),
        ),
    ]
    passed_count = sum(1 for case in cases if case.status == "passed")
    run_status = "passed" if passed_count == len(cases) else "failed"
    output = f"{passed_count}/{len(cases)} simulated checks passed."
    return TestRunResult(status=run_status, output=output, cases=cases)


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
        invite.session.latest_code = invite.session.latest_code or invite.interview.scenario.starter_code
        invite.session.last_autosaved_at = invite.session.last_autosaved_at or _now_utc()
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
    session = _get_candidate_session_for_user(db, session_id=invite.session_id, current_user=current_user)
    return _session_response(session)


@router.get("/sessions/{session_id}", response_model=InterviewSessionRead)
def get_candidate_session(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> InterviewSessionRead:
    return _session_response(_get_candidate_session_for_user(db, session_id=session_id, current_user=current_user))


@router.post("/sessions/{session_id}/events", response_model=TelemetryEventRead, status_code=status.HTTP_201_CREATED)
def save_session_event(
    session_id: UUID,
    payload: TelemetryEventCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> TelemetryEventRead:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    event_payload: dict[str, object] = dict(payload.payload)
    now = _now_utc()

    if payload.event_type == TelemetryEventType.SESSION_STARTED:
        if session.status == InterviewSessionStatus.INVITED:
            session.status = InterviewSessionStatus.STARTED
            session.started_at = now
        session.latest_code = session.latest_code or session.interview.scenario.starter_code
        session.last_autosaved_at = session.last_autosaved_at or now
        event_payload = {"status": session.status.value}
    elif payload.event_type == TelemetryEventType.CODE_EDIT:
        _ensure_session_accepts_work(session)
        code = _payload_string(event_payload, "code", max_length=200000)
        session.latest_code = code
        session.last_autosaved_at = now
        event_payload = {"code_length": len(code), "autosaved_at": now.isoformat()}
    elif payload.event_type == TelemetryEventType.NOTE_UPDATED:
        _ensure_session_accepts_work(session)
        notes = _payload_string(event_payload, "notes", max_length=10000)
        session.notes = notes
        session.last_autosaved_at = now
        event_payload = {"note_length": len(notes), "autosaved_at": now.isoformat()}
    elif payload.event_type in {TelemetryEventType.TEST_RUN, TelemetryEventType.SUBMISSION_CREATED}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use the dedicated test run or submit endpoint for this event type.",
        )

    event = _create_event(db, session=session, event_type=payload.event_type, payload=event_payload)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to save event.") from exc

    db.refresh(event)
    return TelemetryEventRead.model_validate(event)


@router.post("/sessions/{session_id}/run-tests", response_model=TestRunResult)
def run_session_tests(
    session_id: UUID,
    payload: TestRunRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> TestRunResult:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    _ensure_session_accepts_work(session)
    code = payload.code if payload.code is not None else session.latest_code or session.interview.scenario.starter_code
    result = _simulate_test_run(session, code)
    now = _now_utc()

    session.latest_code = code
    session.last_autosaved_at = now
    _create_event(
        db,
        session=session,
        event_type=TelemetryEventType.TEST_RUN,
        payload={
            "status": result.status,
            "output": result.output,
            "code_length": len(code),
            "case_count": len(result.cases),
        },
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to run tests.") from exc

    return result


@router.post("/sessions/{session_id}/submit", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def submit_session_solution(
    session_id: UUID,
    payload: SubmissionCreate,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> SubmissionRead:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    _ensure_session_accepts_work(session)
    now = _now_utc()
    submission = Submission(
        organization_id=session.organization_id,
        session_id=session.id,
        candidate_id=session.candidate_id,
        code=payload.code,
        notes=payload.notes,
        test_output=payload.test_output,
        submitted_at=now,
    )
    db.add(submission)

    session.latest_code = payload.code
    session.notes = payload.notes
    session.last_autosaved_at = now
    session.status = InterviewSessionStatus.SUBMITTED
    session.submitted_at = now

    try:
        db.flush()
        _create_event(
            db,
            session=session,
            event_type=TelemetryEventType.SUBMISSION_CREATED,
            payload={
                "submission_id": str(submission.id),
                "code_length": len(payload.code),
                "note_length": len(payload.notes),
            },
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to submit final solution.",
        ) from exc

    db.refresh(submission)
    return SubmissionRead.model_validate(submission)


@router.post("/sessions/{session_id}/ai", response_model=AICopilotResponse, status_code=status.HTTP_201_CREATED)
def ask_candidate_copilot(
    session_id: UUID,
    payload: AICopilotRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
    copilot: Annotated[CandidateCopilot, Depends(get_candidate_copilot)],
) -> AICopilotResponse:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    previous_messages = list(
        db.execute(
            select(AIMessage)
            .where(AIMessage.session_id == session.id)
            .order_by(AIMessage.created_at.asc())
        ).scalars()
    )
    code_snapshot = payload.code or session.latest_code or session.interview.scenario.starter_code
    ai_mode = session.interview.allowed_ai_mode

    user_message = AIMessage(
        organization_id=session.organization_id,
        session_id=session.id,
        candidate_id=session.candidate_id,
        role=AIMessageRole.USER,
        content=payload.question,
        code_snapshot=code_snapshot,
        ai_mode=ai_mode,
        ai_model=None,
        message_metadata={},
    )
    db.add(user_message)

    result = copilot.generate_reply(
        session=session,
        question=payload.question,
        code=code_snapshot,
        previous_messages=previous_messages,
    )
    assistant_message = AIMessage(
        organization_id=session.organization_id,
        session_id=session.id,
        candidate_id=session.candidate_id,
        role=AIMessageRole.ASSISTANT,
        content=result.content,
        code_snapshot=None,
        ai_mode=ai_mode,
        ai_model=result.model,
        message_metadata={"source": result.source},
    )
    db.add(assistant_message)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save AI copilot exchange.",
        ) from exc

    db.refresh(user_message)
    db.refresh(assistant_message)
    return AICopilotResponse(
        user_message=AIMessageRead.model_validate(user_message),
        assistant_message=AIMessageRead.model_validate(assistant_message),
    )

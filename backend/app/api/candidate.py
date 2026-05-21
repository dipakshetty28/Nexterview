from __future__ import annotations

import json
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
    ProjectFile,
    Scenario,
    ScenarioProject,
    SessionFileSnapshot,
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
from app.schemas.project import (
    CandidateProjectFileRead,
    CandidateScenarioProjectRead,
    CandidateWorkspaceFileRead,
    CandidateWorkspaceFileUpdate,
    CandidateWorkspaceProjectRead,
    CandidateWorkspaceRead,
)
from app.services.copilot import CandidateCopilot
from app.services.invites import hash_invite_token
from app.services.scenario_projects import ensure_session_file_snapshots

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
            selectinload(InviteToken.interview)
            .selectinload(Interview.scenario)
            .selectinload(Scenario.project)
            .selectinload(ScenarioProject.files),
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
        scenario=_candidate_scenario_response(interview.scenario),
        submission=SubmissionRead.model_validate(session.submission) if session.submission else None,
        ai_messages=[
            AIMessageRead.model_validate(message)
            for message in sorted(session.ai_messages, key=lambda message: message.created_at)
        ],
    )


def _candidate_scenario_response(scenario: Scenario | None) -> CandidateScenarioRead:
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interview scenario has not been generated yet.",
        )

    project = None
    if scenario.project is not None:
        visible_files = [
            CandidateProjectFileRead.model_validate(project_file)
            for project_file in sorted(scenario.project.files, key=lambda project_file: project_file.path)
            if not project_file.is_hidden
        ]
        project = CandidateScenarioProjectRead(
            project_name=scenario.project.project_name,
            stack=scenario.project.stack,
            framework=scenario.project.framework,
            package_manager=scenario.project.package_manager,
            install_command=scenario.project.install_command,
            run_command=scenario.project.run_command,
            test_command=scenario.project.test_command,
            entrypoint=scenario.project.entrypoint,
            files=visible_files,
        )

    return CandidateScenarioRead(
        id=scenario.id,
        title=scenario.title,
        business_context=scenario.business_context,
        technical_requirements=scenario.technical_requirements,
        starter_code=scenario.starter_code,
        expected_behavior=scenario.expected_behavior,
        logs_or_bug_report=scenario.logs_or_bug_report,
        bug_description=scenario.bug_description,
        feature_request=scenario.feature_request,
        validation_instructions=scenario.validation_instructions,
        candidate_task_summary=scenario.candidate_task_summary,
        candidate_instructions=scenario.candidate_instructions,
        project=project,
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
            selectinload(InterviewSession.interview)
            .selectinload(Interview.scenario)
            .selectinload(Scenario.project)
            .selectinload(ScenarioProject.files),
            selectinload(InterviewSession.submission),
            selectinload(InterviewSession.ai_messages),
            selectinload(InterviewSession.file_snapshots).selectinload(SessionFileSnapshot.project_file),
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


def _submitted_files_from_session_snapshots(db: Session, *, session: InterviewSession) -> list[dict[str, object]]:
    snapshots = db.execute(
        select(SessionFileSnapshot)
        .join(ProjectFile, SessionFileSnapshot.project_file_id == ProjectFile.id)
        .where(SessionFileSnapshot.session_id == session.id)
        .where(ProjectFile.is_hidden.is_(False))
        .order_by(SessionFileSnapshot.path.asc())
    ).scalars()
    return [
        {
            "path": snapshot.path,
            "content": snapshot.current_content,
            "language": snapshot.language,
        }
        for snapshot in snapshots
    ]


def _visible_session_snapshots(db: Session, *, session: InterviewSession) -> list[SessionFileSnapshot]:
    ensure_session_file_snapshots(db, session=session)
    return list(
        db.execute(
            select(SessionFileSnapshot)
            .join(ProjectFile, SessionFileSnapshot.project_file_id == ProjectFile.id)
            .options(selectinload(SessionFileSnapshot.project_file))
            .where(SessionFileSnapshot.session_id == session.id)
            .where(ProjectFile.is_hidden.is_(False))
            .order_by(SessionFileSnapshot.path.asc())
        ).scalars()
    )


def _workspace_file_response(snapshot: SessionFileSnapshot) -> CandidateWorkspaceFileRead:
    project_file = snapshot.project_file
    return CandidateWorkspaceFileRead(
        id=snapshot.id,
        project_file_id=snapshot.project_file_id,
        path=snapshot.path,
        original_content=snapshot.original_content,
        current_content=snapshot.current_content,
        language=snapshot.language,
        file_type=project_file.file_type,
        is_editable=project_file.is_editable,
        updated_at=snapshot.updated_at,
    )


def _workspace_response(db: Session, *, session: InterviewSession) -> CandidateWorkspaceRead:
    scenario = session.interview.scenario
    if scenario is None or scenario.project is None:
        return CandidateWorkspaceRead(
            session_id=session.id,
            project=None,
            files=[],
            last_autosaved_at=session.last_autosaved_at,
        )

    snapshots = _visible_session_snapshots(db, session=session)
    return CandidateWorkspaceRead(
        session_id=session.id,
        project=CandidateWorkspaceProjectRead.model_validate(scenario.project),
        files=[_workspace_file_response(snapshot) for snapshot in snapshots],
        last_autosaved_at=session.last_autosaved_at,
    )


def _primary_code_from_snapshots(db: Session, *, session: InterviewSession) -> str:
    snapshots = _visible_session_snapshots(db, session=session)
    if not snapshots:
        return session.latest_code or session.interview.scenario.starter_code

    entrypoint = session.interview.scenario.project.entrypoint if session.interview.scenario.project else None
    for snapshot in snapshots:
        if entrypoint and snapshot.path == entrypoint:
            return snapshot.current_content
    for snapshot in snapshots:
        if snapshot.project_file.file_type == "source":
            return snapshot.current_content
    return snapshots[0].current_content


def _workspace_code_context(db: Session, *, session: InterviewSession, fallback_code: str) -> str:
    snapshots = _visible_session_snapshots(db, session=session)
    if not snapshots:
        return fallback_code

    parts: list[str] = []
    for snapshot in snapshots:
        parts.append(f"// File: {snapshot.path}\n{snapshot.current_content}")
    return "\n\n".join(parts)


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
            scenario.bug_description,
            scenario.feature_request,
            scenario.validation_instructions,
            scenario.candidate_task_summary,
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


def _scenario_terms(text: str) -> list[str]:
    stopwords = {
        "about",
        "after",
        "because",
        "candidate",
        "current",
        "should",
        "their",
        "there",
        "these",
        "where",
        "which",
        "without",
    }
    terms: list[str] = []
    for raw_token in text.lower().replace("/", " ").replace("-", " ").split():
        token = "".join(character for character in raw_token if character.isalnum() or character == "_")
        if len(token) < 5 or token in stopwords or token in terms:
            continue
        terms.append(token)
        if len(terms) == 8:
            break
    return terms


def _seed_data_summary(visible_files: list[SessionFileSnapshot]) -> tuple[str | None, int | None, str | None]:
    seed_file = next(
        (
            snapshot
            for snapshot in visible_files
            if snapshot.project_file.file_type == "data" and snapshot.path.lower().endswith(".json")
        ),
        None,
    )
    if seed_file is None:
        return None, None, None

    try:
        parsed = json.loads(seed_file.current_content)
    except json.JSONDecodeError as exc:
        return seed_file.path, None, f"Seed data JSON is invalid: {exc.msg}."

    if isinstance(parsed, list):
        return seed_file.path, len(parsed), None
    if isinstance(parsed, dict):
        return seed_file.path, len(parsed), None
    return seed_file.path, 1, None


def _simulate_workspace_test_run(
    session: InterviewSession,
    snapshots: list[SessionFileSnapshot],
) -> TestRunResult:
    scenario = session.interview.scenario
    project = scenario.project if scenario else None
    visible_files = [snapshot for snapshot in snapshots if not snapshot.project_file.is_hidden]
    changed_files = [snapshot for snapshot in visible_files if snapshot.current_content != snapshot.original_content]
    test_files = [
        snapshot
        for snapshot in visible_files
        if snapshot.project_file.file_type in {"test", "hidden_test"} or "test" in snapshot.path.lower()
    ]
    current_text = "\n\n".join(snapshot.current_content for snapshot in visible_files).lower()
    changed_text = "\n\n".join(snapshot.current_content for snapshot in changed_files).lower()
    bug_terms = _scenario_terms(scenario.bug_description if scenario else "")
    feature_terms = _scenario_terms(scenario.feature_request if scenario else "")
    bug_hits = [term for term in bug_terms if term in changed_text or term in current_text]
    feature_hits = [term for term in feature_terms if term in changed_text or term in current_text]
    seed_path, seed_record_count, seed_error = _seed_data_summary(visible_files)

    quantity_bug_expected = scenario is not None and "quantity" in scenario.bug_description.lower()
    quantity_bug_signal = (
        not quantity_bug_expected
        or ("quantity" in current_text and any(marker in current_text for marker in ("*", "sum(", "reduce(")))
    )
    status_feature_expected = scenario is not None and "status" in scenario.feature_request.lower()
    status_feature_signal = (
        not status_feature_expected
        or (
            "status" in current_text
            and any(marker in current_text for marker in ("filter", "query", "where", "params", "status:"))
        )
    )

    cases = [
        TestCaseResult(
            name="seed-data-loaded",
            status="passed" if seed_path and seed_error is None else "failed",
            details=(
                f"Loaded {seed_record_count} records from `{seed_path}` for deterministic simulation."
                if seed_path and seed_error is None
                else seed_error or "No JSON seed data file was available for this project."
            ),
        ),
        TestCaseResult(
            name="workspace-files-present",
            status="passed" if len(visible_files) >= 2 else "failed",
            details=(
                f"Loaded {len(visible_files)} visible project files from session snapshots."
                if visible_files
                else "No visible project files were available for this session."
            ),
        ),
        TestCaseResult(
            name="candidate-changed-files",
            status="passed" if changed_files else "failed",
            details=(
                f"Detected edits in: {', '.join(snapshot.path for snapshot in changed_files[:5])}."
                if changed_files
                else "No changed files were detected yet."
            ),
        ),
        TestCaseResult(
            name="bug-fix-signal",
            status="passed" if bug_hits or quantity_bug_signal else "failed",
            details=(
                f"Code references bug-related terms: {', '.join(bug_hits[:4])}."
                if bug_hits
                else (
                    "Detected quantity-aware total calculation logic."
                    if quantity_bug_signal
                    else "The changed files do not yet show clear evidence of addressing the described bug."
                )
            ),
        ),
        TestCaseResult(
            name="feature-request-signal",
            status="passed" if feature_hits or status_feature_signal else "failed",
            details=(
                f"Code references feature-related terms: {', '.join(feature_hits[:4])}."
                if feature_hits
                else (
                    "Detected status filtering implementation signals."
                    if status_feature_signal
                    else "The changed files do not yet show clear evidence of the requested feature."
                )
            ),
        ),
        TestCaseResult(
            name="validation-coverage",
            status="passed" if test_files else "failed",
            details=(
                f"Validation files available: {', '.join(snapshot.path for snapshot in test_files[:4])}."
                if test_files
                else "No visible test or validation file exists in the workspace."
            ),
        ),
        TestCaseResult(
            name="runnable-command-known",
            status="passed" if project and project.test_command else "failed",
            details=(
                f"Simulation is based on `{project.test_command}`."
                if project and project.test_command
                else "The project does not define a test command."
            ),
        ),
    ]
    passed_count = sum(1 for case in cases if case.status == "passed")
    run_status = "passed" if passed_count == len(cases) else "failed"
    command = project.test_command if project and project.test_command else "project validation"
    seed_note = f" using `{seed_path}`" if seed_path else ""
    output = f"{passed_count}/{len(cases)} simulated checks passed for `{command}`{seed_note}."
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
    ensure_session_file_snapshots(db, session=invite.session)

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


@router.get("/sessions/{session_id}/workspace", response_model=CandidateWorkspaceRead)
def get_candidate_workspace(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateWorkspaceRead:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    workspace = _workspace_response(db, session=session)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load candidate workspace.",
        ) from exc
    return workspace


@router.put("/sessions/{session_id}/files/{file_id}", response_model=CandidateWorkspaceFileRead)
def update_candidate_workspace_file(
    session_id: UUID,
    file_id: UUID,
    payload: CandidateWorkspaceFileUpdate,
    current_user: Annotated[User, Depends(require_roles(UserRole.CANDIDATE))],
    db: Annotated[Session, Depends(get_db)],
) -> CandidateWorkspaceFileRead:
    session = _get_candidate_session_for_user(db, session_id=session_id, current_user=current_user)
    _ensure_session_accepts_work(session)
    ensure_session_file_snapshots(db, session=session)
    snapshot = db.execute(
        select(SessionFileSnapshot)
        .join(ProjectFile, SessionFileSnapshot.project_file_id == ProjectFile.id)
        .options(selectinload(SessionFileSnapshot.project_file))
        .where(SessionFileSnapshot.id == file_id)
        .where(SessionFileSnapshot.session_id == session.id)
        .where(ProjectFile.is_hidden.is_(False))
    ).scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace file was not found.")
    if not snapshot.project_file.is_editable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This workspace file is read-only.")

    now = _now_utc()
    changed = snapshot.current_content != payload.content
    snapshot.current_content = payload.content
    session.last_autosaved_at = now
    if session.interview.scenario.project and session.interview.scenario.project.entrypoint == snapshot.path:
        session.latest_code = payload.content

    try:
        _create_event(
            db,
            session=session,
            event_type=TelemetryEventType.FILE_EDITED,
            payload={
                "file_id": str(snapshot.id),
                "project_file_id": str(snapshot.project_file_id),
                "path": snapshot.path,
                "content_length": len(payload.content),
                "changed": changed,
            },
        )
        _create_event(
            db,
            session=session,
            event_type=TelemetryEventType.FILE_SAVED,
            payload={
                "file_id": str(snapshot.id),
                "project_file_id": str(snapshot.project_file_id),
                "path": snapshot.path,
                "content_length": len(payload.content),
                "saved_at": now.isoformat(),
            },
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save workspace file.",
        ) from exc

    db.refresh(snapshot)
    return _workspace_file_response(snapshot)


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
        ensure_session_file_snapshots(db, session=session)
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
    elif payload.event_type == TelemetryEventType.FILE_OPENED:
        path = event_payload.get("path")
        event_payload = {
            "file_id": str(event_payload.get("file_id", "")),
            "path": path if isinstance(path, str) else "",
            "opened_at": now.isoformat(),
        }
    elif payload.event_type in {
        TelemetryEventType.FILE_EDITED,
        TelemetryEventType.FILE_SAVED,
        TelemetryEventType.AI_PROMPT_SENT,
    }:
        _ensure_session_accepts_work(session)
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
    visible_snapshots = _visible_session_snapshots(db, session=session)
    if payload.code is not None or not visible_snapshots:
        code = payload.code if payload.code is not None else session.latest_code or session.interview.scenario.starter_code
        result = _simulate_test_run(session, code)
        code_length = len(code)
        changed_file_count = 0
        session.latest_code = code
    else:
        result = _simulate_workspace_test_run(session, visible_snapshots)
        code_length = sum(len(snapshot.current_content) for snapshot in visible_snapshots)
        changed_file_count = sum(
            1 for snapshot in visible_snapshots if snapshot.current_content != snapshot.original_content
        )
        session.latest_code = _primary_code_from_snapshots(db, session=session)
    now = _now_utc()

    session.last_autosaved_at = now
    _create_event(
        db,
        session=session,
        event_type=TelemetryEventType.TEST_RUN,
        payload={
            "status": result.status,
            "output": result.output,
            "code_length": code_length,
            "changed_file_count": changed_file_count,
            "case_count": len(result.cases),
            "test_command": session.interview.scenario.project.test_command if session.interview.scenario.project else None,
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
    visible_snapshots = _visible_session_snapshots(db, session=session)
    submitted_files = (
        [submitted_file.model_dump() for submitted_file in payload.submitted_files]
        or _submitted_files_from_session_snapshots(db, session=session)
    )
    code = payload.code or _primary_code_from_snapshots(db, session=session)
    submission = Submission(
        organization_id=session.organization_id,
        session_id=session.id,
        candidate_id=session.candidate_id,
        code=code,
        notes=payload.notes,
        test_output=payload.test_output,
        submitted_files=submitted_files,
        push_status="not_configured",
        submitted_at=now,
    )
    db.add(submission)

    session.latest_code = code
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
                "code_length": len(code),
                "note_length": len(payload.notes),
                "submitted_file_count": len(submitted_files),
                "changed_file_count": sum(
                    1 for snapshot in visible_snapshots if snapshot.current_content != snapshot.original_content
                ),
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
    fallback_code = payload.code or session.latest_code or session.interview.scenario.starter_code
    code_snapshot = _workspace_code_context(db, session=session, fallback_code=fallback_code)
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
    _create_event(
        db,
        session=session,
        event_type=TelemetryEventType.AI_PROMPT_SENT,
        payload={
            "question_length": len(payload.question),
            "code_snapshot_length": len(code_snapshot),
            "ai_mode": ai_mode,
        },
    )

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

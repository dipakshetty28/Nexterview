from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.interview import (
    Interview,
    InterviewSession,
    InviteToken,
    Scenario,
    ScenarioProject,
    Submission,
)
from app.models.user import User, UserRole
from app.schemas.invite import InviteCreateRequest, InviteCreateResponse, InviteRegenerateRequest, InviteTokenRead
from app.schemas.interview import InterviewCreateRequest, InterviewRead, InterviewSubmissionResultRead
from app.schemas.scenario import ScenarioRead
from app.services.github import GitHubSubmissionFile, GitHubSubmissionPublisher
from app.services.invites import generate_invite_token, hash_invite_token
from app.services.scenario_generator import ScenarioGenerationResult, ScenarioGenerator
from app.services.scenario_projects import upsert_scenario_project
from app.services.scenario_seed_catalog import ScenarioTemplateUnavailableError

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_scenario_generator() -> ScenarioGenerator:
    return ScenarioGenerator()


def get_github_project_publisher() -> GitHubSubmissionPublisher:
    return GitHubSubmissionPublisher()


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
            .options(selectinload(Interview.scenario).selectinload(Scenario.project).selectinload(ScenarioProject.files))
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


def _invite_status(invite: InviteToken) -> str:
    if invite.revoked_at is not None or invite.status == "revoked":
        return "revoked"
    if invite.used_at is not None or invite.status == "used":
        return "used"
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        return "expired"
    return "active"


def _invite_url_for(invite: InviteToken, *, raw_token: str | None = None) -> str | None:
    token = raw_token or invite.token
    if not token:
        return None
    return _invite_url(token)


def _invite_read(invite: InviteToken, *, raw_token: str | None = None) -> InviteTokenRead:
    return InviteTokenRead(
        id=invite.id,
        interview_id=invite.interview_id,
        session_id=invite.session_id,
        candidate_id=invite.candidate_id,
        candidate_email=invite.candidate_email,
        candidate_name=invite.candidate_name,
        invite_url=_invite_url_for(invite, raw_token=raw_token),
        status=_invite_status(invite),
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        used_at=invite.used_at,
        revoked_at=invite.revoked_at,
        regenerated_from_invite_id=invite.regenerated_from_invite_id,
        created_by_user_id=invite.created_by_id,
        session_status=invite.session.status.value if invite.session else None,
    )


def _new_invite(
    *,
    interview: Interview,
    current_user: User,
    expires_in_days: int,
    candidate_email: str | None,
    candidate_name: str | None,
    regenerated_from_invite_id: UUID | None = None,
) -> tuple[InviteToken, str]:
    raw_token = generate_invite_token()
    invite = InviteToken(
        organization_id=interview.organization_id,
        interview_id=interview.id,
        created_by_id=current_user.id,
        token=raw_token,
        token_hash=hash_invite_token(raw_token),
        candidate_email=candidate_email,
        candidate_name=candidate_name,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        regenerated_from_invite_id=regenerated_from_invite_id,
    )
    return invite, raw_token


def _get_invite_for_interview(db: Session, *, interview: Interview, invite_id: UUID) -> InviteToken:
    invite = db.execute(
        select(InviteToken)
        .options(selectinload(InviteToken.session))
        .where(
            InviteToken.id == invite_id,
            InviteToken.interview_id == interview.id,
            InviteToken.organization_id == interview.organization_id,
        )
    ).scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite was not found.")
    return invite


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
            .options(selectinload(Interview.scenario).selectinload(Scenario.project).selectinload(ScenarioProject.files))
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


@router.get("/{interview_id}/submissions", response_model=list[InterviewSubmissionResultRead])
def list_interview_submissions(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> list[InterviewSubmissionResultRead]:
    interview = _get_interview_for_user(db, interview_id, current_user)
    try:
        rows = db.execute(
            select(InterviewSession, User, Submission)
            .join(User, User.id == InterviewSession.candidate_id)
            .outerjoin(Submission, Submission.session_id == InterviewSession.id)
            .where(InterviewSession.interview_id == interview.id)
            .order_by(InterviewSession.created_at.desc())
        ).all()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load interview submissions.",
        ) from exc
    session_ids = [session.id for session, _, _ in rows]
    invites_by_session_id: dict[UUID, InviteToken] = {}
    if session_ids:
        invite_rows = db.execute(
            select(InviteToken)
            .where(InviteToken.session_id.in_(session_ids))
            .order_by(InviteToken.created_at.desc())
        ).scalars()
        for invite in invite_rows:
            if invite.session_id and invite.session_id not in invites_by_session_id:
                invites_by_session_id[invite.session_id] = invite

    return [
        InterviewSubmissionResultRead(
            session_id=session.id,
            candidate_id=session.candidate_id,
            candidate_email=candidate.email,
            candidate_name=candidate.full_name,
            status=session.status.value,
            invite_status=_invite_status(invites_by_session_id[session.id]) if session.id in invites_by_session_id else None,
            invite_expires_at=invites_by_session_id[session.id].expires_at if session.id in invites_by_session_id else None,
            invite_used_at=invites_by_session_id[session.id].used_at if session.id in invites_by_session_id else None,
            started_at=session.started_at,
            submitted_at=session.submitted_at,
            reviewed_at=session.reviewed_at,
            submission_id=submission.id if submission else None,
            test_output=submission.test_output if submission else None,
            notes=submission.notes if submission else session.notes,
        )
        for session, candidate, submission in rows
    ]


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    interview = _get_interview_for_user(db, interview_id, current_user)
    db.execute(delete(Interview).where(Interview.id == interview.id).execution_options(synchronize_session=False))
    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete interview.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{interview_id}/invites", response_model=list[InviteTokenRead])
def list_interview_invites(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> list[InviteTokenRead]:
    interview = _get_interview_for_user(db, interview_id, current_user)
    try:
        invites = db.execute(
            select(InviteToken)
            .options(selectinload(InviteToken.session))
            .where(InviteToken.interview_id == interview.id, InviteToken.organization_id == interview.organization_id)
            .order_by(InviteToken.created_at.desc())
        ).scalars()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load invites.") from exc
    return [_invite_read(invite) for invite in invites]


@router.post("/{interview_id}/invite", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate_invite(
    interview_id: UUID,
    payload: InviteCreateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InviteCreateResponse:
    interview = _get_interview_for_user(db, interview_id, current_user)
    if interview.scenario is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Generate a scenario before creating invites.")
    candidate_email = _normalize_email(str(payload.candidate_email)) if payload.candidate_email else None
    created_invites: list[tuple[InviteToken, str]] = []
    for _ in range(payload.invite_count):
        invite, raw_token = _new_invite(
            interview=interview,
            current_user=current_user,
            expires_in_days=payload.expires_in_days,
            candidate_email=candidate_email,
            candidate_name=payload.candidate_name,
        )
        created_invites.append((invite, raw_token))
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

    invite_reads: list[InviteTokenRead] = []
    for invite, raw_token in created_invites:
        db.refresh(invite)
        invite_reads.append(_invite_read(invite, raw_token=raw_token))
    first_invite = invite_reads[0]
    return InviteCreateResponse(**first_invite.model_dump(), invites=invite_reads)


@router.post("/{interview_id}/invites/{invite_id}/regenerate", response_model=InviteTokenRead, status_code=status.HTTP_201_CREATED)
def regenerate_interview_invite(
    interview_id: UUID,
    invite_id: UUID,
    payload: InviteRegenerateRequest,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InviteTokenRead:
    interview = _get_interview_for_user(db, interview_id, current_user)
    invite = _get_invite_for_interview(db, interview=interview, invite_id=invite_id)
    if _invite_status(invite) != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active invites can be regenerated.")
    invite.status = "revoked"
    invite.revoked_at = datetime.now(timezone.utc)
    replacement, raw_token = _new_invite(
        interview=interview,
        current_user=current_user,
        expires_in_days=payload.expires_in_days,
        candidate_email=invite.candidate_email,
        candidate_name=invite.candidate_name,
        regenerated_from_invite_id=invite.id,
    )
    db.add(replacement)
    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to regenerate invite.") from exc
    db.refresh(replacement)
    return _invite_read(replacement, raw_token=raw_token)


@router.post("/{interview_id}/invites/{invite_id}/revoke", response_model=InviteTokenRead)
def revoke_interview_invite(
    interview_id: UUID,
    invite_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> InviteTokenRead:
    interview = _get_interview_for_user(db, interview_id, current_user)
    invite = _get_invite_for_interview(db, interview=interview, invite_id=invite_id)
    if _invite_status(invite) != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active invites can be revoked.")
    invite.status = "revoked"
    invite.revoked_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to revoke invite.") from exc
    db.refresh(invite)
    return _invite_read(invite)


@router.post("/{interview_id}/generate-scenario", response_model=ScenarioRead)
def generate_scenario(
    interview_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
    generator: Annotated[ScenarioGenerator, Depends(get_scenario_generator)],
    github_publisher: Annotated[GitHubSubmissionPublisher, Depends(get_github_project_publisher)],
) -> ScenarioRead:
    interview = _get_interview_for_user(db, interview_id, current_user)
    try:
        result: ScenarioGenerationResult = generator.generate(interview)
    except ScenarioTemplateUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if interview.scenario is None:
        scenario = Scenario(interview_id=interview.id)
        db.add(scenario)
    else:
        scenario = interview.scenario

    scenario.title = result.scenario.title
    scenario.role_title = result.scenario.role_title
    scenario.seniority = result.scenario.seniority
    scenario.interview_type = result.scenario.interview_type
    scenario.difficulty = result.scenario.difficulty
    scenario.stack = result.scenario.stack
    scenario.language = result.scenario.language
    scenario.framework = result.scenario.framework
    scenario.ai_mode = result.scenario.ai_mode
    scenario.business_context = result.scenario.business_context
    scenario.technical_requirements = result.scenario.technical_requirements
    scenario.visible_requirements = result.scenario.visible_requirements
    scenario.starter_code = result.scenario.starter_code
    scenario.starter_files_json = [file_payload.model_dump() for file_payload in result.scenario.starter_files_json]
    scenario.test_files_json = [file_payload.model_dump() for file_payload in result.scenario.test_files_json]
    scenario.expected_solution_files_json = [
        file_payload.model_dump() for file_payload in result.scenario.expected_solution_files_json
    ]
    scenario.expected_behavior = result.scenario.expected_behavior
    scenario.logs_or_bug_report = result.scenario.logs_or_bug_report
    scenario.bug_description = result.scenario.bug_description
    scenario.bug_description_internal = result.scenario.bug_description_internal
    scenario.feature_request = result.scenario.feature_request
    scenario.validation_instructions = result.scenario.validation_instructions
    scenario.validation_command = result.scenario.validation_command
    scenario.constraints = result.scenario.constraints
    scenario.candidate_task_summary = result.scenario.candidate_task_summary
    scenario.expected_solution_summary = result.scenario.expected_solution_summary
    scenario.scenario_fit = result.scenario.scenario_fit
    scenario.hidden_evaluation_points = result.scenario.hidden_evaluation_points
    scenario.hidden_rubric = result.scenario.hidden_rubric
    scenario.candidate_instructions = result.scenario.candidate_instructions
    scenario.interviewer_rubric = result.scenario.interviewer_rubric
    scenario.generation_source = result.source
    scenario.ai_model = result.model
    interview.status = "READY"

    try:
        db.flush()
        project = upsert_scenario_project(db, scenario=scenario, project_payload=result.scenario.project)
        if project is not None and result.scenario.project is not None:
            github_result = github_publisher.publish_scenario_project(
                interview_id=interview.id,
                scenario_id=scenario.id,
                generated_at=datetime.now(timezone.utc),
                files=[
                    GitHubSubmissionFile(path=project_file.path, content=project_file.content)
                    for project_file in result.scenario.project.files
                ],
            )
            project.starter_branch_name = github_result.branch_name
            project.starter_commit_sha = github_result.commit_sha
            project.starter_repository_url = github_result.repository_url
            project.starter_push_status = github_result.status
            project.starter_push_error = github_result.error
        db.commit()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to store scenario.")
    db.refresh(scenario)
    return ScenarioRead.model_validate(scenario)

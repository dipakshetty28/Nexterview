from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.interview import (
    AIMessage,
    AgentReview,
    Interview,
    InterviewSession,
    InterviewSessionStatus,
    Scenario,
    ScenarioProject,
    Submission,
    TelemetryEvent,
)
from app.models.user import User, UserRole
from app.schemas.review import (
    AgentReviewRead,
    AIUsageAnalysisRead,
    FileDiffRead,
    GitHubReviewLinksRead,
    ScoreBreakdownItemRead,
    SessionResultRead,
    SubmissionReviewSummaryRead,
)
from app.services.review_agents import (
    RepoSubmissionReviewer,
    build_score_breakdown,
    recommendation_for_score,
    summarize_ai_usage,
    weighted_score_from_breakdown,
)

router = APIRouter(prefix="/api", tags=["reviews"])


def get_review_agent_runner() -> RepoSubmissionReviewer:
    return RepoSubmissionReviewer()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _organization_ids_for(user: User) -> list[UUID]:
    return [membership.organization_id for membership in user.memberships]


def _ensure_internal_reviewer(user: User) -> list[UUID]:
    organization_ids = _organization_ids_for(user)
    if not organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not attached to an organization.",
        )
    return organization_ids


def _raise_schema_not_ready(exc: ProgrammingError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Review database tables are not available. Run Alembic migrations with `alembic upgrade head`.",
    ) from exc


def _submission_options():
    return (
        selectinload(Submission.session)
        .selectinload(InterviewSession.interview)
        .selectinload(Interview.scenario)
        .selectinload(Scenario.project)
        .selectinload(ScenarioProject.files),
        selectinload(Submission.session).selectinload(InterviewSession.ai_messages),
        selectinload(Submission.session).selectinload(InterviewSession.telemetry_events),
        selectinload(Submission.session).selectinload(InterviewSession.candidate),
        selectinload(Submission.session).selectinload(InterviewSession.interview),
        selectinload(Submission.agent_reviews),
    )


def _get_submission_for_reviewer(db: Session, *, submission_id: UUID, current_user: User) -> Submission:
    organization_ids = _ensure_internal_reviewer(current_user)
    try:
        submission = db.execute(
            select(Submission)
            .options(*_submission_options())
            .where(Submission.id == submission_id, Submission.organization_id.in_(organization_ids))
        ).scalar_one_or_none()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load submission.") from exc
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission was not found.")
    return submission


def _get_session_result_for_reviewer(db: Session, *, session_id: UUID, current_user: User) -> Submission:
    organization_ids = _ensure_internal_reviewer(current_user)
    try:
        submission = db.execute(
            select(Submission)
            .join(InterviewSession, Submission.session_id == InterviewSession.id)
            .options(*_submission_options())
            .where(Submission.session_id == session_id, InterviewSession.organization_id.in_(organization_ids))
        ).scalar_one_or_none()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load result.") from exc
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session result was not found.")
    return submission


def _review_context(submission: Submission) -> dict[str, Any]:
    session = submission.session
    scenario = session.interview.scenario
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission has no generated scenario.")

    test_outputs = []
    if submission.test_output:
        test_outputs.append(submission.test_output)
    for event in sorted(session.telemetry_events, key=lambda item: item.created_at):
        if event.event_type.value == "test_run":
            output = event.payload.get("output")
            if isinstance(output, str) and output not in test_outputs:
                test_outputs.append(output)

    return {
        "submission_id": str(submission.id),
        "session_id": str(submission.session_id),
        "scenario": {
            "title": scenario.title,
            "business_context": scenario.business_context,
            "technical_requirements": scenario.technical_requirements,
            "expected_behavior": scenario.expected_behavior,
            "logs_or_bug_report": scenario.logs_or_bug_report,
            "candidate_instructions": scenario.candidate_instructions,
            "bug_description": scenario.bug_description,
            "feature_request": scenario.feature_request,
            "validation_instructions": scenario.validation_instructions,
            "hidden_evaluation_points": scenario.hidden_evaluation_points,
            "hidden_rubric": scenario.hidden_rubric,
            "interviewer_rubric": scenario.interviewer_rubric,
        },
        "candidate_instructions": scenario.candidate_instructions,
        "bug_description": scenario.bug_description,
        "feature_request": scenario.feature_request,
        "validation_instructions": scenario.validation_instructions,
        "original_project_files": _original_project_files(scenario),
        "candidate_submitted_files": submission.submitted_files,
        "file_diffs": submission.file_diffs,
        "ai_chat_transcript": _ai_transcript(session.ai_messages),
        "telemetry_events": _telemetry_events(session.telemetry_events),
        "test_run_outputs": test_outputs,
        "candidate_notes": submission.notes or session.notes or "",
        "github": {
            "branch_name": submission.branch_name,
            "commit_sha": submission.commit_sha,
            "repository_url": submission.repository_url,
            "pull_request_url": submission.pull_request_url,
            "push_status": submission.push_status,
            "push_error": submission.push_error,
        },
    }


def _original_project_files(scenario: Scenario) -> list[dict[str, Any]]:
    if scenario.project is None:
        return [
            {
                "path": "starter-code",
                "content": scenario.starter_code,
                "language": "text",
                "file_type": "source",
                "is_hidden": False,
                "is_editable": True,
            }
        ]
    return [
        {
            "path": project_file.path,
            "content": project_file.content,
            "language": project_file.language,
            "file_type": project_file.file_type,
            "is_hidden": project_file.is_hidden,
            "is_editable": project_file.is_editable,
        }
        for project_file in sorted(scenario.project.files, key=lambda item: item.path)
    ]


def _ai_transcript(messages: list[AIMessage]) -> list[dict[str, Any]]:
    return [
        {
            "role": message.role.value,
            "content": message.content,
            "ai_mode": message.ai_mode,
            "metadata": message.message_metadata,
            "created_at": message.created_at.isoformat(),
        }
        for message in sorted(messages, key=lambda item: item.created_at)
    ]


def _telemetry_events(events: list[TelemetryEvent]) -> list[dict[str, Any]]:
    return [
        {
            "event_type": event.event_type.value,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }
        for event in sorted(events, key=lambda item: item.created_at)
    ]


def _summary_for_submission(submission: Submission, *, context: dict[str, Any] | None = None) -> SubmissionReviewSummaryRead:
    review_context = context or _review_context(submission)
    reviews = sorted(submission.agent_reviews, key=lambda review: review.agent_type)
    review_dicts = [
        {
            "agent_type": review.agent_type,
            "score": review.score,
        }
        for review in reviews
    ]
    breakdown = build_score_breakdown(review_dicts)
    weighted_score = weighted_score_from_breakdown(breakdown)
    hiring_review = next((review for review in reviews if review.agent_type == "hiring_recommendation"), None)
    recommendation = hiring_review.recommendation if hiring_review else recommendation_for_score(weighted_score)
    file_diffs = [FileDiffRead.model_validate(file_diff) for file_diff in submission.file_diffs]
    return SubmissionReviewSummaryRead(
        submission_id=submission.id,
        session_id=submission.session_id,
        candidate_id=submission.candidate_id,
        submitted_at=submission.submitted_at,
        status=submission.session.status.value,
        changed_files=[file_diff.path for file_diff in file_diffs],
        file_diffs=file_diffs,
        github=GitHubReviewLinksRead(
            branch_name=submission.branch_name,
            commit_sha=submission.commit_sha,
            repository_url=submission.repository_url,
            pull_request_url=submission.pull_request_url,
            push_status=submission.push_status,
            push_error=submission.push_error,
        ),
        agent_reviews=[AgentReviewRead.model_validate(review) for review in reviews],
        score_breakdown=[ScoreBreakdownItemRead.model_validate(item) for item in breakdown],
        weighted_score=weighted_score,
        recommendation=recommendation,
        ai_usage_analysis=AIUsageAnalysisRead.model_validate(summarize_ai_usage(review_context)),
        test_output=submission.test_output,
        notes=submission.notes,
    )


def _session_result_for_submission(submission: Submission) -> SessionResultRead:
    summary = _summary_for_submission(submission)
    session = submission.session
    scenario = session.interview.scenario
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission has no generated scenario.")
    return SessionResultRead(
        **summary.model_dump(),
        candidate_email=session.candidate.email,
        candidate_name=session.candidate.full_name,
        interview_id=session.interview_id,
        role_title=session.interview.role_title,
        scenario_title=scenario.title,
        bug_description=scenario.bug_description,
        feature_request=scenario.feature_request,
        validation_instructions=scenario.validation_instructions,
    )


@router.post(
    "/submissions/{submission_id}/review",
    response_model=SubmissionReviewSummaryRead,
    status_code=status.HTTP_201_CREATED,
)
def review_submission(
    submission_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
    reviewer: Annotated[RepoSubmissionReviewer, Depends(get_review_agent_runner)],
) -> SubmissionReviewSummaryRead:
    submission = _get_submission_for_reviewer(db, submission_id=submission_id, current_user=current_user)
    context = _review_context(submission)
    if not submission.agent_reviews:
        results = reviewer.review(context)
        for result in results:
            review = AgentReview(
                organization_id=submission.organization_id,
                submission_id=submission.id,
                session_id=submission.session_id,
                agent_type=result.agent_type,
                agent_label=result.agent_label,
                score=result.score,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                evidence=result.evidence,
                risk_flags=result.risk_flags,
                recommendation=result.recommendation,
                explanation=result.explanation,
                raw_response=result.raw_response,
            )
            db.add(review)
        submission.session.status = InterviewSessionStatus.REVIEWED
        submission.session.reviewed_at = submission.session.reviewed_at or _now_utc()

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to store submission review.",
            ) from exc

        submission = _get_submission_for_reviewer(db, submission_id=submission_id, current_user=current_user)

    return _summary_for_submission(submission, context=context)


@router.get("/submissions/{submission_id}/reviews", response_model=SubmissionReviewSummaryRead)
def get_submission_reviews(
    submission_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> SubmissionReviewSummaryRead:
    submission = _get_submission_for_reviewer(db, submission_id=submission_id, current_user=current_user)
    return _summary_for_submission(submission)


@router.get("/results/{session_id}", response_model=SessionResultRead)
def get_session_result(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> SessionResultRead:
    submission = _get_session_result_for_reviewer(db, session_id=session_id, current_user=current_user)
    return _session_result_for_submission(submission)

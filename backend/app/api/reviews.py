from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.api.deps import require_roles
from app.db.session import SessionLocal
from app.db.session import get_db
from app.models.interview import (
    AIMessage,
    AgentReview,
    Interview,
    InterviewSession,
    InterviewSessionStatus,
    Scenario,
    ScenarioProject,
    Score,
    Submission,
    TelemetryEvent,
)
from app.models.user import User, UserRole
from app.schemas.review import (
    AgentReviewRead,
    AITranscriptMessageRead,
    AIUsageAnalysisRead,
    FileDiffRead,
    PromptQualitySummaryRead,
    ResultsDashboardItemRead,
    ScoreBreakdownItemRead,
    SessionResultRead,
    SubmittedCodeFileRead,
    SubmissionReviewSummaryRead,
    TestRunSummaryRead,
    TelemetryTimelineEventRead,
)
from app.services.review_agents import (
    RepoSubmissionReviewer,
    build_score_breakdown,
    recommendation_for_score,
    summarize_ai_usage,
    weighted_score_from_breakdown,
)

router = APIRouter(prefix="/api", tags=["reviews"])
logger = logging.getLogger(__name__)


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
        selectinload(Submission.session).selectinload(InterviewSession.test_runs),
        selectinload(Submission.session).selectinload(InterviewSession.candidate),
        selectinload(Submission.session).selectinload(InterviewSession.interview),
        selectinload(Submission.agent_reviews),
        selectinload(Submission.score),
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
        "test_runs": [
            {
                "status": test_run.status,
                "command": test_run.command,
                "passed_count": test_run.passed_count,
                "failed_count": test_run.failed_count,
                "total_count": test_run.total_count,
                "failure_summary": test_run.failure_summary,
                "created_at": test_run.created_at,
            }
            for test_run in sorted(session.test_runs, key=lambda item: item.created_at)
        ],
        "test_run_outputs": test_outputs,
        "candidate_notes": submission.notes or session.notes or "",
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
            "id": message.id,
            "role": message.role.value,
            "content": message.content,
            "ai_mode": message.ai_mode,
            "metadata": message.message_metadata,
            "created_at": message.created_at,
        }
        for message in sorted(messages, key=lambda item: item.created_at)
    ]


def _telemetry_events(events: list[TelemetryEvent]) -> list[dict[str, Any]]:
    return [
        {
            "id": event.id,
            "event_type": event.event_type.value,
            "payload": event.payload,
            "created_at": event.created_at,
        }
        for event in sorted(events, key=lambda item: item.created_at)
    ]


def _submitted_code_files(submission: Submission) -> list[SubmittedCodeFileRead]:
    submitted_files = []
    for submitted_file in submission.submitted_files:
        path = submitted_file.get("path")
        content = submitted_file.get("content")
        language = submitted_file.get("language")
        file_type = submitted_file.get("file_type")
        if isinstance(path, str) and isinstance(content, str) and isinstance(language, str):
            submitted_files.append(
                SubmittedCodeFileRead(
                    path=path,
                    content=content,
                    language=language,
                    file_type=file_type if isinstance(file_type, str) else None,
                )
            )
    return sorted(submitted_files, key=lambda item: item.path)


def _risk_flags_for_reviews(reviews: list[AgentReview]) -> list[str]:
    flags: list[str] = []
    seen: set[str] = set()
    for review in sorted(reviews, key=lambda item: item.agent_type):
        for flag in review.risk_flags:
            cleaned = flag.strip() if isinstance(flag, str) else ""
            if cleaned and cleaned.lower() not in seen:
                flags.append(cleaned)
                seen.add(cleaned.lower())
    return flags


def _prompt_quality_summary(context: dict[str, Any]) -> dict[str, Any]:
    transcript = [message for message in context.get("ai_chat_transcript", []) if isinstance(message, dict)]
    telemetry_events = [event for event in context.get("telemetry_events", []) if isinstance(event, dict)]
    user_messages = [message for message in transcript if message.get("role") == "user"]
    prompt_texts = [str(message.get("content") or "") for message in user_messages]
    prompts_with_context = [
        message
        for message in user_messages
        if isinstance(message.get("metadata"), dict) and bool(message["metadata"].get("current_file_path"))
    ]
    vague_prompt_count = sum(1 for prompt in prompt_texts if _is_vague_prompt(prompt))
    validation_prompt_count = sum(
        1
        for prompt in prompt_texts
        if any(keyword in prompt.lower() for keyword in ["test", "verify", "validate", "edge case", "regression"])
    )
    test_run_count = sum(1 for event in telemetry_events if event.get("event_type") == "test_run")
    average_prompt_length = round(sum(len(prompt) for prompt in prompt_texts) / len(prompt_texts), 1) if prompt_texts else 0.0

    strengths = []
    risks = []
    if prompts_with_context:
        strengths.append("Candidate supplied file context in AI prompts.")
    if validation_prompt_count or test_run_count:
        strengths.append("Candidate showed validation intent through prompts or test runs.")
    if not prompt_texts:
        risks.append("No AI prompts were available for prompting-skill evaluation.")
    if vague_prompt_count:
        risks.append("Some prompts were short or underspecified.")
    if prompt_texts and not validation_prompt_count and not test_run_count:
        risks.append("Prompting history has limited verification signals.")

    if not prompt_texts:
        summary = "Candidate did not use the AI copilot in this session."
    elif risks and not strengths:
        summary = "Candidate prompting was limited and needs stronger context plus validation."
    elif risks:
        summary = "Candidate used AI with some useful context, but prompt quality had review risks."
    else:
        summary = "Candidate prompts included useful context and validation-oriented signals."

    return {
        "candidate_prompt_count": len(prompt_texts),
        "prompts_with_file_context": len(prompts_with_context),
        "vague_prompt_count": vague_prompt_count,
        "validation_prompt_count": validation_prompt_count,
        "average_prompt_length": average_prompt_length,
        "summary": summary,
        "strengths": strengths,
        "risks": risks,
    }


def _is_vague_prompt(prompt: str) -> bool:
    cleaned = " ".join(prompt.lower().split())
    if len(cleaned) < 35:
        return True
    vague_phrases = {"fix this", "help me", "what is wrong", "give me code", "solve this"}
    return cleaned in vague_phrases


def _dashboard_item_for_session(session: InterviewSession) -> ResultsDashboardItemRead:
    submission = session.submission
    score = submission.score if submission and submission.score else None
    reviews = submission.agent_reviews if submission else []
    scenario = session.interview.scenario
    test_runs = sorted(session.test_runs, key=lambda item: item.created_at)
    final_test_run = test_runs[-1] if test_runs else None
    return ResultsDashboardItemRead(
        session_id=session.id,
        submission_id=submission.id if submission else None,
        interview_id=session.interview_id,
        candidate_id=session.candidate_id,
        candidate_email=session.candidate.email,
        candidate_name=session.candidate.full_name,
        role_title=session.interview.role_title,
        scenario_title=scenario.title if scenario else None,
        status=session.status.value,
        submitted_at=session.submitted_at,
        reviewed_at=session.reviewed_at,
        weighted_score=score.weighted_score if score else None,
        recommendation=score.recommendation if score else None,
        risk_flags=_risk_flags_for_reviews(reviews),
        test_attempt_count=len(test_runs),
        first_test_status=test_runs[0].status if test_runs else None,
        final_test_status=final_test_run.status if final_test_run else None,
        final_test_summary=final_test_run.failure_summary if final_test_run and final_test_run.failure_summary else None,
    )


def _summary_for_submission(submission: Submission, *, context: dict[str, Any] | None = None) -> SubmissionReviewSummaryRead:
    review_context = context or _review_context(submission)
    reviews = sorted(submission.agent_reviews, key=lambda review: review.agent_type)
    if submission.score is not None:
        breakdown = submission.score.score_breakdown
        weighted_score = submission.score.weighted_score
        recommendation = submission.score.recommendation
        ai_usage_analysis = submission.score.ai_usage_analysis
    else:
        breakdown = _score_breakdown_for_reviews(reviews)
        weighted_score = weighted_score_from_breakdown(breakdown)
        recommendation = _recommendation_for_reviews(reviews, weighted_score)
        ai_usage_analysis = summarize_ai_usage(review_context)
    file_diffs = [FileDiffRead.model_validate(file_diff) for file_diff in submission.file_diffs]
    test_runs = [
        TestRunSummaryRead.model_validate(test_run)
        for test_run in sorted(submission.session.test_runs, key=lambda item: item.created_at)
    ]
    return SubmissionReviewSummaryRead(
        submission_id=submission.id,
        session_id=submission.session_id,
        candidate_id=submission.candidate_id,
        submitted_at=submission.submitted_at,
        status=submission.session.status.value,
        changed_files=[file_diff.path for file_diff in file_diffs],
        file_diffs=file_diffs,
        agent_reviews=[AgentReviewRead.model_validate(review) for review in reviews],
        score_breakdown=[ScoreBreakdownItemRead.model_validate(item) for item in breakdown],
        weighted_score=weighted_score,
        recommendation=recommendation,
        ai_usage_analysis=AIUsageAnalysisRead.model_validate(ai_usage_analysis),
        test_output=submission.test_output,
        test_runs=test_runs,
        notes=submission.notes,
    )


def _session_result_for_submission(submission: Submission) -> SessionResultRead:
    summary = _summary_for_submission(submission)
    session = submission.session
    scenario = session.interview.scenario
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission has no generated scenario.")
    review_context = _review_context(submission)
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
        submitted_files=_submitted_code_files(submission),
        ai_chat_transcript=[
            AITranscriptMessageRead.model_validate(message) for message in _ai_transcript(session.ai_messages)
        ],
        telemetry_timeline=[
            TelemetryTimelineEventRead.model_validate(event) for event in _telemetry_events(session.telemetry_events)
        ],
        prompt_quality_summary=PromptQualitySummaryRead.model_validate(_prompt_quality_summary(review_context)),
        risk_flags=_risk_flags_for_reviews(submission.agent_reviews),
    )


def _score_breakdown_for_reviews(reviews: list[AgentReview]) -> list[dict[str, Any]]:
    return build_score_breakdown(
        [
            {
                "agent_type": review.agent_type,
                "score": review.score,
            }
            for review in reviews
        ]
    )


def _recommendation_for_reviews(reviews: list[AgentReview], weighted_score: float | None) -> str | None:
    hiring_review = next((review for review in reviews if review.agent_type == "hiring_recommendation"), None)
    return hiring_review.recommendation if hiring_review else recommendation_for_score(weighted_score)


def _upsert_score(
    db: Session,
    *,
    submission: Submission,
    reviews: list[AgentReview],
    context: dict[str, Any],
) -> Score | None:
    if not reviews:
        return None
    breakdown = _score_breakdown_for_reviews(reviews)
    weighted_score = weighted_score_from_breakdown(breakdown)
    if weighted_score is None:
        return None
    recommendation = _recommendation_for_reviews(reviews, weighted_score) or "review complete"
    ai_usage_analysis = summarize_ai_usage(context)
    score = submission.score
    if score is None:
        score = Score(
            organization_id=submission.organization_id,
            submission_id=submission.id,
            session_id=submission.session_id,
            weighted_score=weighted_score,
            recommendation=recommendation,
            score_breakdown=breakdown,
            ai_usage_analysis=ai_usage_analysis,
            scoring_version="v1",
        )
        db.add(score)
    else:
        score.weighted_score = weighted_score
        score.recommendation = recommendation
        score.score_breakdown = breakdown
        score.ai_usage_analysis = ai_usage_analysis
        score.scoring_version = "v1"
    return score


def _persist_submission_review(
    db: Session,
    *,
    submission: Submission,
    reviewer: RepoSubmissionReviewer,
    context: dict[str, Any] | None = None,
) -> None:
    review_context = context or _review_context(submission)
    reviews = sorted(submission.agent_reviews, key=lambda review: review.agent_type)
    if not reviews:
        reviews = []
        for result in reviewer.review(review_context):
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
            reviews.append(review)
            db.add(review)
        db.flush()

    _upsert_score(db, submission=submission, reviews=reviews, context=review_context)
    submission.session.status = InterviewSessionStatus.REVIEWED
    submission.session.reviewed_at = submission.session.reviewed_at or _now_utc()


def run_submission_review_background(
    submission_id: UUID,
    reviewer: RepoSubmissionReviewer | None = None,
    bind: Any | None = None,
) -> None:
    if bind is None:
        db = SessionLocal()
    else:
        db = sessionmaker(autocommit=False, autoflush=False, bind=bind)()
    try:
        submission = db.execute(
            select(Submission).options(*_submission_options()).where(Submission.id == submission_id)
        ).scalar_one_or_none()
        if submission is None:
            logger.warning("Skipping submission review because submission %s was not found.", submission_id)
            return
        _persist_submission_review(
            db,
            submission=submission,
            reviewer=reviewer or RepoSubmissionReviewer(),
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Background submission review failed for submission %s.", submission_id)
    finally:
        db.close()


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
    _persist_submission_review(db, submission=submission, reviewer=reviewer, context=context)
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


@router.get("/results", response_model=list[ResultsDashboardItemRead])
def list_results_dashboard(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ResultsDashboardItemRead]:
    organization_ids = _ensure_internal_reviewer(current_user)
    try:
        sessions = db.execute(
            select(InterviewSession)
            .options(
                selectinload(InterviewSession.candidate),
                selectinload(InterviewSession.interview).selectinload(Interview.scenario),
                selectinload(InterviewSession.submission).selectinload(Submission.score),
                selectinload(InterviewSession.submission).selectinload(Submission.agent_reviews),
                selectinload(InterviewSession.test_runs),
            )
            .where(InterviewSession.organization_id.in_(organization_ids))
            .order_by(InterviewSession.updated_at.desc())
        ).scalars()
    except ProgrammingError as exc:
        db.rollback()
        _raise_schema_not_ready(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to load results dashboard.") from exc
    return [_dashboard_item_for_session(session) for session in sessions]


@router.get("/results/{session_id}", response_model=SessionResultRead)
def get_session_result(
    session_id: UUID,
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER))],
    db: Annotated[Session, Depends(get_db)],
) -> SessionResultRead:
    submission = _get_session_result_for_reviewer(db, session_id=session_id, current_user=current_user)
    return _session_result_for_submission(submission)

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FileDiffRead(BaseModel):
    path: str
    status: str
    language: str
    file_type: str
    additions: int
    deletions: int
    diff: str


class AgentReviewRead(BaseModel):
    id: UUID
    submission_id: UUID
    session_id: UUID
    agent_type: str
    agent_label: str
    score: int
    strengths: list[str]
    weaknesses: list[str]
    evidence: list[str]
    risk_flags: list[str]
    recommendation: str
    explanation: str
    raw_response: dict[str, Any]
    expected: list[str] = Field(default_factory=list)
    observed: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    confidence: float | None = None
    review_source: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScoreBreakdownItemRead(BaseModel):
    agent_type: str
    label: str
    weight: int
    score: int | None
    weighted_score: float | None


class AIUsageAnalysisRead(BaseModel):
    candidate_prompt_count: int
    assistant_response_count: int
    prompts_with_file_context: int
    test_run_count: int
    response_confidence_values: list[str]
    validated_suggestions: bool
    summary: str


class SubmittedCodeFileRead(BaseModel):
    path: str
    content: str
    language: str
    file_type: str | None = None


class AITranscriptMessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    ai_mode: str
    metadata: dict[str, Any]
    created_at: datetime


class TelemetryTimelineEventRead(BaseModel):
    id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class PromptQualitySummaryRead(BaseModel):
    candidate_prompt_count: int
    prompts_with_file_context: int
    vague_prompt_count: int
    validation_prompt_count: int
    average_prompt_length: float
    summary: str
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ResultsDashboardItemRead(BaseModel):
    session_id: UUID
    submission_id: UUID | None
    interview_id: UUID
    candidate_id: UUID
    candidate_email: str
    candidate_name: str
    role_title: str
    scenario_title: str | None
    status: str
    submitted_at: datetime | None
    reviewed_at: datetime | None
    weighted_score: float | None
    recommendation: str | None
    risk_flags: list[str] = Field(default_factory=list)
    test_attempt_count: int = 0
    first_test_status: str | None = None
    final_test_status: str | None = None
    final_test_summary: str | None = None


class TestRunSummaryRead(BaseModel):
    id: UUID
    status: str
    command: str
    duration_ms: int
    passed_count: int
    failed_count: int
    total_count: int
    failure_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionReviewSummaryRead(BaseModel):
    submission_id: UUID
    session_id: UUID
    candidate_id: UUID
    submitted_at: datetime
    status: str
    changed_files: list[str]
    file_diffs: list[FileDiffRead] = Field(default_factory=list)
    agent_reviews: list[AgentReviewRead] = Field(default_factory=list)
    score_breakdown: list[ScoreBreakdownItemRead] = Field(default_factory=list)
    weighted_score: float | None
    recommendation: str | None
    ai_usage_analysis: AIUsageAnalysisRead
    test_output: str | None
    test_runs: list[TestRunSummaryRead] = Field(default_factory=list)
    notes: str
    review_source: str | None = None


class SessionResultRead(SubmissionReviewSummaryRead):
    candidate_email: str
    candidate_name: str
    interview_id: UUID
    role_title: str
    scenario_title: str
    bug_description: str
    feature_request: str
    validation_instructions: str
    expected_behavior: list[str] = Field(default_factory=list)
    expected_solution_summary: str
    hidden_evaluation_points: list[str] = Field(default_factory=list)
    interviewer_rubric: list[str] = Field(default_factory=list)
    candidate_observed: list[str] = Field(default_factory=list)
    candidate_missed: list[str] = Field(default_factory=list)
    suggested_follow_up_questions: list[str] = Field(default_factory=list)
    submitted_files: list[SubmittedCodeFileRead] = Field(default_factory=list)
    ai_chat_transcript: list[AITranscriptMessageRead] = Field(default_factory=list)
    telemetry_timeline: list[TelemetryTimelineEventRead] = Field(default_factory=list)
    prompt_quality_summary: PromptQualitySummaryRead
    risk_flags: list[str] = Field(default_factory=list)

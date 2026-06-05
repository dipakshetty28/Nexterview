from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CalibrationTier = Literal["strong", "average", "weak"]
CalibrationMessageRole = Literal["user", "assistant"]
CalibrationTestStatus = Literal["passed", "failed"]


class CalibrationTestResultRead(BaseModel):
    status: CalibrationTestStatus
    command: str
    passed_count: int
    failed_count: int
    summary: str
    output: str


class CalibrationTranscriptMessageRead(BaseModel):
    role: CalibrationMessageRole
    content: str


class CalibrationAgentReviewRead(BaseModel):
    agent_type: str
    agent_label: str
    score: int = Field(ge=0, le=100)
    recommendation: str
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class CalibrationSessionRead(BaseModel):
    id: str
    tier: CalibrationTier
    candidate_name: str
    role_title: str
    scenario_title: str
    ai_mode: str
    status: str
    final_score: int = Field(ge=0, le=100)
    recommendation: str
    review_summary: str
    expected_behavior: list[str] = Field(default_factory=list)
    observed_behavior: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    final_code_path: str
    final_code_language: str
    final_code: str
    test_result: CalibrationTestResultRead
    ai_transcript: list[CalibrationTranscriptMessageRead] = Field(default_factory=list)
    agent_reviews: list[CalibrationAgentReviewRead] = Field(default_factory=list)

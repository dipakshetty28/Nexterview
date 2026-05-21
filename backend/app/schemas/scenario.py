from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneratedScenario(BaseModel):
    title: str = Field(description="Short, specific title for the engineering task.")
    business_context: str = Field(description="Realistic product or business reason for the work.")
    technical_requirements: list[str] = Field(description="Concrete implementation requirements.")
    starter_code: str = Field(description="Broken or incomplete starter code for the candidate.")
    expected_behavior: list[str] = Field(description="Observable behavior the completed solution should produce.")
    logs_or_bug_report: str = Field(description="Relevant logs, error output, or bug report details.")
    hidden_evaluation_points: list[str] = Field(description="Interviewer-only signals to evaluate.")
    candidate_instructions: str = Field(description="Instructions shown to the candidate.")
    interviewer_rubric: list[str] = Field(description="Rubric points for interviewer scoring.")

    @field_validator("title", "business_context", "starter_code", "logs_or_bug_report", "candidate_instructions")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("Scenario text fields must contain meaningful content.")
        return cleaned

    @field_validator("technical_requirements", "expected_behavior", "hidden_evaluation_points", "interviewer_rubric")
    @classmethod
    def require_meaningful_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) < 2:
            raise ValueError("Scenario list fields must include at least two items.")
        return cleaned


class ScenarioRead(GeneratedScenario):
    id: UUID
    interview_id: UUID
    generation_source: str
    ai_model: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

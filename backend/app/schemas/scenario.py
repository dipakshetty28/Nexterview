from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.project import GeneratedScenarioProject, ScenarioProjectRead


class ScenarioFilePayload(BaseModel):
    path: str
    language: str
    content: str


class GeneratedScenario(BaseModel):
    title: str = Field(description="Short, specific title for the engineering task.")
    role_title: str = Field(default="", description="Role title the scenario was generated for.")
    seniority: str = Field(default="", description="Seniority level the scenario was generated for.")
    interview_type: str = Field(default="", description="Interview type the scenario was generated for.")
    difficulty: str = Field(default="", description="Difficulty level the scenario was generated for.")
    stack: list[str] = Field(default_factory=list, description="Stack tags used to generate the scenario.")
    language: str = Field(default="", description="Primary implementation language.")
    framework: str = Field(default="", description="Primary framework or runtime.")
    ai_mode: str = Field(default="", description="Allowed candidate AI mode.")
    business_context: str = Field(description="Realistic product or business reason for the work.")
    technical_requirements: list[str] = Field(description="Concrete implementation requirements.")
    visible_requirements: list[str] = Field(default_factory=list, description="Candidate-visible implementation requirements.")
    starter_code: str = Field(description="Broken or incomplete starter code for the candidate.")
    starter_files_json: list[ScenarioFilePayload] = Field(default_factory=list)
    test_files_json: list[ScenarioFilePayload] = Field(default_factory=list)
    expected_solution_files_json: list[ScenarioFilePayload] = Field(default_factory=list)
    expected_behavior: list[str] = Field(description="Observable behavior the completed solution should produce.")
    logs_or_bug_report: str = Field(description="Relevant logs, error output, or bug report details.")
    bug_description: str = Field(default="", description="Root bug or defect intentionally present in the project.")
    bug_description_internal: str = Field(default="", description="Interviewer-only root bug details.")
    feature_request: str = Field(default="", description="Feature request the candidate should implement or account for.")
    validation_instructions: str = Field(default="", description="Candidate-facing validation or test instructions.")
    validation_command: str = Field(default="", description="Private command used by the platform runner.")
    constraints: list[str] = Field(default_factory=list, description="Candidate-visible constraints.")
    candidate_task_summary: str = Field(default="", description="Short summary of the work shown to candidates.")
    expected_solution_summary: str = Field(default="", description="Interviewer-only expected solution summary.")
    scenario_fit: str = Field(default="", description="Why the scenario fits the interview configuration.")
    hidden_evaluation_points: list[str] = Field(description="Interviewer-only signals to evaluate.")
    hidden_rubric: list[str] = Field(default_factory=list, description="Interviewer-only rubric for repo project review.")
    candidate_instructions: str = Field(description="Instructions shown to the candidate.")
    interviewer_rubric: list[str] = Field(description="Rubric points for interviewer scoring.")
    project: GeneratedScenarioProject | None = Field(
        default=None,
        description="Optional multi-file runnable project template for the scenario.",
    )

    @field_validator("title", "business_context", "starter_code", "logs_or_bug_report", "candidate_instructions")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("Scenario text fields must contain meaningful content.")
        return cleaned

    @field_validator(
        "role_title",
        "seniority",
        "interview_type",
        "difficulty",
        "language",
        "framework",
        "ai_mode",
        "bug_description",
        "bug_description_internal",
        "feature_request",
        "validation_instructions",
        "validation_command",
        "candidate_task_summary",
        "expected_solution_summary",
        "scenario_fit",
    )
    @classmethod
    def strip_optional_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("technical_requirements", "expected_behavior", "hidden_evaluation_points", "interviewer_rubric")
    @classmethod
    def require_meaningful_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) < 2:
            raise ValueError("Scenario list fields must include at least two items.")
        return cleaned

    @field_validator("visible_requirements", "constraints", "stack")
    @classmethod
    def strip_optional_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ScenarioRead(GeneratedScenario):
    id: UUID
    interview_id: UUID
    generation_source: str
    ai_model: str | None = None
    project: ScenarioProjectRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

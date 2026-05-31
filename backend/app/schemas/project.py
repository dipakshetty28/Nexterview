from __future__ import annotations

import enum
import re
from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectFileType(str, enum.Enum):
    SOURCE = "source"
    CONFIG = "config"
    TEST = "test"
    DATA = "data"
    DOCS = "docs"
    HIDDEN_TEST = "hidden_test"
    METADATA = "metadata"


_CANDIDATE_CLI_COMMAND_RE = re.compile(
    r"\b("
    r"python\s+-m\s+pip\s+install|pip\s+install|uv\s+pip\s+install|poetry\s+install|"
    r"npm\s+install|pnpm\s+install|yarn\s+install|bun\s+install|"
    r"npm\s+run\s+(dev|start|test)|npm\s+test|pnpm\s+test|yarn\s+test|bun\s+test|"
    r"pytest|vitest|uvicorn"
    r")\b",
    re.IGNORECASE,
)


def _clean_project_path(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or cleaned.startswith("/") or path.is_absolute() or ".." in path.parts:
        raise ValueError("Project file paths must be relative POSIX paths without parent traversal.")
    if ":" in path.parts[0]:
        raise ValueError("Project file paths must not include drive letters.")
    return cleaned


class GeneratedProjectFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=400000)
    language: str = Field(min_length=1, max_length=80)
    file_type: ProjectFileType
    is_editable: bool = True
    is_hidden: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _clean_project_path(value)

    @field_validator("language")
    @classmethod
    def strip_language(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def align_hidden_test_flags(self) -> GeneratedProjectFile:
        if self.file_type == ProjectFileType.HIDDEN_TEST and not self.is_hidden:
            self.is_hidden = True
        if self.is_hidden and self.is_editable:
            self.is_editable = False
        return self


class GeneratedSolutionFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=400000)
    language: str = Field(min_length=1, max_length=80)

    model_config = ConfigDict(extra="forbid")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _clean_project_path(value)

    @field_validator("language")
    @classmethod
    def strip_language(cls, value: str) -> str:
        return value.strip().lower()


class GeneratedScenarioProject(BaseModel):
    stack: list[str] = Field(min_length=1, max_length=12)
    project_name: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=8)
    run_command: str | None = Field(default=None, max_length=500)
    test_command: str | None = Field(default=None, max_length=500)
    install_command: str | None = Field(default=None, max_length=500)
    entrypoint: str | None = Field(default=None, max_length=500)
    package_manager: str | None = Field(default=None, max_length=80)
    framework: str | None = Field(default=None, max_length=120)
    files: list[GeneratedProjectFile] = Field(min_length=1, max_length=80)

    model_config = ConfigDict(extra="forbid")

    @field_validator("stack")
    @classmethod
    def strip_stack(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Project stack must include at least one item.")
        return cleaned

    @field_validator("project_name", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("run_command", "test_command", "install_command", "entrypoint", "package_manager", "framework")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_unique_paths(self) -> GeneratedScenarioProject:
        paths = [project_file.path for project_file in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Project files must use unique paths.")
        return self


class AIGeneratedScenarioDetails(BaseModel):
    title: str = Field(min_length=8, max_length=180)
    business_context: str = Field(min_length=40)
    candidate_task_summary: str = Field(min_length=20)
    visible_requirements: list[str] = Field(default_factory=list, max_length=12)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    bug_description: str = Field(min_length=20)
    bug_description_internal: str | None = Field(default=None, max_length=4000)
    feature_request: str = Field(min_length=20)
    expected_behavior: str = Field(min_length=20)
    validation_instructions: str = Field(min_length=20)
    candidate_instructions: str = Field(min_length=40)
    hidden_rubric: str = Field(min_length=40)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "title",
        "business_context",
        "candidate_task_summary",
        "bug_description",
        "feature_request",
        "expected_behavior",
        "validation_instructions",
        "candidate_instructions",
        "hidden_rubric",
        "bug_description_internal",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("visible_requirements", "constraints")
    @classmethod
    def strip_list_items(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class AIGeneratedProjectMetadata(BaseModel):
    project_name: str = Field(min_length=2, max_length=140)
    stack: str = Field(min_length=2, max_length=200)
    language: str | None = Field(default=None, max_length=80)
    framework: str = Field(min_length=2, max_length=120)
    package_manager: str = Field(min_length=2, max_length=80)
    install_command: str = Field(min_length=2, max_length=500)
    run_command: str = Field(min_length=2, max_length=500)
    test_command: str = Field(min_length=2, max_length=500)
    validation_command: str | None = Field(default=None, max_length=500)
    entrypoint: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "project_name",
        "stack",
        "language",
        "framework",
        "package_manager",
        "install_command",
        "run_command",
        "test_command",
        "validation_command",
        "entrypoint",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("entrypoint")
    @classmethod
    def validate_entrypoint(cls, value: str) -> str:
        return _clean_project_path(value)


class AIGeneratedProjectEnvelope(BaseModel):
    scenario: AIGeneratedScenarioDetails
    project: AIGeneratedProjectMetadata
    files: list[GeneratedProjectFile] = Field(min_length=5, max_length=12)
    expected_solution_files: list[GeneratedSolutionFile] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_project_contract(self) -> AIGeneratedProjectEnvelope:
        paths = {project_file.path for project_file in self.files}
        if self.project.entrypoint not in paths:
            raise ValueError("The project entrypoint must match one generated file path.")
        if not any(project_file.file_type == ProjectFileType.DATA and project_file.path.endswith(".json") for project_file in self.files):
            raise ValueError("Generated projects must include at least one JSON seed data file.")
        if not any(project_file.file_type in {ProjectFileType.TEST, ProjectFileType.HIDDEN_TEST} for project_file in self.files):
            raise ValueError("Generated projects must include at least one test or validation file.")
        if not any(project_file.path in {"README.md", "TASK.md"} for project_file in self.files):
            raise ValueError("Generated projects must include README.md or TASK.md.")
        if not any(project_file.file_type == ProjectFileType.SOURCE for project_file in self.files):
            raise ValueError("Generated projects must include at least one source file.")
        editable_paths = {project_file.path for project_file in self.files if project_file.is_editable}
        solution_paths = {solution_file.path for solution_file in self.expected_solution_files}
        if not solution_paths <= editable_paths:
            raise ValueError("Expected solution files must correspond to editable project files.")
        candidate_materials = [
            self.scenario.validation_instructions,
            self.scenario.candidate_instructions,
            *self.scenario.visible_requirements,
            *self.scenario.constraints,
            *[
                project_file.content
                for project_file in self.files
                if not project_file.is_hidden and project_file.file_type == ProjectFileType.DOCS
            ],
        ]
        if any(_CANDIDATE_CLI_COMMAND_RE.search(material) for material in candidate_materials):
            raise ValueError(
                "Candidate-facing task materials must describe the pre-provisioned workspace and platform Run button, "
                "not local install, server, or test CLI commands."
            )
        return self


class ProjectFileRead(BaseModel):
    id: UUID
    project_id: UUID
    path: str
    content: str
    language: str
    file_type: str
    is_editable: bool
    is_hidden: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScenarioProjectRead(BaseModel):
    id: UUID
    scenario_id: UUID
    stack: list[str]
    project_name: str
    description: str
    run_command: str | None
    test_command: str | None
    install_command: str | None
    entrypoint: str | None
    package_manager: str | None
    framework: str | None
    starter_branch_name: str | None
    starter_commit_sha: str | None
    starter_repository_url: str | None
    starter_push_status: str | None
    starter_push_error: str | None
    files: list[ProjectFileRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateProjectFileRead(BaseModel):
    path: str
    content: str
    language: str
    file_type: str
    is_editable: bool

    model_config = ConfigDict(from_attributes=True)


class CandidateScenarioProjectRead(BaseModel):
    project_name: str
    stack: list[str]
    framework: str | None
    package_manager: str | None
    install_command: str | None
    run_command: str | None
    test_command: str | None
    entrypoint: str | None
    files: list[CandidateProjectFileRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SessionFileSnapshotRead(BaseModel):
    id: UUID
    session_id: UUID
    project_file_id: UUID
    path: str
    original_content: str
    current_content: str
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateWorkspaceFileRead(BaseModel):
    id: UUID
    project_file_id: UUID
    path: str
    original_content: str
    current_content: str
    language: str
    file_type: str
    is_editable: bool
    updated_at: datetime


class CandidateWorkspaceProjectRead(BaseModel):
    id: UUID
    project_name: str
    stack: list[str]
    description: str
    framework: str | None
    package_manager: str | None
    install_command: str | None
    run_command: str | None
    test_command: str | None
    entrypoint: str | None

    model_config = ConfigDict(from_attributes=True)


class CandidateWorkspaceRead(BaseModel):
    session_id: UUID
    project: CandidateWorkspaceProjectRead | None
    files: list[CandidateWorkspaceFileRead] = Field(default_factory=list)
    last_autosaved_at: datetime | None


class CandidateWorkspaceFileUpdate(BaseModel):
    content: str = Field(max_length=400000)


class SubmittedFileRead(BaseModel):
    path: str
    content: str
    language: str
    file_type: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _clean_project_path(value)

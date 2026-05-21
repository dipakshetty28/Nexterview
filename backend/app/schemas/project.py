from __future__ import annotations

import enum
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
    files: list[ProjectFileRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

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


class SubmittedFileRead(BaseModel):
    path: str
    content: str
    language: str
    file_type: str | None = None

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _clean_project_path(value)

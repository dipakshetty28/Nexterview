from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.project import AIGeneratedProjectEnvelope, ProjectFileType


class ScenarioTargetMismatchError(ValueError):
    """Raised when generated project files do not match the selected interview stack."""


@dataclass(frozen=True)
class ScenarioTarget:
    kind: str
    language: str
    framework: str
    runtime: str
    package_manager: str
    test_framework: str
    validation_command: str
    file_templates: tuple[str, ...]

    def prompt_payload(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "language": self.language,
            "framework": self.framework,
            "runtime": self.runtime,
            "package_manager": self.package_manager,
            "test_framework": self.test_framework,
            "validation_command": self.validation_command,
            "file_templates": list(self.file_templates),
        }


_TARGETS = {
    "java_spring_boot": ScenarioTarget(
        kind="java_spring_boot",
        language="java",
        framework="Spring Boot",
        runtime="JVM",
        package_manager="Maven",
        test_framework="JUnit",
        validation_command="mvn test",
        file_templates=("pom.xml", "src/main/java/...", "src/test/java/..."),
    ),
    "python_fastapi": ScenarioTarget(
        kind="python_fastapi",
        language="python",
        framework="FastAPI",
        runtime="Python",
        package_manager="pip",
        test_framework="pytest",
        validation_command="python -m pytest",
        file_templates=("app/...", "tests/...", "requirements.txt"),
    ),
    "node_express": ScenarioTarget(
        kind="node_express",
        language="typescript",
        framework="Express",
        runtime="Node.js",
        package_manager="npm",
        test_framework="Vitest/Jest",
        validation_command="npm test",
        file_templates=("package.json", "src/...", "tests/..."),
    ),
    "react_next": ScenarioTarget(
        kind="react_next",
        language="typescript",
        framework="Next.js",
        runtime="Node.js",
        package_manager="npm",
        test_framework="Vitest/React Testing Library",
        validation_command="npm test",
        file_templates=("package.json", "app/...", "components/...", "tests/..."),
    ),
    "ai_rag": ScenarioTarget(
        kind="ai_rag",
        language="python",
        framework="RAG",
        runtime="Python",
        package_manager="pip",
        test_framework="pytest",
        validation_command="python -m pytest",
        file_templates=("app/...", "tests/...", "requirements.txt"),
    ),
}


def normalize_scenario_target(*, stack: list[str], language: str | None = None, framework: str | None = None, role_title: str = "", interview_type: str = "") -> ScenarioTarget | None:
    raw_text = " ".join([language or "", framework or "", role_title, interview_type, *stack]).lower()
    tokens = _tokens(raw_text)

    if _has_any(tokens, raw_text, ("java", "spring", "spring boot", "jvm", "maven", "gradle")):
        return _TARGETS["java_spring_boot"]
    if _has_any(tokens, raw_text, ("rag", "langchain", "langgraph", "ai engineering", "llm")):
        return _TARGETS["ai_rag"]
    if _has_any(tokens, raw_text, ("react", "next", "next.js", "nextjs", "typescript frontend")):
        return _TARGETS["react_next"]
    if _has_any(tokens, raw_text, ("python", "fastapi")):
        return _TARGETS["python_fastapi"]
    if _has_any(tokens, raw_text, ("node", "express", "javascript", "typescript backend")):
        return _TARGETS["node_express"]
    return None


def validate_envelope_matches_target(envelope: AIGeneratedProjectEnvelope, target: ScenarioTarget | None) -> None:
    if target is None:
        return
    if target.kind == "java_spring_boot":
        _validate_java_spring_boot(envelope)
    elif target.kind == "python_fastapi":
        _validate_python_fastapi(envelope)


def _tokens(value: str) -> set[str]:
    return {
        "".join(character for character in token if character.isalnum())
        for token in value.replace("+", " ").replace("/", " ").replace("-", " ").replace(".", " ").split()
        if token.strip()
    }


def _has_any(tokens: set[str], raw_text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        normalized = keyword.lower().strip()
        if " " in normalized:
            if normalized in raw_text:
                return True
        elif normalized.replace(".", "") in tokens:
            return True
    return False


def _visible_test_paths(envelope: AIGeneratedProjectEnvelope) -> list[str]:
    return [
        project_file.path
        for project_file in envelope.files
        if not project_file.is_hidden and project_file.file_type == ProjectFileType.TEST
    ]


def _validation_command(envelope: AIGeneratedProjectEnvelope) -> str:
    return (envelope.project.validation_command or envelope.project.test_command or "").lower()


def _validate_java_spring_boot(envelope: AIGeneratedProjectEnvelope) -> None:
    paths = [project_file.path for project_file in envelope.files]
    lowered_paths = [path.lower() for path in paths]
    visible_tests = _visible_test_paths(envelope)
    command = _validation_command(envelope)
    project_text = " ".join(
        [
            envelope.project.language or "",
            envelope.project.framework,
            envelope.project.stack,
            envelope.project.package_manager,
            envelope.project.test_framework or "",
            command,
        ]
    ).lower()

    if not ("java" in project_text and "spring" in project_text):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must generate Java + Spring Boot metadata.")
    if not any(path in {"pom.xml", "build.gradle", "build.gradle.kts"} for path in lowered_paths):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must include pom.xml or build.gradle.")
    if not any(path.startswith("src/main/java/") and path.endswith(".java") for path in lowered_paths):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must include src/main/java source files.")
    if not any(path.startswith("src/test/java/") and path.endswith(".java") for path in visible_tests):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must include visible src/test/java tests.")
    if not re.search(r"\b(mvn\s+test|gradle\s+test|\.\/gradlew\s+test)\b", command):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must validate with mvn test or gradle test.")
    if any(path.endswith(".py") for path in lowered_paths):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must not include Python files.")
    if any("pytest" in project_file.content.lower() for project_file in envelope.files):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must not include pytest content.")
    if any("fastapi" in project_file.content.lower() for project_file in envelope.files):
        raise ScenarioTargetMismatchError("Java/Spring Boot interviews must not include FastAPI content.")


def _validate_python_fastapi(envelope: AIGeneratedProjectEnvelope) -> None:
    paths = [project_file.path.lower() for project_file in envelope.files]
    command = _validation_command(envelope)
    project_text = " ".join(
        [
            envelope.project.language or "",
            envelope.project.framework,
            envelope.project.stack,
            envelope.project.package_manager,
            envelope.project.test_framework or "",
            command,
        ]
    ).lower()

    if "fastapi" not in project_text and not any("fastapi" in project_file.content.lower() for project_file in envelope.files):
        raise ScenarioTargetMismatchError("Python/FastAPI interviews must generate FastAPI project files.")
    if not any(path.endswith(".py") for path in paths):
        raise ScenarioTargetMismatchError("Python/FastAPI interviews must include Python files.")
    if not any(path.endswith(".py") for path in _visible_test_paths(envelope)):
        raise ScenarioTargetMismatchError("Python/FastAPI interviews must include pytest-style Python tests.")
    if not ("pytest" in command or "python -m pytest" in command):
        raise ScenarioTargetMismatchError("Python/FastAPI interviews must validate with pytest.")
    if any(path in {"pom.xml", "build.gradle", "build.gradle.kts"} or path.startswith("src/main/java/") for path in paths):
        raise ScenarioTargetMismatchError("Python/FastAPI interviews must not include Java build files.")

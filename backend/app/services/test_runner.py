from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import UUID

from app.models.interview import Scenario
from app.schemas.invite import TestCaseResult, TestRunResult

__test__ = False


class TestRunnerError(RuntimeError):
    """Raised when the runner cannot safely execute a scenario."""


@dataclass(frozen=True)
class CandidateTestFile:
    path: str
    content: str
    language: str
    file_type: str | None = None
    is_hidden: bool = False


_SECRET_PATTERNS = (
    re.compile(r"\b(OPENAI_API_KEY|GITHUB_TOKEN|JWT_SECRET|DATABASE_URL|REDIS_URL)\s*=\s*[^\s]+", re.IGNORECASE),
    re.compile(r"\b(postgresql|postgres|redis)://[^\s)]+", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
)

_ALLOWED_COMMANDS: dict[str, tuple[str, ...]] = {
    "pytest": (sys.executable, "-m", "pytest", "--tb=short", "-q"),
    "python -m pytest": (sys.executable, "-m", "pytest", "--tb=short", "-q"),
}


class CandidateTestRunner:
    def __init__(self, *, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def run_candidate_tests(
        self,
        *,
        scenario: Scenario,
        candidate_files: list[CandidateTestFile],
        visible_tests: list[CandidateTestFile],
        hidden_tests: list[CandidateTestFile] | None = None,
        include_hidden: bool = False,
    ) -> TestRunResult:
        command_text = _normalize_command(scenario.validation_command or _scenario_test_command(scenario))
        created_at = datetime.now(timezone.utc)
        if command_text not in _ALLOWED_COMMANDS:
            return TestRunResult(
                status="error",
                command=command_text or "unsupported",
                stdout="",
                stderr="",
                duration_ms=0,
                passed_count=0,
                failed_count=0,
                total_count=0,
                failure_summary="No safe local runner is available for this scenario command yet.",
                created_at=created_at,
                output="No safe local runner is available for this scenario command yet.",
                cases=[
                    TestCaseResult(
                        name="runner-supported",
                        status="failed",
                        details="This scenario needs a Docker-backed or language-specific runner before checks can execute.",
                    )
                ],
            )

        files_to_write = _merge_files(
            [
                *candidate_files,
                *visible_tests,
                *(hidden_tests or [] if include_hidden else []),
            ]
        )
        start = time.perf_counter()
        workspace = tempfile.mkdtemp(prefix="nexterview-test-")
        try:
            for file in files_to_write:
                _write_workspace_file(workspace, file)
            completed = subprocess.run(
                _ALLOWED_COMMANDS[command_text],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=_safe_env(workspace),
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            stdout = _sanitize_output(completed.stdout)
            stderr = _sanitize_output(completed.stderr)
            counts = _parse_pytest_counts(stdout + "\n" + stderr, completed.returncode)
            status = "passed" if completed.returncode == 0 else "failed"
            failure_summary = _failure_summary(status=status, stdout=stdout, stderr=stderr, counts=counts)
            return TestRunResult(
                status=status,
                command=command_text,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                passed_count=counts["passed"],
                failed_count=counts["failed"],
                total_count=counts["total"],
                failure_summary=failure_summary,
                created_at=created_at,
                output=_safe_summary(status=status, command=command_text, counts=counts, failure_summary=failure_summary),
                cases=[
                    TestCaseResult(
                        name="pytest",
                        status="passed" if status == "passed" else "failed",
                        details=failure_summary or f"{counts['passed']}/{counts['total']} tests passed.",
                    )
                ],
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            stdout = _sanitize_output(exc.stdout or "")
            stderr = _sanitize_output(exc.stderr or "")
            failure_summary = f"Test run timed out after {self.timeout_seconds} seconds."
            return TestRunResult(
                status="timeout",
                command=command_text,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                passed_count=0,
                failed_count=1,
                total_count=1,
                failure_summary=failure_summary,
                created_at=created_at,
                output=failure_summary,
                cases=[TestCaseResult(name="timeout", status="failed", details=failure_summary)],
            )
        except OSError:
            duration_ms = int((time.perf_counter() - start) * 1000)
            failure_summary = "Unable to execute the workspace checks in the local runner."
            return TestRunResult(
                status="error",
                command=command_text,
                stdout="",
                stderr="",
                duration_ms=duration_ms,
                passed_count=0,
                failed_count=1,
                total_count=1,
                failure_summary=failure_summary,
                created_at=created_at,
                output=failure_summary,
                cases=[TestCaseResult(name="runner-error", status="failed", details=failure_summary)],
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


def _test_run_result_from_model_read(row: object) -> TestRunResult:
    return TestRunResult(
        status=getattr(row, "status"),
        command=getattr(row, "command"),
        stdout=getattr(row, "stdout"),
        stderr=getattr(row, "stderr"),
        duration_ms=getattr(row, "duration_ms"),
        passed_count=getattr(row, "passed_count"),
        failed_count=getattr(row, "failed_count"),
        total_count=getattr(row, "total_count"),
        failure_summary=getattr(row, "failure_summary"),
        created_at=getattr(row, "created_at"),
        output=_safe_summary(
            status=getattr(row, "status"),
            command=getattr(row, "command"),
            counts={
                "passed": getattr(row, "passed_count"),
                "failed": getattr(row, "failed_count"),
                "total": getattr(row, "total_count"),
            },
            failure_summary=getattr(row, "failure_summary"),
        ),
        cases=[
            TestCaseResult(
                name="stored-run",
                status="passed" if getattr(row, "status") == "passed" else "failed",
                details=getattr(row, "failure_summary") or "Stored test run completed.",
            )
        ],
    )


def _scenario_test_command(scenario: Scenario) -> str:
    if scenario.project and scenario.project.test_command:
        return scenario.project.test_command
    return ""


def _normalize_command(command: str) -> str:
    cleaned = " ".join(command.strip().split()).lower()
    if cleaned in {"pytest", "pytest -q", "python -m pytest -q"}:
        return "python -m pytest"
    return cleaned


def _merge_files(files: list[CandidateTestFile]) -> list[CandidateTestFile]:
    merged: dict[str, CandidateTestFile] = {}
    for file in files:
        merged[file.path] = file
    return list(merged.values())


def _write_workspace_file(root: str, file: CandidateTestFile) -> None:
    path = _safe_relative_path(file.path)
    destination = os.path.abspath(os.path.join(root, *path.parts))
    root_abs = os.path.abspath(root)
    if not destination.startswith(root_abs + os.sep):
        raise TestRunnerError("Unsafe workspace path.")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(file.content)


def _safe_relative_path(path: str) -> PurePosixPath:
    cleaned = path.strip().replace("\\", "/")
    candidate = PurePosixPath(cleaned)
    if not cleaned or cleaned.startswith("/") or candidate.is_absolute() or ".." in candidate.parts:
        raise TestRunnerError("Unsafe workspace path.")
    if ":" in candidate.parts[0]:
        raise TestRunnerError("Unsafe workspace path.")
    return candidate


def _safe_env(workspace: str) -> dict[str, str]:
    env = {
        "PYTHONPATH": workspace,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def _sanitize_output(value: str) -> str:
    sanitized = value.replace("\r\n", "\n")
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: match.group(0).split("=")[0] + "=[redacted]" if "=" in match.group(0) else "[redacted]", sanitized)
    sanitized = re.sub(r"Traceback \(most recent call last\):[\s\S]*?(?=\n\n|$)", "[technical details hidden]", sanitized)
    return sanitized[-12000:]


def _parse_pytest_counts(output: str, return_code: int) -> dict[str, int]:
    passed = sum(int(match) for match in re.findall(r"(\d+)\s+passed", output))
    failed = sum(int(match) for match in re.findall(r"(\d+)\s+failed", output))
    errors = sum(int(match) for match in re.findall(r"(\d+)\s+errors?", output))
    total = passed + failed + errors
    if total == 0:
        total = 1
        failed = 0 if return_code == 0 else 1
        passed = 1 if return_code == 0 else 0
    return {"passed": passed, "failed": failed + errors, "total": total}


def _failure_summary(*, status: str, stdout: str, stderr: str, counts: dict[str, int]) -> str:
    if status == "passed":
        return ""
    combined = "\n".join(part for part in [stdout, stderr] if part).strip()
    for line in combined.splitlines():
        cleaned = line.strip()
        if cleaned.startswith("FAILED ") or "AssertionError" in cleaned or cleaned.startswith("E   "):
            return cleaned[:1000]
    if combined:
        return combined.splitlines()[-1][:1000]
    return f"{counts['failed']}/{counts['total']} tests failed."


def _safe_summary(*, status: str, command: str, counts: dict[str, int], failure_summary: str) -> str:
    if status == "passed":
        return f"{counts['passed']}/{counts['total']} tests passed with `{command}`."
    if status == "failed":
        return f"{counts['failed']}/{counts['total']} tests failed with `{command}`. {failure_summary}".strip()
    return failure_summary or f"Test run ended with status {status}."

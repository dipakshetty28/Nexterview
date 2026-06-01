from __future__ import annotations

import json
import os
import sys
from collections.abc import Generator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.interviews import get_scenario_generator
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Interview, Organization, OrganizationMember, ProjectFile, Scenario, ScenarioProject, User, UserRole
from app.schemas.scenario import GeneratedScenario
from app.services.scenario_generator import ScenarioGenerationResult, ScenarioGenerator, parse_generated_project_json
from app.services.scenario_seed_catalog import seed_scenarios
from app.services.test_runner import CandidateTestFile, CandidateTestRunner

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

_ = (Interview, Organization, OrganizationMember, ProjectFile, Scenario, ScenarioProject, User)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to a PostgreSQL database to run interview integration tests.")
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Interview integration tests must not run against SQLite.")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_admin(client: TestClient) -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "StrongPass123!",
            "full_name": "Example Owner",
            "organization_name": "Example Org",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _scenario_payload() -> GeneratedScenario:
    return GeneratedScenario.model_validate(
        {
            "title": "Debug duplicate webhook delivery handling",
            "role_title": "Backend Engineer",
            "seniority": "Senior",
            "interview_type": "Backend debugging",
            "difficulty": "Intermediate",
            "stack": ["Python", "FastAPI"],
            "language": "python",
            "framework": "FastAPI",
            "ai_mode": "Pair Programmer Mode",
            "business_context": (
                "The interview operations team receives duplicate webhook events from an assessment vendor, and "
                "candidate scores are being overwritten when retries arrive out of order."
            ),
            "technical_requirements": [
                "Add idempotent handling keyed by vendor event id.",
                "Reject stale score updates without breaking legitimate retries.",
                "Document the API response contract for ignored duplicates.",
            ],
            "visible_requirements": [
                "Add idempotent handling keyed by vendor event id.",
                "Reject stale score updates without breaking legitimate retries.",
            ],
            "starter_code": "def handle_webhook(event):\n    save_score(event.candidate_id, event.score)\n",
            "starter_files_json": [
                {
                    "path": "app/services/webhooks.py",
                    "language": "python",
                    "content": "def handle_webhook(event):\n    save_score(event.candidate_id, event.score)\n",
                }
            ],
            "test_files_json": [
                {
                    "path": "tests/test_webhooks.py",
                    "language": "python",
                    "content": "def test_duplicate_event_is_ignored():\n    assert True\n",
                }
            ],
            "expected_solution_files_json": [
                {
                    "path": "app/services/webhooks.py",
                    "language": "python",
                    "content": "def handle_webhook(event):\n    return {'status': 'deduped'}\n",
                }
            ],
            "expected_behavior": [
                "Duplicate events do not overwrite the existing score.",
                "Out-of-order retries are logged and ignored safely.",
            ],
            "logs_or_bug_report": "Bug report: score changed from 91 to 72 after vendor retried event evt_123.",
            "bug_description_internal": "Duplicate webhook events are not tracked before applying score writes.",
            "validation_command": "pytest",
            "constraints": ["Keep response shape stable."],
            "expected_solution_summary": "Persist or check vendor event ids before applying score updates.",
            "scenario_fit": "Backend debugging scenario for senior FastAPI candidates.",
            "hidden_evaluation_points": [
                "Checks candidate reasoning about idempotency and ordering.",
                "Rewards tests for duplicate and stale events.",
            ],
            "candidate_instructions": (
                "Use AI as a collaborator, validate the proposed change, and explain how the fix is verified."
            ),
            "interviewer_rubric": [
                "Correctly identifies duplicate delivery as the root cause.",
                "Implements a scoped persistence or lookup strategy for event ids.",
            ],
            "project": {
                "stack": ["Python", "FastAPI"],
                "project_name": "webhook-score-api",
                "description": "Repo-style webhook idempotency exercise.",
                "install_command": "pip install -r requirements.txt",
                "run_command": "uvicorn app.main:app --reload",
                "test_command": "pytest",
                "entrypoint": "app/main.py",
                "package_manager": "pip",
                "framework": "FastAPI",
                "files": [
                    {
                        "path": "app/main.py",
                        "content": "from app.services.webhooks import handle_webhook\n",
                        "language": "python",
                        "file_type": "source",
                        "is_editable": True,
                        "is_hidden": False,
                    },
                    {
                        "path": "app/services/webhooks.py",
                        "content": "def handle_webhook(event):\n    save_score(event.candidate_id, event.score)\n",
                        "language": "python",
                        "file_type": "source",
                        "is_editable": True,
                        "is_hidden": False,
                    },
                    {
                        "path": "data/events.json",
                        "content": "[{\"id\":\"evt_123\",\"score\":72}]\n",
                        "language": "json",
                        "file_type": "data",
                        "is_editable": True,
                        "is_hidden": False,
                    },
                    {
                        "path": "tests/test_webhooks.py",
                        "content": "def test_duplicate_event_is_ignored():\n    assert True\n",
                        "language": "python",
                        "file_type": "test",
                        "is_editable": True,
                        "is_hidden": False,
                    },
                    {
                        "path": "tests/test_hidden_webhooks.py",
                        "content": "def test_hidden_out_of_order_retry():\n    assert True\n",
                        "language": "python",
                        "file_type": "hidden_test",
                        "is_editable": False,
                        "is_hidden": True,
                    },
                    {
                        "path": "README.md",
                        "content": "# Webhook score API\n\nUse the Nexterview Run button to check your changes.\n",
                        "language": "markdown",
                        "file_type": "docs",
                        "is_editable": True,
                        "is_hidden": False,
                    },
                ],
            },
        }
    )


def _ai_project_payload() -> dict[str, object]:
    return {
        "scenario": {
            "title": "Repair invoice approval exports",
            "business_context": (
                "Finance managers export approved invoices into an accounting queue, but rejected invoices are "
                "sometimes included and totals are wrong for multi-line invoices."
            ),
            "candidate_task_summary": "Fix invoice totals and add an approval status filter to the export endpoint.",
            "bug_description": "The invoice total uses only the first line item and ignores additional line items.",
            "feature_request": "Add an optional status query parameter to filter invoice exports by approval status.",
            "expected_behavior": (
                "Invoice totals include every line item. The export endpoint filters invoices by status when requested."
            ),
            "validation_instructions": (
                "Use the Nexterview Run button to check invoice totals and approval status filtering."
            ),
            "candidate_instructions": (
                "Use the tests and seed data to verify the fix. Explain the root cause and how you validated it."
            ),
            "hidden_rubric": (
                "Candidate fixes the total calculation in the service. Candidate adds generic status filtering. "
                "Candidate does not hardcode approved invoices."
            ),
        },
        "project": {
            "project_name": "invoice-export-service",
            "stack": "Node.js + Express",
            "language": "typescript",
            "framework": "Express",
            "package_manager": "npm",
            "install_command": "npm install",
            "run_command": "npm run dev",
            "test_command": "npm test",
            "validation_command": "npm test",
            "entrypoint": "src/server.ts",
        },
        "files": [
            {
                "path": "package.json",
                "language": "json",
                "file_type": "config",
                "is_editable": True,
                "is_hidden": False,
                "content": "{\"scripts\":{\"dev\":\"tsx src/server.ts\",\"test\":\"vitest run\"}}\n",
            },
            {
                "path": "src/server.ts",
                "language": "typescript",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
                "content": "import express from 'express';\nimport { listInvoices } from './services/invoices';\n",
            },
            {
                "path": "src/services/invoices.ts",
                "language": "typescript",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
                "content": "export function total(invoice) { return invoice.lines[0].amount; }\n",
            },
            {
                "path": "src/data/invoices.json",
                "language": "json",
                "file_type": "data",
                "is_editable": True,
                "is_hidden": False,
                "content": "[{\"id\":\"inv_1\",\"status\":\"approved\",\"lines\":[{\"amount\":100},{\"amount\":50}]}]\n",
            },
            {
                "path": "tests/invoices.test.ts",
                "language": "typescript",
                "file_type": "test",
                "is_editable": True,
                "is_hidden": False,
                "content": "import { expect, test } from 'vitest';\ntest('totals all lines', () => expect(true).toBe(true));\n",
            },
            {
                "path": "tests/hidden-export.test.ts",
                "language": "typescript",
                "file_type": "hidden_test",
                "is_editable": False,
                "is_hidden": True,
                "content": "import { expect, test } from 'vitest';\ntest('hidden status filter', () => expect(true).toBe(true));\n",
            },
            {
                "path": "README.md",
                "language": "markdown",
                "file_type": "docs",
                "is_editable": True,
                "is_hidden": False,
                "content": "# Invoice export service\n\nUse the Nexterview Run button to check your changes.\n",
            },
        ],
        "expected_solution_files": [
            {
                "path": "src/services/invoices.ts",
                "language": "typescript",
                "content": "export function total(invoice) { return invoice.lines.reduce((sum, line) => sum + line.amount, 0); }\n",
            }
        ],
    }


def _java_spring_interview(*, interview_type: str = "Backend debugging") -> Interview:
    return Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Java", "Spring Boot", "PostgreSQL"],
        difficulty="Intermediate",
        interview_type=interview_type,
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness", "Debugging"],
        status="DRAFT",
    )


def _fastapi_interview() -> Interview:
    return Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Python", "FastAPI", "PostgreSQL"],
        difficulty="Intermediate",
        interview_type="Backend debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness", "Debugging"],
        status="DRAFT",
    )


def _seed_payload(key: str) -> dict[str, object]:
    return next(seed.payload for seed in seed_scenarios() if seed.key == key)


def _assert_java_spring_boot_scenario(scenario: GeneratedScenario) -> None:
    assert scenario.language == "java"
    assert scenario.framework == "Spring Boot"
    assert scenario.validation_command == "mvn test"
    assert scenario.project is not None
    paths = {project_file.path for project_file in scenario.project.files}
    visible_test_paths = {test_file.path for test_file in scenario.test_files_json}
    starter_paths = {starter_file.path for starter_file in scenario.starter_files_json}

    assert "pom.xml" in paths
    assert any(path.startswith("src/main/java/") and path.endswith(".java") for path in starter_paths)
    assert any(path.startswith("src/test/java/") and path.endswith(".java") for path in visible_test_paths)
    assert not any(path.endswith(".py") for path in paths)
    assert "requirements.txt" not in paths
    assert "app/main.py" not in paths
    assert "pytest" not in "\n".join(project_file.content.lower() for project_file in scenario.project.files)


def _runner_files_from_scenario(
    scenario: GeneratedScenario,
    *,
    use_expected_solution: bool = False,
) -> list[CandidateTestFile]:
    assert scenario.project is not None
    solution_by_path = {
        solution.path: solution
        for solution in scenario.expected_solution_files_json
    }
    files = []
    for project_file in scenario.project.files:
        if project_file.is_hidden:
            continue
        solution = solution_by_path.get(project_file.path) if use_expected_solution else None
        files.append(
            CandidateTestFile(
                path=project_file.path,
                content=solution.content if solution else project_file.content,
                language=solution.language if solution else project_file.language,
                file_type=project_file.file_type.value,
                is_hidden=False,
            )
        )
    return files


def _visible_runner_tests(files: list[CandidateTestFile]) -> list[CandidateTestFile]:
    return [file for file in files if file.file_type == "test" or "test" in file.path.lower()]


def test_create_interview_and_generate_scenario_with_mocked_ai_service(client: TestClient) -> None:
    token = _register_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/interviews",
        headers=headers,
        json={
            "role_title": "Backend Engineer",
            "seniority": "Senior",
            "stack": ["Python", "FastAPI", "PostgreSQL"],
            "difficulty": "Intermediate",
            "interview_type": "Backend debugging",
            "duration_minutes": 75,
            "allowed_ai_mode": "Pair Programmer Mode",
            "evaluation_criteria": ["Correctness", "Debugging", "AI validation"],
        },
    )
    assert create_response.status_code == 201
    interview = create_response.json()
    assert interview["status"] == "DRAFT"
    assert interview["scenario"] is None

    class StubScenarioGenerator:
        def generate(self, interview: Interview) -> ScenarioGenerationResult:
            assert interview.role_title == "Backend Engineer"
            return ScenarioGenerationResult(scenario=_scenario_payload(), source="openai", model="test-model")

    app.dependency_overrides[get_scenario_generator] = lambda: StubScenarioGenerator()
    generate_response = client.post(f"/api/interviews/{interview['id']}/generate-scenario", headers=headers)
    assert generate_response.status_code == 200
    scenario = generate_response.json()
    assert scenario["title"] == "Debug duplicate webhook delivery handling"
    assert scenario["generation_source"] == "openai"
    assert scenario["ai_model"] == "test-model"
    assert scenario["role_title"] == "Backend Engineer"
    assert scenario["language"] == "python"
    assert scenario["framework"] == "FastAPI"
    assert scenario["visible_requirements"]
    assert scenario["hidden_evaluation_points"][0].startswith("Checks candidate")
    assert scenario["project"]["project_name"] == "webhook-score-api"
    assert len(scenario["project"]["files"]) == 6
    assert any(project_file["is_hidden"] for project_file in scenario["project"]["files"])

    detail_response = client.get(f"/api/interviews/{interview['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "READY"
    assert detail["scenario"]["title"] == "Debug duplicate webhook delivery handling"

    list_response = client.get("/api/interviews", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(f"/api/interviews/{interview['id']}", headers=headers)
    assert delete_response.status_code == 204

    deleted_detail_response = client.get(f"/api/interviews/{interview['id']}", headers=headers)
    assert deleted_detail_response.status_code == 404
    deleted_list_response = client.get("/api/interviews", headers=headers)
    assert deleted_list_response.status_code == 200
    assert deleted_list_response.json() == []


def test_scenario_generator_parses_mocked_ai_project_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "test-model")

    class FakeResponses:
        def create(self, **_: object) -> SimpleNamespace:
            return SimpleNamespace(output_text=json.dumps(_ai_project_payload()))

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Node.js", "Express", "TypeScript"],
        difficulty="Intermediate",
        interview_type="API debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness", "API design"],
        status="DRAFT",
    )

    result = ScenarioGenerator().generate(interview)

    assert result.source == "openai"
    assert result.model == "test-model"
    assert result.scenario.title == "Repair invoice approval exports"
    assert result.scenario.project is not None
    assert result.scenario.project.project_name == "invoice-export-service"
    assert result.scenario.language == "typescript"
    assert result.scenario.expected_solution_files_json[0].path == "src/services/invoices.ts"
    assert len(result.scenario.project.files) == 7
    assert any(project_file.file_type.value == "data" for project_file in result.scenario.project.files)
    assert any(project_file.is_hidden for project_file in result.scenario.project.files)


def test_java_spring_boot_generation_returns_java_project_when_openai_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")

    result = ScenarioGenerator().generate(_java_spring_interview())

    assert result.source == "fallback"
    assert result.model is None
    _assert_java_spring_boot_scenario(result.scenario)
    assert "pagination" in result.scenario.bug_description.lower()


def test_python_fastapi_selection_still_returns_python_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")

    result = ScenarioGenerator().generate(_fastapi_interview())

    assert result.source == "fallback"
    assert result.scenario.language == "python"
    assert result.scenario.framework == "FastAPI"
    assert result.scenario.validation_command in {"pytest", "python -m pytest"}
    assert result.scenario.project is not None
    paths = {project_file.path for project_file in result.scenario.project.files}
    assert "app/main.py" in paths
    assert any(path.endswith(".py") for path in paths)
    assert not any(path.startswith("src/main/java/") for path in paths)


def test_python_seed_starter_fails_and_expected_solution_passes_real_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-not-leak")
    scenario = parse_generated_project_json(json.dumps(_seed_payload("orders-review")), interview=_fastapi_interview())
    runner = CandidateTestRunner(timeout_seconds=15)
    starter_files = _runner_files_from_scenario(scenario)
    fixed_files = _runner_files_from_scenario(scenario, use_expected_solution=True)

    starter_result = runner.run_candidate_tests(
        scenario=scenario,  # type: ignore[arg-type]
        candidate_files=starter_files,
        visible_tests=_visible_runner_tests(starter_files),
    )
    fixed_result = runner.run_candidate_tests(
        scenario=scenario,  # type: ignore[arg-type]
        candidate_files=fixed_files,
        visible_tests=_visible_runner_tests(fixed_files),
    )

    assert starter_result.status == "failed"
    assert starter_result.failed_count >= 1
    assert fixed_result.status == "passed"
    assert fixed_result.passed_count >= 2
    assert "sk-test-should-not-leak" not in starter_result.stdout
    assert "sk-test-should-not-leak" not in starter_result.stderr


def test_test_runner_timeout_is_reported() -> None:
    runner = CandidateTestRunner(timeout_seconds=1)
    scenario = parse_generated_project_json(json.dumps(_seed_payload("orders-review")), interview=_fastapi_interview())
    files = [
        CandidateTestFile(path="app/main.py", content="def health():\n    return 'ok'\n", language="python", file_type="source"),
        CandidateTestFile(path="app/data/orders.json", content="[]\n", language="json", file_type="data"),
        CandidateTestFile(path="tests/test_timeout.py", content="import time\n\ndef test_timeout():\n    time.sleep(5)\n", language="python", file_type="test"),
        CandidateTestFile(path="README.md", content="# Timeout\n", language="markdown", file_type="docs"),
    ]

    result = runner.run_candidate_tests(
        scenario=scenario,  # type: ignore[arg-type]
        candidate_files=files,
        visible_tests=_visible_runner_tests(files),
    )

    assert result.status == "timeout"
    assert "timed out" in result.failure_summary


def test_wrong_language_ai_output_retries_then_uses_java_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "test-model")
    wrong_language_payload = _seed_payload("fastapi-pagination")
    calls: list[int] = []

    class FakeResponses:
        def create(self, **_: object) -> SimpleNamespace:
            calls.append(1)
            return SimpleNamespace(output_text=json.dumps(wrong_language_payload))

    class FakeOpenAI:
        def __init__(self, **_: object) -> None:
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    result = ScenarioGenerator().generate(_java_spring_interview())

    assert len(calls) == 2
    assert result.source == "fallback"
    assert result.model == "test-model"
    _assert_java_spring_boot_scenario(result.scenario)


def test_java_spring_boot_parser_rejects_python_project() -> None:
    with pytest.raises(Exception):
        parse_generated_project_json(json.dumps(_seed_payload("fastapi-pagination")), interview=_java_spring_interview())


def test_project_json_parser_rejects_missing_data_file() -> None:
    payload = _ai_project_payload()
    payload["files"] = [
        project_file for project_file in payload["files"] if project_file["file_type"] != "data"  # type: ignore[index]
    ]
    interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Node.js", "Express"],
        difficulty="Intermediate",
        interview_type="API debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness"],
        status="DRAFT",
    )

    with pytest.raises(Exception):
        parse_generated_project_json(json.dumps(payload), interview=interview)


def test_project_json_parser_rejects_missing_expected_solution() -> None:
    payload = _ai_project_payload()
    payload.pop("expected_solution_files")
    interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Node.js", "Express"],
        difficulty="Intermediate",
        interview_type="API debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness"],
        status="DRAFT",
    )

    with pytest.raises(Exception):
        parse_generated_project_json(json.dumps(payload), interview=interview)


def test_project_json_parser_rejects_candidate_setup_commands() -> None:
    payload = _ai_project_payload()
    payload["scenario"]["validation_instructions"] = "Run npm test before submitting."  # type: ignore[index]
    interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Node.js", "Express"],
        difficulty="Intermediate",
        interview_type="API debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness"],
        status="DRAFT",
    )

    with pytest.raises(Exception):
        parse_generated_project_json(json.dumps(payload), interview=interview)


def test_candidate_role_cannot_create_interviews(client: TestClient) -> None:
    _ = _register_admin(client)
    response = client.post(
        "/api/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "StrongPass123!",
            "full_name": "Candidate User",
            "organization_name": "Candidate Org",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        candidate = db.query(User).filter(User.email == "candidate@example.com").one()
        candidate.role = UserRole.CANDIDATE
        for membership in candidate.memberships:
            membership.role = UserRole.CANDIDATE
        db.commit()
    finally:
        db.close()

    forbidden_response = client.post(
        "/api/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "role_title": "Backend Engineer",
            "seniority": "Senior",
            "stack": ["Python"],
            "difficulty": "Intermediate",
            "interview_type": "Backend debugging",
            "duration_minutes": 75,
            "allowed_ai_mode": "Pair Programmer Mode",
            "evaluation_criteria": ["Correctness"],
        },
    )
    assert forbidden_response.status_code == 403


def test_scenario_generator_falls_back_without_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="AI Platform Engineer",
        seniority="Staff",
        stack=["Python", "LangChain", "PostgreSQL"],
        difficulty="Advanced",
        interview_type="AI engineering",
        duration_minutes=90,
        allowed_ai_mode="Senior Engineer Mode",
        evaluation_criteria=["AI validation", "Architecture", "Correctness"],
        status="DRAFT",
    )

    result = ScenarioGenerator().generate(interview)

    assert result.source == "fallback"
    assert result.model is None
    assert result.scenario.project is not None
    assert "retrieval" in result.scenario.title.lower() or "rag" in result.scenario.project.project_name
    assert result.scenario.language == "python"
    assert result.scenario.framework == "RAG"
    assert result.scenario.expected_solution_files_json
    assert result.scenario.validation_command
    assert "install" not in result.scenario.validation_instructions.lower()
    assert "pytest" not in result.scenario.validation_instructions.lower()
    paths = {project_file.path for project_file in result.scenario.project.files}
    assert {"app/retrieval.py", "app/data/documents.json", "tests/test_retrieval.py", "README.md"} <= paths
    readme = next(project_file for project_file in result.scenario.project.files if project_file.path == "README.md")
    assert "pip install" not in readme.content
    assert "pytest" not in readme.content
    assert result.scenario.hidden_evaluation_points


def test_seed_catalog_contains_executable_private_solutions() -> None:
    seeds = seed_scenarios()
    assert len(seeds) >= 8
    assert any(seed.key == "fastapi-pagination" for seed in seeds)
    assert sum(1 for seed in seeds if seed.target_kind == "java_spring_boot") >= 3
    assert any(seed.key == "spring-boot-pagination" for seed in seeds)
    assert any(seed.key == "spring-boot-validation" for seed in seeds)
    assert any(seed.key == "spring-boot-org-access" for seed in seeds)
    assert any(seed.key == "rag-metadata" for seed in seeds)
    assert any(seed.key == "security-org-access" for seed in seeds)

    for seed in seeds:
        payload = seed.payload
        envelope = parse_generated_project_json(json.dumps(payload), interview=Interview(
            id=uuid4(),
            organization_id=uuid4(),
            created_by_id=uuid4(),
            role_title="Seed Reviewer",
            seniority="Senior",
            stack=["Python", "TypeScript", "FastAPI", "React"],
            difficulty="Intermediate",
            interview_type="Seed validation",
            duration_minutes=75,
            allowed_ai_mode="Pair Programmer Mode",
            evaluation_criteria=["Correctness"],
            status="DRAFT",
        ))
        assert envelope.expected_solution_files_json
        assert envelope.test_files_json
        visible_tests = "\n".join(test_file.content for test_file in envelope.test_files_json)
        assert "assert" in visible_tests or "expect(" in visible_tests or "andExpect(" in visible_tests
        starter_by_path = {file_payload.path: file_payload.content for file_payload in envelope.starter_files_json}
        assert any(starter_by_path.get(solution.path) != solution.content for solution in envelope.expected_solution_files_json)


def test_fallback_scenarios_are_role_and_stack_matched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    frontend_interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Frontend React Engineer",
        seniority="Senior",
        stack=["React", "Next.js", "TypeScript"],
        difficulty="Intermediate",
        interview_type="Frontend hydration bug",
        duration_minutes=60,
        allowed_ai_mode="Debugging Assistant Mode",
        evaluation_criteria=["Correctness"],
        status="DRAFT",
    )
    security_interview = Interview(
        id=uuid4(),
        organization_id=uuid4(),
        created_by_id=uuid4(),
        role_title="Backend Security Engineer",
        seniority="Staff",
        stack=["Python", "FastAPI", "Auth"],
        difficulty="Advanced",
        interview_type="Security review task",
        duration_minutes=90,
        allowed_ai_mode="Senior Engineer Mode",
        evaluation_criteria=["Security", "Correctness"],
        status="DRAFT",
    )

    frontend = ScenarioGenerator().generate(frontend_interview).scenario
    security = ScenarioGenerator().generate(security_interview).scenario

    assert frontend.framework == "Next.js"
    assert "hydration" in frontend.title.lower()
    assert security.framework == "FastAPI"
    assert "organization" in security.bug_description.lower()
    assert frontend.title != security.title

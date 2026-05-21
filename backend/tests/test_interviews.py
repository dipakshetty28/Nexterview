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
            "business_context": (
                "The interview operations team receives duplicate webhook events from an assessment vendor, and "
                "candidate scores are being overwritten when retries arrive out of order."
            ),
            "technical_requirements": [
                "Add idempotent handling keyed by vendor event id.",
                "Reject stale score updates without breaking legitimate retries.",
                "Document the API response contract for ignored duplicates.",
            ],
            "starter_code": "def handle_webhook(event):\n    save_score(event.candidate_id, event.score)\n",
            "expected_behavior": [
                "Duplicate events do not overwrite the existing score.",
                "Out-of-order retries are logged and ignored safely.",
            ],
            "logs_or_bug_report": "Bug report: score changed from 91 to 72 after vendor retried event evt_123.",
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
                        "content": "# Webhook score API\n\nRun pytest.\n",
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
            "validation_instructions": "Run npm test. Call GET /invoices?status=approved during manual validation.",
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
            "framework": "Express",
            "package_manager": "npm",
            "install_command": "npm install",
            "run_command": "npm run dev",
            "test_command": "npm test",
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
                "content": "# Invoice export service\n\nRun npm test.\n",
            },
        ],
    }


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
    assert len(result.scenario.project.files) == 7
    assert any(project_file.file_type.value == "data" for project_file in result.scenario.project.files)
    assert any(project_file.is_hidden for project_file in result.scenario.project.files)


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
    assert result.scenario.title == "Fix order totals and add status filtering"
    assert result.scenario.project is not None
    assert result.scenario.project.project_name == "orders-review-api"
    assert {project_file.path for project_file in result.scenario.project.files} >= {
        "app/main.py",
        "app/services/orders.py",
        "app/data/orders.json",
        "tests/test_orders.py",
        "README.md",
    }
    assert result.scenario.hidden_evaluation_points

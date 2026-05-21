from __future__ import annotations

import os
from collections.abc import Generator
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
from app.models import Interview, Organization, OrganizationMember, Scenario, User, UserRole
from app.schemas.scenario import GeneratedScenario
from app.services.scenario_generator import ScenarioGenerationResult, ScenarioGenerator

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

_ = (Interview, Organization, OrganizationMember, Scenario, User)


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
        }
    )


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

    detail_response = client.get(f"/api/interviews/{interview['id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["status"] == "READY"
    assert detail["scenario"]["title"] == "Debug duplicate webhook delivery handling"

    list_response = client.get("/api/interviews", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


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
    assert "RAG" in result.scenario.title
    assert result.scenario.hidden_evaluation_points

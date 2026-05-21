from __future__ import annotations

import os
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Interview, InterviewSession, InviteToken, Organization, OrganizationMember, Scenario, User, UserRole

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

_ = (Interview, InterviewSession, InviteToken, Organization, OrganizationMember, Scenario, User)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to a PostgreSQL database to run invite integration tests.")
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Invite integration tests must not run against SQLite.")

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


def _create_candidate(client: TestClient, *, email: str, full_name: str) -> None:
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        organization = db.execute(select(Organization).where(Organization.slug == "example-org")).scalar_one()
        candidate = User(
            email=email,
            full_name=full_name,
            role=UserRole.CANDIDATE,
            hashed_password=hash_password("StrongPass123!"),
            is_active=True,
        )
        db.add(candidate)
        db.flush()
        db.add(OrganizationMember(organization_id=organization.id, user_id=candidate.id, role=UserRole.CANDIDATE))
        db.commit()
    finally:
        db.close()


def _create_ready_interview(client: TestClient, *, token: str) -> str:
    create_response = client.post(
        "/api/interviews",
        headers={"Authorization": f"Bearer {token}"},
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
    interview_id = create_response.json()["id"]
    scenario_response = client.post(
        f"/api/interviews/{interview_id}/generate-scenario",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scenario_response.status_code == 200
    return interview_id


def test_interviewer_invites_candidate_and_candidate_starts_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token = _register_admin(client)
    _create_candidate(client, email="candidate@example.com", full_name="Candidate User")
    interview_id = _create_ready_interview(client, token=admin_token)

    invite_response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "candidate@example.com"},
    )
    assert invite_response.status_code == 201
    invite = invite_response.json()
    assert invite["candidate_email"] == "candidate@example.com"
    assert invite["session_id"]
    raw_invite_token = urlparse(invite["invite_url"]).path.rsplit("/", 1)[-1]

    public_response = client.get(f"/api/invite/{raw_invite_token}")
    assert public_response.status_code == 200
    public_invite = public_response.json()
    assert public_invite["candidate_email"] == "candidate@example.com"
    assert public_invite["status"] == "invited"
    assert public_invite["interview"]["scenario_title"]

    unauthenticated_start = client.post(f"/api/invite/{raw_invite_token}/start")
    assert unauthenticated_start.status_code == 401

    candidate_login = client.post(
        "/api/auth/login",
        json={"email": "candidate@example.com", "password": "StrongPass123!"},
    )
    assert candidate_login.status_code == 200
    candidate_token = candidate_login.json()["access_token"]

    start_response = client.post(
        f"/api/invite/{raw_invite_token}/start",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert start_response.status_code == 200
    session = start_response.json()
    assert session["status"] == "started"
    assert session["interview_id"] == interview_id
    assert session["scenario"]["candidate_instructions"]
    assert "hidden_evaluation_points" not in session["scenario"]
    assert "interviewer_rubric" not in session["scenario"]

    session_response = client.get(
        f"/api/sessions/{session['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert session_response.status_code == 200
    assert session_response.json()["id"] == session["id"]

    admin_session_response = client.get(
        f"/api/sessions/{session['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_session_response.status_code == 403


def test_invite_rejects_unknown_candidate(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token = _register_admin(client)
    interview_id = _create_ready_interview(client, token=admin_token)

    response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "missing@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No active candidate account with that email exists in this organization."

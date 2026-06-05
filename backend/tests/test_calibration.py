from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User, UserRole

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a PostgreSQL database to run calibration integration tests.",
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    assert TEST_DATABASE_URL is not None
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Calibration integration tests must not run against SQLite.")

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


def _register_user(client: TestClient, *, email: str = "owner@example.com") -> str:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "StrongPass123!",
            "full_name": "Example User",
            "organization_name": "Example Org",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def _set_role(email: str, role: UserRole) -> None:
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = db.query(User).filter(User.email == email).one()
        user.role = role
        for membership in user.memberships:
            membership.role = role
        db.commit()
    finally:
        db.close()


def test_admin_can_read_curated_calibration_sessions(client: TestClient) -> None:
    token = _register_user(client)

    response = client.get("/api/calibration", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    sessions = response.json()
    assert [session["tier"] for session in sessions] == ["strong", "average", "weak"]
    assert all(session["status"] == "reviewed" for session in sessions)
    assert all(session["final_code"] for session in sessions)
    assert all(session["test_result"]["summary"] for session in sessions)
    assert all(session["ai_transcript"] for session in sessions)
    assert all(session["agent_reviews"] for session in sessions)
    assert all(session["expected_behavior"] for session in sessions)
    assert all(session["observed_behavior"] for session in sessions)
    assert all(session["differentiators"] for session in sessions)
    serialized = response.text.lower()
    assert "hidden_evaluation_points" not in serialized
    assert "interviewer_rubric" not in serialized
    assert "system prompt" not in serialized
    assert "github" not in serialized


def test_interviewer_can_read_calibration_sessions(client: TestClient) -> None:
    token = _register_user(client, email="interviewer@example.com")
    _set_role("interviewer@example.com", UserRole.INTERVIEWER)

    response = client.get("/api/calibration", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_candidate_cannot_read_calibration_sessions(client: TestClient) -> None:
    token = _register_user(client, email="candidate@example.com")
    _set_role("candidate@example.com", UserRole.CANDIDATE)

    response = client.get("/api/calibration", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403

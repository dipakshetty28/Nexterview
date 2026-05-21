from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Organization, OrganizationMember, User, UserRole

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a PostgreSQL database to run interview integration tests.",
)


@pytest.fixture()
def client_and_session() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    assert TEST_DATABASE_URL is not None
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Interview integration tests must not run against SQLite.")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

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
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(db: Session, *, email: str, role: UserRole, organization: Organization) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0].replace(".", " ").title(),
        role=role,
        hashed_password=hash_password("StrongPass123!"),
    )
    db.add(user)
    db.flush()
    db.add(OrganizationMember(organization=organization, user=user, role=role))
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _interview_payload() -> dict[str, Any]:
    return {
        "title": "Backend Debugging Loop",
        "role_title": "Senior Backend Engineer",
        "seniority": "SENIOR",
        "stack": ["Python", "FastAPI", "PostgreSQL"],
        "interview_type": "BACKEND_DEBUGGING",
        "difficulty": "HARD",
        "duration_minutes": 75,
        "ai_mode": "DEBUGGING_ASSISTANT",
        "scenario": {
            "title": "Retry loop creates duplicate payments",
            "business_context": "A payments service creates duplicate transactions when processor timeouts happen during retries.",
            "candidate_instructions": "Find the root cause, describe the idempotency bug, and outline validation steps.",
            "technical_requirements": "Preserve idempotency keys across retries and prevent duplicate transaction records.",
            "evaluation_rubric": "Look for root-cause analysis, tests, database safeguards, and clear tradeoff communication.",
        },
    }


def test_interviewer_can_manage_only_organization_interviews(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    db = SessionLocal()
    try:
        org_one = Organization(name="Org One", slug="org-one")
        org_two = Organization(name="Org Two", slug="org-two")
        db.add_all([org_one, org_two])
        db.flush()
        interviewer = _create_user(db, email="interviewer@org-one.test", role=UserRole.INTERVIEWER, organization=org_one)
        other_interviewer = _create_user(
            db,
            email="interviewer@org-two.test",
            role=UserRole.INTERVIEWER,
            organization=org_two,
        )
        candidate = _create_user(db, email="candidate@org-one.test", role=UserRole.CANDIDATE, organization=org_one)
        db.commit()
    finally:
        db.close()

    create_response = client.post("/api/interviews", json=_interview_payload(), headers=_headers(interviewer))
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "Backend Debugging Loop"
    assert created["organization"]["slug"] == "org-one"
    assert created["session_count"] == 0
    assert created["scenarios"][0]["title"] == "Retry loop creates duplicate payments"

    interview_id = created["id"]

    list_response = client.get("/api/interviews", headers=_headers(interviewer))
    assert list_response.status_code == 200
    assert [interview["id"] for interview in list_response.json()["interviews"]] == [interview_id]

    detail_response = client.get(f"/api/interviews/{interview_id}", headers=_headers(interviewer))
    assert detail_response.status_code == 200
    assert detail_response.json()["role_title"] == "Senior Backend Engineer"

    patch_response = client.patch(
        f"/api/interviews/{interview_id}",
        json={"title": "Updated Backend Debugging Loop", "status": "ACTIVE"},
        headers=_headers(interviewer),
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Backend Debugging Loop"
    assert patch_response.json()["status"] == "ACTIVE"

    forbidden_org_response = client.get(f"/api/interviews/{interview_id}", headers=_headers(other_interviewer))
    assert forbidden_org_response.status_code == 404

    candidate_response = client.post("/api/interviews", json=_interview_payload(), headers=_headers(candidate))
    assert candidate_response.status_code == 403

    delete_response = client.delete(f"/api/interviews/{interview_id}", headers=_headers(interviewer))
    assert delete_response.status_code == 204

    empty_list_response = client.get("/api/interviews", headers=_headers(interviewer))
    assert empty_list_response.status_code == 200
    assert empty_list_response.json()["interviews"] == []

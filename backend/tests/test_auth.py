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
from app.models import Organization, OrganizationMember, User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a PostgreSQL database to run auth integration tests.",
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    assert TEST_DATABASE_URL is not None
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Auth integration tests must not run against SQLite.")

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


def test_register_login_and_current_user(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "OWNER@Example.com",
            "password": "StrongPass123!",
            "full_name": "Example Owner",
            "organization_name": "Example Org",
        },
    )

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["token_type"] == "bearer"
    assert registered["access_token"]
    assert registered["user"]["email"] == "owner@example.com"
    assert registered["user"]["role"] == "ADMIN"
    assert registered["user"]["organizations"][0]["organization"]["name"] == "Example Org"
    assert "hashed_password" not in registered["user"]

    duplicate_response = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "StrongPass123!",
            "full_name": "Duplicate Owner",
            "organization_name": "Duplicate Org",
        },
    )
    assert duplicate_response.status_code == 409

    login_response = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    current_user_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert current_user_response.status_code == 200
    assert current_user_response.json()["email"] == "owner@example.com"

    dashboard_response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["user"]["role"] == "ADMIN"


def test_current_user_requires_valid_bearer_token(client: TestClient) -> None:
    missing_token_response = client.get("/api/auth/me")
    assert missing_token_response.status_code == 401

    invalid_token_response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
    assert invalid_token_response.status_code == 401

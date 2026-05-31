from __future__ import annotations

import os
from collections.abc import Generator
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.api.candidate import get_candidate_copilot, get_github_submission_publisher
from app.api.interviews import get_github_project_publisher
from app.api.reviews import get_review_agent_runner
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    AgentReview,
    AIMessage,
    AIMessageRole,
    Interview,
    InterviewSession,
    InterviewSessionStatus,
    InviteToken,
    Organization,
    OrganizationMember,
    ProjectFile,
    Scenario,
    ScenarioProject,
    Score,
    SessionFileSnapshot,
    Submission,
    TelemetryEvent,
    TelemetryEventType,
    User,
    UserRole,
)
from app.services.copilot import CopilotResult
from app.services.github import GitHubSubmissionPushResult
from app.services.review_agents import AGENT_DEFINITIONS, AgentReviewResult, generate_file_diffs

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

_ = (
    AIMessage,
    AgentReview,
    Interview,
    InterviewSession,
    InviteToken,
    Organization,
    OrganizationMember,
    ProjectFile,
    Scenario,
    ScenarioProject,
    Score,
    SessionFileSnapshot,
    Submission,
    TelemetryEvent,
    User,
)


_SUBMISSION_TRANSPORT_FIELDS = {
    "branch_name",
    "base_branch_name",
    "commit_sha",
    "repository_url",
    "pull_request_url",
    "push_status",
    "push_error",
}


def _assert_no_submission_transport_fields(payload: dict[str, object]) -> None:
    for field in _SUBMISSION_TRANSPORT_FIELDS:
        assert field not in payload


@pytest.fixture(autouse=True)
def _disable_github_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "github_token", "")
    monkeypatch.setattr(settings, "github_owner", "")
    monkeypatch.setattr(settings, "github_repo", "")
    monkeypatch.setattr(settings, "github_default_branch", "main")
    monkeypatch.setattr(settings, "github_create_pr", False)


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


def _create_ready_interview(
    client: TestClient,
    *,
    token: str,
    role_title: str = "Backend Engineer",
    stack: list[str] | None = None,
    interview_type: str = "Backend debugging",
) -> str:
    create_response = client.post(
        "/api/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "role_title": role_title,
            "seniority": "Senior",
            "stack": stack or ["Python", "FastAPI", "PostgreSQL"],
            "difficulty": "Intermediate",
            "interview_type": interview_type,
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


def test_scenario_generation_publishes_starter_branch_when_github_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token = _register_admin(client)
    create_response = client.post(
        "/api/interviews",
        headers={"Authorization": f"Bearer {admin_token}"},
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

    class StubProjectPublisher:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def publish_scenario_project(self, **kwargs: object) -> GitHubSubmissionPushResult:
            assert str(kwargs["interview_id"]) == interview_id
            files = kwargs["files"]
            assert isinstance(files, list)
            self.paths = sorted(file.path for file in files)
            return GitHubSubmissionPushResult(
                status="pushed",
                branch_name="scenario-interview-starter",
                commit_sha="starter123",
                repository_url="https://github.com/example/repo",
            )

    publisher = StubProjectPublisher()
    app.dependency_overrides[get_github_project_publisher] = lambda: publisher
    scenario_response = client.post(
        f"/api/interviews/{interview_id}/generate-scenario",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert scenario_response.status_code == 200
    project = scenario_response.json()["project"]
    assert project["starter_push_status"] == "pushed"
    assert project["starter_branch_name"] == "scenario-interview-starter"
    assert project["starter_commit_sha"] == "starter123"
    assert project["starter_repository_url"] == "https://github.com/example/repo"
    assert "app/main.py" in publisher.paths
    assert "tests/test_orders_hidden.py" in publisher.paths


def _start_workspace_session(client: TestClient, *, candidate_email: str) -> tuple[str, str, dict[str, object], dict[str, object]]:
    admin_token = _register_admin(client)
    _create_candidate(client, email=candidate_email, full_name="Workspace Candidate")
    interview_id = _create_ready_interview(client, token=admin_token)
    invite_response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": candidate_email},
    )
    assert invite_response.status_code == 201
    raw_invite_token = urlparse(invite_response.json()["invite_url"]).path.rsplit("/", 1)[-1]
    candidate_login = client.post(
        "/api/auth/login",
        json={"email": candidate_email, "password": "StrongPass123!"},
    )
    assert candidate_login.status_code == 200
    candidate_token = candidate_login.json()["access_token"]
    start_response = client.post(
        f"/api/invite/{raw_invite_token}/start",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert start_response.status_code == 200
    session = start_response.json()
    workspace_response = client.get(
        f"/api/sessions/{session['id']}/workspace",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert workspace_response.status_code == 200
    return admin_token, candidate_token, session, workspace_response.json()


def _fix_order_workspace(client: TestClient, *, candidate_token: str, session_id: str, workspace: dict[str, object]) -> None:
    files_by_path = {workspace_file["path"]: workspace_file for workspace_file in workspace["files"]}  # type: ignore[index]
    service_file = files_by_path["app/services/orders.py"]
    main_file = files_by_path["app/main.py"]
    fixed_service = service_file["current_content"].replace(
        'return round(sum(item["unit_price"] for item in order["items"]), 2)',
        'return round(sum(item["unit_price"] * item["quantity"] for item in order["items"]), 2)',
    )
    service_update_response = client.put(
        f"/api/sessions/{session_id}/files/{service_file['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"content": fixed_service},
    )
    assert service_update_response.status_code == 200

    fixed_main = main_file["current_content"].replace(
        "def list_orders() -> list[dict[str, object]]:\n"
        "    return [summarize_order(order) for order in load_orders()]\n",
        "def list_orders(status: str | None = None) -> list[dict[str, object]]:\n"
        "    orders = load_orders()\n"
        "    if status is not None:\n"
        "        orders = [order for order in orders if order[\"status\"] == status]\n"
        "    return [summarize_order(order) for order in orders]\n",
    )
    main_update_response = client.put(
        f"/api/sessions/{session_id}/files/{main_file['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"content": fixed_main},
    )
    assert main_update_response.status_code == 200


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
    assert "hidden_rubric" not in session["scenario"]
    assert "interviewer_rubric" not in session["scenario"]
    assert "expected_solution_files_json" not in session["scenario"]
    assert "bug_description_internal" not in session["scenario"]
    assert "expected_solution_summary" not in session["scenario"]
    assert session["scenario"]["visible_requirements"]
    assert session["scenario"]["starter_files_json"]
    assert session["scenario"]["language"]
    assert session["scenario"]["framework"]
    assert session["scenario"]["project"]["project_name"] == "orders-review-api"
    assert session["scenario"]["project"]["install_command"] is None
    assert session["scenario"]["project"]["run_command"] is None
    assert session["scenario"]["project"]["test_command"] is None
    assert "starter_branch_name" not in session["scenario"]["project"]
    assert "starter_repository_url" not in session["scenario"]["project"]
    assert "starter_push_status" not in session["scenario"]["project"]
    assert "install" not in session["scenario"]["validation_instructions"].lower()
    assert "pytest" not in session["scenario"]["validation_instructions"].lower()
    candidate_files = session["scenario"]["project"]["files"]
    assert candidate_files
    assert all(project_file["is_editable"] is True for project_file in candidate_files)
    assert {project_file["path"] for project_file in candidate_files} >= {
        "app/main.py",
        "app/services/orders.py",
        "app/data/orders.json",
        "tests/test_orders.py",
        "README.md",
    }
    assert "tests/test_orders_hidden.py" not in {project_file["path"] for project_file in candidate_files}

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

    session_started_response = client.post(
        f"/api/sessions/{session['id']}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "session_started", "payload": {}},
    )
    assert session_started_response.status_code == 201
    assert session_started_response.json()["event_type"] == "session_started"

    edited_code = (
        "def handle_webhook(event):\n"
        "    try:\n"
        "        if event.id in processed_duplicate_events:\n"
        "            return {'status': 'duplicate'}\n"
        "        return save_score(event.candidate_id, event.score)\n"
        "    except Exception as error:\n"
        "        raise error\n"
    )
    code_event_response = client.post(
        f"/api/sessions/{session['id']}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "code_edit", "payload": {"code": edited_code}},
    )
    assert code_event_response.status_code == 201
    assert code_event_response.json()["payload"]["code_length"] == len(edited_code)

    notes = "Root cause: duplicate webhook retries overwrite scores without idempotency."
    note_event_response = client.post(
        f"/api/sessions/{session['id']}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "note_updated", "payload": {"notes": notes}},
    )
    assert note_event_response.status_code == 201
    assert note_event_response.json()["payload"]["note_length"] == len(notes)

    autosaved_session_response = client.get(
        f"/api/sessions/{session['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert autosaved_session_response.status_code == 200
    autosaved_session = autosaved_session_response.json()
    assert autosaved_session["latest_code"] == edited_code
    assert autosaved_session["notes"] == notes

    test_run_response = client.post(
        f"/api/sessions/{session['id']}/run-tests",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"code": edited_code},
    )
    assert test_run_response.status_code == 200
    test_run = test_run_response.json()
    assert test_run["status"] == "passed"
    assert test_run["cases"]

    session_id = session["id"]

    class StubCopilot:
        def __init__(self) -> None:
            self.calls = 0

        def generate_reply(
            self,
            *,
            session: InterviewSession,
            question: str,
            context: dict[str, object],
            previous_messages: list[AIMessage],
        ) -> CopilotResult:
            assert str(session.id) == session_id
            assert "idempotency" in question.lower()
            assert "hidden_rubric" not in context
            assert "hidden_evaluation_points" not in context
            assert "interviewer_rubric" not in context
            assert "tests/test_orders_hidden.py" not in str(context)
            assert "app/main.py" in context["visible_project_file_tree"]
            assert "app/services/orders.py" in context["visible_project_file_tree"]
            assert context["latest_test_output"] == test_run["output"]
            current_file = context["current_file"]
            assert isinstance(current_file, dict)
            assert current_file["path"] == "app/main.py"
            assert "Root cause" in str(context["candidate_notes"])
            if self.calls == 0:
                assert previous_messages == []
                content = "Try extracting the idempotency key before the retry loop.\n\n```python\nkey = invoice_id\n```"
            else:
                assert [message.role for message in previous_messages] == [AIMessageRole.USER, AIMessageRole.ASSISTANT]
                content = "Yes. Build on the previous approach and add a regression test for duplicate retries."
            assert session.interview.scenario is not None
            self.calls += 1
            return CopilotResult(
                content=content,
                source="mock",
                model="test-copilot",
                suggested_files=[{"path": "app/main.py", "reason": "Open file with handler code."}],
                risk_flags=["Add a regression check before submitting."],
                confidence="medium",
                included_context_size=1234,
            )

    stub_copilot = StubCopilot()
    app.dependency_overrides[get_candidate_copilot] = lambda: stub_copilot
    ai_response = client.post(
        f"/api/sessions/{session['id']}/ai",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "question": "How should I fix the idempotency bug?",
            "code": edited_code,
            "current_file_path": "app/main.py",
            "current_file_content": edited_code,
            "latest_test_output": test_run["output"],
            "notes": notes,
        },
    )
    assert ai_response.status_code == 201
    ai_exchange = ai_response.json()
    assert ai_exchange["user_message"]["role"] == "user"
    assert "code_snapshot" not in ai_exchange["user_message"]
    assert "ai_model" not in ai_exchange["user_message"]
    assert ai_exchange["user_message"]["message_metadata"] == {
        "current_file_path": "app/main.py",
        "latest_test_output_included": True,
        "notes_included": True,
    }
    assert ai_exchange["assistant_message"]["role"] == "assistant"
    assert "ai_model" not in ai_exchange["assistant_message"]
    assert "```python" in ai_exchange["assistant_message"]["content"]
    assert ai_exchange["assistant_message"]["message_metadata"]["confidence"] == "medium"
    assert ai_exchange["assistant_message"]["message_metadata"]["suggested_files"][0]["path"] == "app/main.py"
    assert "source" not in ai_exchange["assistant_message"]["message_metadata"]
    assert ai_exchange["response"]["confidence"] == "medium"
    assert ai_exchange["response"]["suggested_files"][0]["path"] == "app/main.py"

    follow_up_response = client.post(
        f"/api/sessions/{session['id']}/ai",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "question": "Does this idempotency approach need a test?",
            "code": edited_code,
            "current_file_path": "app/main.py",
            "current_file_content": edited_code,
            "latest_test_output": test_run["output"],
            "notes": notes,
        },
    )
    assert follow_up_response.status_code == 201
    follow_up_exchange = follow_up_response.json()
    assert "regression test" in follow_up_exchange["assistant_message"]["content"]
    assert "code_snapshot" not in follow_up_exchange["user_message"]
    assert "ai_model" not in follow_up_exchange["assistant_message"]

    admin_ai_response = client.post(
        f"/api/sessions/{session['id']}/ai",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"question": "Can I see this?", "code": edited_code},
    )
    assert admin_ai_response.status_code == 403

    reinvite_response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "candidate@example.com"},
    )
    assert reinvite_response.status_code == 201
    reinvite = reinvite_response.json()
    assert reinvite["session_id"] == session["id"]
    assert reinvite["invite_url"] != invite["invite_url"]

    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"code": edited_code, "notes": notes, "test_output": test_run["output"]},
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    assert submission["code"] == edited_code
    assert submission["notes"] == notes
    _assert_no_submission_transport_fields(submission)
    submitted_paths = {submitted_file["path"] for submitted_file in submission["submitted_files"]}
    assert "app/main.py" in submitted_paths
    assert "tests/test_orders_hidden.py" not in submitted_paths

    submitted_session_response = client.get(
        f"/api/sessions/{session['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert submitted_session_response.status_code == 200
    submitted_session = submitted_session_response.json()
    assert submitted_session["status"] == "reviewed"
    assert submitted_session["submission"]["id"] == submission["id"]
    _assert_no_submission_transport_fields(submitted_session["submission"])

    post_submit_edit_response = client.post(
        f"/api/sessions/{session['id']}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "code_edit", "payload": {"code": "def later():\n    return None\n"}},
    )
    assert post_submit_edit_response.status_code == 409

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        events = list(db.execute(select(TelemetryEvent)).scalars())
        event_types = [event.event_type for event in events]
        ai_event = next(event for event in events if event.event_type == TelemetryEventType.AI_PROMPT_SENT)
    finally:
        db.close()
    assert TelemetryEventType.SESSION_STARTED in event_types
    assert TelemetryEventType.CODE_EDIT in event_types
    assert TelemetryEventType.NOTE_UPDATED in event_types
    assert TelemetryEventType.TEST_RUN in event_types
    assert TelemetryEventType.AI_PROMPT_SENT in event_types
    assert TelemetryEventType.SUBMISSION_CREATED in event_types
    assert ai_event.payload["candidate_prompt"] == "How should I fix the idempotency bug?"
    assert ai_event.payload["included_context_size"] == 1234
    assert ai_event.payload["current_file_path"] == "app/main.py"
    assert ai_event.payload["ai_mode"] == "Pair Programmer Mode"
    assert ai_event.payload["response_confidence"] == "medium"

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        ai_messages = list(db.execute(select(AIMessage).order_by(AIMessage.created_at.asc())).scalars())
    finally:
        db.close()
    assert [message.role for message in ai_messages] == [
        AIMessageRole.USER,
        AIMessageRole.ASSISTANT,
        AIMessageRole.USER,
        AIMessageRole.ASSISTANT,
    ]
    assert ai_messages[0].content == "How should I fix the idempotency bug?"
    assert ai_messages[0].message_metadata["included_context_size"] == 1234
    assert "idempotency key" in ai_messages[1].content
    assert ai_messages[1].message_metadata["suggested_files"][0]["path"] == "app/main.py"


def test_candidate_workspace_edits_snapshots_and_submits_files(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token = _register_admin(client)
    _create_candidate(client, email="workspace@example.com", full_name="Workspace Candidate")
    interview_id = _create_ready_interview(client, token=admin_token)
    invite_response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "workspace@example.com"},
    )
    assert invite_response.status_code == 201
    raw_invite_token = urlparse(invite_response.json()["invite_url"]).path.rsplit("/", 1)[-1]
    candidate_login = client.post(
        "/api/auth/login",
        json={"email": "workspace@example.com", "password": "StrongPass123!"},
    )
    assert candidate_login.status_code == 200
    candidate_token = candidate_login.json()["access_token"]
    start_response = client.post(
        f"/api/invite/{raw_invite_token}/start",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert start_response.status_code == 200
    session = start_response.json()

    workspace_response = client.get(
        f"/api/sessions/{session['id']}/workspace",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["project"]["project_name"] == "orders-review-api"
    assert workspace["project"]["install_command"] is None
    assert workspace["project"]["run_command"] is None
    assert workspace["project"]["test_command"] is None
    paths = {workspace_file["path"] for workspace_file in workspace["files"]}
    assert "app/main.py" in paths
    assert "app/services/orders.py" in paths
    assert "tests/test_orders_hidden.py" not in paths

    files_by_path = {workspace_file["path"]: workspace_file for workspace_file in workspace["files"]}
    main_file = files_by_path["app/main.py"]
    service_file = files_by_path["app/services/orders.py"]
    opened_response = client.post(
        f"/api/sessions/{session['id']}/events",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"event_type": "file_opened", "payload": {"file_id": main_file["id"], "path": main_file["path"]}},
    )
    assert opened_response.status_code == 201

    fixed_service = service_file["current_content"].replace(
        'return round(sum(item["unit_price"] for item in order["items"]), 2)',
        'return round(sum(item["unit_price"] * item["quantity"] for item in order["items"]), 2)',
    )
    service_update_response = client.put(
        f"/api/sessions/{session['id']}/files/{service_file['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"content": fixed_service},
    )
    assert service_update_response.status_code == 200
    assert service_update_response.json()["current_content"] == fixed_service

    fixed_main = main_file["current_content"].replace(
        "def list_orders() -> list[dict[str, object]]:\n"
        "    return [summarize_order(order) for order in load_orders()]\n",
        "def list_orders(status: str | None = None) -> list[dict[str, object]]:\n"
        "    orders = load_orders()\n"
        "    if status is not None:\n"
        "        orders = [order for order in orders if order[\"status\"] == status]\n"
        "    return [summarize_order(order) for order in orders]\n",
    )
    main_update_response = client.put(
        f"/api/sessions/{session['id']}/files/{main_file['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"content": fixed_main},
    )
    assert main_update_response.status_code == 200

    workspace_after_update = client.get(
        f"/api/sessions/{session['id']}/workspace",
        headers={"Authorization": f"Bearer {candidate_token}"},
    ).json()
    updated_files_by_path = {workspace_file["path"]: workspace_file for workspace_file in workspace_after_update["files"]}
    assert updated_files_by_path["app/services/orders.py"]["original_content"] != fixed_service
    assert updated_files_by_path["app/services/orders.py"]["current_content"] == fixed_service

    run_response = client.post(
        f"/api/sessions/{session['id']}/run-tests",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={},
    )
    assert run_response.status_code == 200
    test_run = run_response.json()
    assert test_run["status"] == "passed"
    assert "workspace checks passed using `app/data/orders.json`" in test_run["output"]
    assert test_run["cases"][0]["name"] == "seed-data-loaded"

    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"notes": "Fixed totals, added status filtering, and ran the workspace checks.", "test_output": test_run["output"]},
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    submitted_by_path = {submitted_file["path"]: submitted_file for submitted_file in submission["submitted_files"]}
    assert submitted_by_path["app/services/orders.py"]["content"] == fixed_service
    assert submitted_by_path["app/main.py"]["content"] == fixed_main
    assert "tests/test_orders_hidden.py" not in submitted_by_path

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        service_snapshot = db.execute(
            select(SessionFileSnapshot)
            .join(ProjectFile, SessionFileSnapshot.project_file_id == ProjectFile.id)
            .where(ProjectFile.path == "app/services/orders.py")
        ).scalar_one()
        event_types = [event.event_type for event in db.execute(select(TelemetryEvent)).scalars()]
    finally:
        db.close()
    assert service_snapshot.current_content == fixed_service
    assert service_snapshot.original_content != fixed_service
    assert TelemetryEventType.FILE_OPENED in event_types
    assert TelemetryEventType.FILE_EDITED in event_types
    assert TelemetryEventType.FILE_SAVED in event_types
    assert TelemetryEventType.TEST_RUN in event_types
    assert TelemetryEventType.SUBMISSION_CREATED in event_types

    delete_response = client.delete(
        f"/api/interviews/{interview_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204


def test_candidate_java_spring_scenario_is_stack_matched_and_safe(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token = _register_admin(client)
    _create_candidate(client, email="java-candidate@example.com", full_name="Java Candidate")
    interview_id = _create_ready_interview(
        client,
        token=admin_token,
        stack=["Java", "Spring Boot", "PostgreSQL"],
        interview_type="Backend debugging",
    )
    invite_response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "java-candidate@example.com"},
    )
    assert invite_response.status_code == 201
    raw_invite_token = urlparse(invite_response.json()["invite_url"]).path.rsplit("/", 1)[-1]
    candidate_login = client.post(
        "/api/auth/login",
        json={"email": "java-candidate@example.com", "password": "StrongPass123!"},
    )
    assert candidate_login.status_code == 200
    candidate_token = candidate_login.json()["access_token"]

    start_response = client.post(
        f"/api/invite/{raw_invite_token}/start",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )

    assert start_response.status_code == 200
    scenario = start_response.json()["scenario"]
    assert scenario["language"] == "java"
    assert scenario["framework"] == "Spring Boot"
    assert scenario["validation_command"] == "mvn test"
    assert "expected_solution_files_json" not in scenario
    assert "hidden_evaluation_points" not in scenario
    assert "hidden_rubric" not in scenario
    assert "interviewer_rubric" not in scenario
    assert "bug_description_internal" not in scenario
    assert "expected_solution_summary" not in scenario

    project_paths = {project_file["path"] for project_file in scenario["project"]["files"]}
    test_paths = {test_file["path"] for test_file in scenario["test_files_json"]}
    assert "pom.xml" in project_paths
    assert any(path.startswith("src/main/java/") and path.endswith(".java") for path in project_paths)
    assert any(path.startswith("src/test/java/") and path.endswith(".java") for path in test_paths)
    assert not any(path.endswith(".py") for path in project_paths)
    assert "requirements.txt" not in project_paths


def test_candidate_submission_pushes_changed_files_to_github_when_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token, candidate_token, session, workspace = _start_workspace_session(
        client,
        candidate_email="github-success@example.com",
    )
    _fix_order_workspace(client, candidate_token=candidate_token, session_id=session["id"], workspace=workspace)
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        project = db.execute(select(ScenarioProject)).scalar_one()
        project.starter_branch_name = "scenario-interview-starter"
        project.starter_push_status = "pushed"
        db.commit()
    finally:
        db.close()

    class StubGitHubPublisher:
        def publish_submission(self, **kwargs: object) -> GitHubSubmissionPushResult:
            files = kwargs["files"]
            assert isinstance(files, list)
            paths = [file.path for file in files]
            assert sorted(paths) == ["app/main.py", "app/services/orders.py"]
            assert str(kwargs["interview_id"]) == session["interview_id"]
            assert str(kwargs["session_id"]) == session["id"]
            assert kwargs["candidate_email"] == "github-success@example.com"
            assert kwargs["base_branch_name"] == "scenario-interview-starter"
            return GitHubSubmissionPushResult(
                status="pushed",
                branch_name="interview-branch",
                base_branch_name="scenario-interview-starter",
                commit_sha="abc123",
                repository_url="https://github.com/example/repo",
                pull_request_url="https://github.com/example/repo/pull/10",
            )

    app.dependency_overrides[get_github_submission_publisher] = lambda: StubGitHubPublisher()
    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"notes": "Fixed and verified.", "test_output": "Workspace checks passed."},
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    _assert_no_submission_transport_fields(submission)
    assert submission["submitted_files"]

    results_response = client.get(
        f"/api/interviews/{session['interview_id']}/submissions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert results_response.status_code == 200
    results = results_response.json()
    _assert_no_submission_transport_fields(results[0])


def test_candidate_submission_falls_back_when_github_is_not_configured(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    _, candidate_token, session, workspace = _start_workspace_session(
        client,
        candidate_email="github-disabled@example.com",
    )
    _fix_order_workspace(client, candidate_token=candidate_token, session_id=session["id"], workspace=workspace)

    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"notes": "Fixed and verified.", "test_output": "Workspace checks passed."},
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    _assert_no_submission_transport_fields(submission)
    assert submission["submitted_files"]


def test_candidate_submission_records_failed_github_push_without_failing_submission(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    _, candidate_token, session, workspace = _start_workspace_session(
        client,
        candidate_email="github-failed@example.com",
    )
    _fix_order_workspace(client, candidate_token=candidate_token, session_id=session["id"], workspace=workspace)

    class FailingGitHubPublisher:
        def publish_submission(self, **_: object) -> GitHubSubmissionPushResult:
            return GitHubSubmissionPushResult(
                status="failed",
                branch_name="interview-branch",
                repository_url="https://github.com/example/repo",
                error="GitHub returned HTTP 403: Resource not accessible by integration.",
            )

    app.dependency_overrides[get_github_submission_publisher] = lambda: FailingGitHubPublisher()
    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"notes": "Fixed and verified.", "test_output": "Workspace checks passed."},
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    _assert_no_submission_transport_fields(submission)
    assert submission["submitted_files"]


def test_candidate_submission_rejects_unsafe_submitted_file_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    _, candidate_token, session, _ = _start_workspace_session(
        client,
        candidate_email="unsafe-path@example.com",
    )

    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "notes": "Trying to submit an unsafe file.",
            "submitted_files": [{"path": ".env", "content": "GITHUB_TOKEN=secret", "language": "text"}],
        },
    )
    assert submit_response.status_code == 422
    assert "environment files" in submit_response.json()["detail"]

    session_response = client.get(
        f"/api/sessions/{session['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert session_response.status_code == 200
    assert session_response.json()["status"] == "started"


def test_generate_file_diffs_for_modified_added_and_deleted_files() -> None:
    diffs = generate_file_diffs(
        original_files=[
            {"path": "app/main.py", "content": "value = 1\n", "language": "python", "file_type": "source"},
            {"path": "README.md", "content": "old\n", "language": "markdown", "file_type": "docs"},
        ],
        candidate_files=[
            {"path": "app/main.py", "content": "value = 2\n", "language": "python", "file_type": "source"},
            {"path": "tests/test_main.py", "content": "def test_main():\n    assert True\n", "language": "python", "file_type": "test"},
        ],
    )

    by_path = {diff["path"]: diff for diff in diffs}
    assert by_path["app/main.py"]["status"] == "modified"
    assert by_path["app/main.py"]["additions"] == 1
    assert by_path["app/main.py"]["deletions"] == 1
    assert by_path["README.md"]["status"] == "deleted"
    assert by_path["tests/test_main.py"]["status"] == "added"
    assert "--- a/app/main.py" in by_path["app/main.py"]["diff"]
    assert "+++ b/app/main.py" in by_path["app/main.py"]["diff"]


def test_multi_file_submission_review_uses_repo_context_and_internal_rubric(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    admin_token, candidate_token, session, workspace = _start_workspace_session(
        client,
        candidate_email="review-context@example.com",
    )
    _fix_order_workspace(client, candidate_token=candidate_token, session_id=session["id"], workspace=workspace)
    workspace_files = {workspace_file["path"]: workspace_file for workspace_file in workspace["files"]}
    main_file = workspace_files["app/main.py"]

    run_response = client.post(
        f"/api/sessions/{session['id']}/run-tests",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={},
    )
    assert run_response.status_code == 200
    test_run = run_response.json()

    class StubCopilot:
        def generate_reply(
            self,
            *,
            session: InterviewSession,
            question: str,
            context: dict[str, object],
            previous_messages: list[AIMessage],
        ) -> CopilotResult:
            assert "hidden_rubric" not in context
            assert "hidden_evaluation_points" not in context
            assert "interviewer_rubric" not in context
            assert previous_messages == []
            assert "status filter" in question.lower()
            return CopilotResult(
                content="Check the status query path and rerun workspace checks.",
                source="mock",
                model="test-copilot",
                suggested_files=[{"path": "app/main.py", "reason": "Endpoint query handling lives here."}],
                risk_flags=[],
                confidence="high",
                included_context_size=512,
            )

    app.dependency_overrides[get_candidate_copilot] = lambda: StubCopilot()
    ai_response = client.post(
        f"/api/sessions/{session['id']}/ai",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "question": "Can you review my status filter and suggest validation?",
            "current_file_path": "app/main.py",
            "current_file_content": main_file["current_content"],
            "latest_test_output": test_run["output"],
            "notes": "Root cause: totals ignored item quantities.",
        },
    )
    assert ai_response.status_code == 201

    class StubGitHubPublisher:
        def publish_submission(self, **_: object) -> GitHubSubmissionPushResult:
            return GitHubSubmissionPushResult(
                status="pushed",
                branch_name="interview-review-branch",
                commit_sha="def456",
                repository_url="https://github.com/example/repo",
                pull_request_url="https://github.com/example/repo/pull/11",
            )

    class StubReviewRunner:
        def __init__(self) -> None:
            self.context: dict[str, object] | None = None

        def review(self, context: dict[str, object]) -> list[AgentReviewResult]:
            self.context = context
            scenario_context = context["scenario"]
            assert isinstance(scenario_context, dict)
            assert scenario_context["hidden_rubric"]
            assert scenario_context["hidden_evaluation_points"]
            assert scenario_context["interviewer_rubric"]
            assert "hidden_rubric" not in ai_response.text
            assert "app/main.py" in [file["path"] for file in context["candidate_submitted_files"]]  # type: ignore[index]
            assert any(file["is_hidden"] for file in context["original_project_files"])  # type: ignore[index]
            assert {file_diff["path"] for file_diff in context["file_diffs"]} == {  # type: ignore[index]
                "app/main.py",
                "app/services/orders.py",
            }
            assert any(message["role"] == "user" for message in context["ai_chat_transcript"])  # type: ignore[index]
            assert any(event["event_type"] == "test_run" for event in context["telemetry_events"])  # type: ignore[index]
            assert context["test_run_outputs"] == [test_run["output"]]
            assert "github" not in context
            return [
                AgentReviewResult(
                    agent_type=agent["type"],
                    agent_label=agent["label"],
                    score=82 if agent["type"] != "hiring_recommendation" else 80,
                    strengths=[f"{agent['label']} reviewed repo evidence."],
                    weaknesses=[],
                    evidence=["Diffs, AI transcript, telemetry, and notes were included."],
                    risk_flags=["Review input validation before hiring decision."] if agent["type"] == "security" else [],
                    recommendation="hire" if agent["type"] == "hiring_recommendation" else "strong signal",
                    explanation=f"{agent['label']} completed the mocked review.",
                    raw_response={"source": "mock"},
                )
                for agent in AGENT_DEFINITIONS
            ]

    review_runner = StubReviewRunner()
    app.dependency_overrides[get_github_submission_publisher] = lambda: StubGitHubPublisher()
    app.dependency_overrides[get_review_agent_runner] = lambda: review_runner
    submit_response = client.post(
        f"/api/sessions/{session['id']}/submit",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={
            "notes": "Root cause: totals ignored quantity. I fixed totals, added status filtering, and reran checks.",
            "test_output": test_run["output"],
        },
    )
    assert submit_response.status_code == 201
    submission = submit_response.json()
    assert {file_diff["path"] for file_diff in submission["file_diffs"]} == {
        "app/main.py",
        "app/services/orders.py",
    }
    review_response = client.get(
        f"/api/submissions/{submission['id']}/reviews",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review_response.status_code == 200
    review_summary = review_response.json()
    assert review_summary["status"] == "reviewed"
    assert review_summary["weighted_score"] == 82
    assert review_summary["recommendation"] == "hire"
    assert len(review_summary["agent_reviews"]) == len(AGENT_DEFINITIONS)
    assert review_summary["ai_usage_analysis"]["candidate_prompt_count"] == 1
    assert review_summary["ai_usage_analysis"]["validated_suggestions"] is True
    assert "github" not in review_summary
    assert review_runner.context is not None

    result_response = client.get(
        f"/api/results/{session['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["candidate_email"] == "review-context@example.com"
    assert result["changed_files"] == ["app/main.py", "app/services/orders.py"]
    assert "github" not in result
    assert len(result["score_breakdown"]) == 7
    assert "Review input validation before hiring decision." in result["risk_flags"]
    assert "app/main.py" in {file["path"] for file in result["submitted_files"]}
    assert [message["role"] for message in result["ai_chat_transcript"]] == ["user", "assistant"]
    assert all("ai_model" not in message for message in result["ai_chat_transcript"])
    assert all("code_snapshot" not in message for message in result["ai_chat_transcript"])
    assert any(event["event_type"] == "test_run" for event in result["telemetry_timeline"])
    assert result["prompt_quality_summary"]["candidate_prompt_count"] == 1
    assert result["prompt_quality_summary"]["prompts_with_file_context"] == 1

    dashboard_response = client.get(
        "/api/results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert len(dashboard) == 1
    assert dashboard[0]["session_id"] == session["id"]
    assert dashboard[0]["weighted_score"] == 82
    assert dashboard[0]["recommendation"] == "hire"
    assert dashboard[0]["risk_flags"] == ["Review input validation before hiring decision."]
    _assert_no_submission_transport_fields(dashboard[0])

    candidate_dashboard_response = client.get(
        "/api/results",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_dashboard_response.status_code == 403
    candidate_result_response = client.get(
        f"/api/results/{session['id']}",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_result_response.status_code == 403

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        assert db.execute(select(AgentReview)).scalars().all()
        stored_score = db.execute(select(Score)).scalar_one()
        stored_session = db.execute(select(InterviewSession).where(InterviewSession.id == session["id"])).scalar_one()
    finally:
        db.close()
    assert stored_session.status == InterviewSessionStatus.REVIEWED
    assert stored_score.weighted_score == 82
    assert stored_score.recommendation == "hire"
    assert len(stored_score.score_breakdown) == 7


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


def test_invite_rejects_submitted_session(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
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

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        session = db.execute(select(InterviewSession)).scalar_one()
        session.status = InterviewSessionStatus.SUBMITTED
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/api/interviews/{interview_id}/invite",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"candidate_email": "candidate@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This candidate already has a submitted or reviewed session for the interview."

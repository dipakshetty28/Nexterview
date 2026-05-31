from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models import (
    Interview,
    InterviewSession,
    InterviewSessionStatus,
    Organization,
    OrganizationMember,
    ProjectFile,
    Scenario,
    ScenarioProject,
    SessionFileSnapshot,
    User,
    UserRole,
)
from app.services.scenario_projects import ensure_session_file_snapshots

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

_ = (
    Interview,
    InterviewSession,
    Organization,
    OrganizationMember,
    ProjectFile,
    Scenario,
    ScenarioProject,
    SessionFileSnapshot,
    User,
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to a PostgreSQL database to run project snapshot integration tests.")
    url = make_url(TEST_DATABASE_URL)
    if url.drivername.startswith("sqlite"):
        raise RuntimeError("Project snapshot integration tests must not run against SQLite.")

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _create_interview_graph(db: Session) -> tuple[Interview, Scenario, InterviewSession]:
    organization = Organization(name="Example Org", slug="example-org")
    interviewer = User(
        email="interviewer@example.com",
        full_name="Interviewer",
        role=UserRole.INTERVIEWER,
        hashed_password="hash",
    )
    candidate = User(
        email="candidate@example.com",
        full_name="Candidate",
        role=UserRole.CANDIDATE,
        hashed_password="hash",
    )
    db.add_all([organization, interviewer, candidate])
    db.flush()
    db.add_all(
        [
            OrganizationMember(organization_id=organization.id, user_id=interviewer.id, role=UserRole.INTERVIEWER),
            OrganizationMember(organization_id=organization.id, user_id=candidate.id, role=UserRole.CANDIDATE),
        ]
    )
    interview = Interview(
        organization_id=organization.id,
        created_by_id=interviewer.id,
        role_title="Backend Engineer",
        seniority="Senior",
        stack=["Python", "FastAPI"],
        difficulty="Intermediate",
        interview_type="Backend debugging",
        duration_minutes=75,
        allowed_ai_mode="Pair Programmer Mode",
        evaluation_criteria=["Correctness", "Debugging"],
        status="READY",
    )
    db.add(interview)
    db.flush()
    scenario = Scenario(
        interview_id=interview.id,
        title="Debug duplicate retries",
        business_context="Finance needs safe retries for a billing service.",
        technical_requirements=["Keep retries idempotent.", "Add regression coverage."],
        starter_code="def charge_customer():\n    return None\n",
        expected_behavior=["Retries reuse one key.", "Duplicate charges are prevented."],
        logs_or_bug_report="Provider received multiple idempotency keys for one invoice.",
        bug_description="The retry loop creates a new idempotency key on each attempt.",
        feature_request="Expose a deterministic retry helper for payment operations.",
        validation_instructions="Run pytest and explain the duplicate retry regression.",
        candidate_task_summary="Fix billing retries without rewriting the provider integration.",
        hidden_evaluation_points=["Looks for stable idempotency keys.", "Checks error handling."],
        hidden_rubric=["Hidden tests assert one provider charge for transient failures."],
        candidate_instructions="Fix the bug and document verification.",
        interviewer_rubric=["Correctness", "Debugging process"],
        generation_source="test",
        ai_model=None,
    )
    db.add(scenario)
    db.flush()
    session = InterviewSession(
        organization_id=organization.id,
        interview_id=interview.id,
        candidate_id=candidate.id,
        status=InterviewSessionStatus.INVITED,
    )
    db.add(session)
    db.flush()
    return interview, scenario, session


def test_scenario_project_model_creation(db: Session) -> None:
    _, scenario, _ = _create_interview_graph(db)
    project = ScenarioProject(
        scenario_id=scenario.id,
        stack=["Python", "FastAPI", "PostgreSQL"],
        project_name="billing-retry-service",
        description="Repo-style billing retry exercise.",
        run_command="python app/billing.py",
        test_command="pytest",
        install_command="pip install -r requirements.txt",
        entrypoint="app/billing.py",
        package_manager="pip",
        framework="FastAPI",
    )
    db.add(project)
    db.flush()
    db.add_all(
        [
            ProjectFile(
                project_id=project.id,
                path="app/billing.py",
                content="def charge_customer():\n    return None\n",
                language="python",
                file_type="source",
            ),
            ProjectFile(
                project_id=project.id,
                path="tests/test_billing.py",
                content="def test_retry_contract():\n    assert True\n",
                language="python",
                file_type="test",
            ),
            ProjectFile(
                project_id=project.id,
                path="tests/test_hidden_retry.py",
                content="def test_hidden_retry_contract():\n    assert True\n",
                language="python",
                file_type="hidden_test",
                is_editable=False,
                is_hidden=True,
            ),
        ]
    )
    db.commit()

    stored_project = db.execute(select(ScenarioProject)).scalar_one()
    assert stored_project.scenario_id == scenario.id
    assert stored_project.project_name == "billing-retry-service"
    assert [project_file.path for project_file in stored_project.files] == [
        "app/billing.py",
        "tests/test_billing.py",
        "tests/test_hidden_retry.py",
    ]
    assert stored_project.files[-1].is_hidden is True
    assert stored_project.files[-1].is_editable is False


def test_session_file_snapshots_are_created_from_project_files(db: Session) -> None:
    _, scenario, session = _create_interview_graph(db)
    project = ScenarioProject(
        scenario_id=scenario.id,
        stack=["Python"],
        project_name="billing-retry-service",
        description="Repo-style billing retry exercise.",
        run_command="python app/billing.py",
        test_command="pytest",
        install_command="pip install -r requirements.txt",
        entrypoint="app/billing.py",
        package_manager="pip",
        framework="Python",
    )
    db.add(project)
    db.flush()
    db.add_all(
        [
            ProjectFile(
                project_id=project.id,
                path="app/billing.py",
                content="def charge_customer():\n    return None\n",
                language="python",
                file_type="source",
            ),
            ProjectFile(
                project_id=project.id,
                path="data/payments.json",
                content='{"invoice_id": "inv_891"}\n',
                language="json",
                file_type="data",
            ),
        ]
    )
    db.commit()
    db.refresh(session)

    snapshots = ensure_session_file_snapshots(db, session=session)
    db.commit()

    assert [snapshot.path for snapshot in snapshots] == ["app/billing.py", "data/payments.json"]
    first_snapshot = db.execute(
        select(SessionFileSnapshot).where(SessionFileSnapshot.path == "app/billing.py")
    ).scalar_one()
    assert first_snapshot.original_content == "def charge_customer():\n    return None\n"
    assert first_snapshot.current_content == first_snapshot.original_content

    first_snapshot.current_content = "def charge_customer():\n    return 'fixed'\n"
    db.commit()
    db.refresh(session)

    second_pass = ensure_session_file_snapshots(db, session=session)
    db.commit()

    assert len(second_pass) == 2
    unchanged_snapshot = db.execute(
        select(SessionFileSnapshot).where(SessionFileSnapshot.path == "app/billing.py")
    ).scalar_one()
    assert unchanged_snapshot.current_content == "def charge_customer():\n    return 'fixed'\n"
    persisted_snapshots = db.execute(
        select(SessionFileSnapshot).order_by(SessionFileSnapshot.path.asc())
    ).scalars().all()
    assert [snapshot.id for snapshot in persisted_snapshots] == [snapshot.id for snapshot in second_pass]

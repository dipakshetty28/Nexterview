import os

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Interview, Scenario
from app.services.scenario_generator import generate_scenario_structured


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_interview() -> int:
    db = SessionLocal()
    interview = Interview(
        role_title="Backend Engineer",
        stack="Python + FastAPI",
        difficulty="Senior",
        interview_type="Backend debugging",
        duration_minutes=90,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    interview_id = interview.id
    db.close()
    return interview_id


def test_generate_scenario_endpoint_fallback_when_key_missing():
    os.environ.pop("OPENAI_API_KEY", None)
    interview_id = seed_interview()

    response = client.post(f"/api/interviews/{interview_id}/generate-scenario")
    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "title",
        "business_context",
        "technical_requirements",
        "starter_code",
        "expected_behavior",
        "logs_or_bug_report",
        "hidden_evaluation_points",
        "candidate_instructions",
        "interviewer_rubric",
        "interview_id",
    }
    assert expected_keys.issubset(data.keys())

    db = SessionLocal()
    count = db.query(Scenario).filter(Scenario.interview_id == interview_id).count()
    db.close()
    assert count == 1


def test_structured_generation_with_mocked_ai_client():
    os.environ["OPENAI_API_KEY"] = "test-key"

    def mocked_ai_client(_prompt: str) -> str:
        return """{
            \"title\": \"Fix payment retry idempotency\",
            \"business_context\": \"Duplicate transactions are being created.\",
            \"technical_requirements\": \"Patch retry logic and add tests.\",
            \"starter_code\": \"def process_payment(): pass\",
            \"expected_behavior\": \"No duplicate writes after retries.\",
            \"logs_or_bug_report\": \"ERROR duplicate tx for same idempotency key\",
            \"hidden_evaluation_points\": \"Validation strategy and rollback safety\",
            \"candidate_instructions\": \"Fix bug and explain root cause\",
            \"interviewer_rubric\": \"Assess correctness and tradeoffs\"
        }"""

    scenario = generate_scenario_structured(
        role="Backend Engineer",
        stack="Python + FastAPI",
        difficulty="Senior",
        interview_type="Backend debugging",
        duration=90,
        ai_client=mocked_ai_client,
    )

    assert scenario.title == "Fix payment retry idempotency"

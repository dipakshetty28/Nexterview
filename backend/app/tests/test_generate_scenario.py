from fastapi.testclient import TestClient

from app.api.interviews import get_current_user, get_scenario_service
from app.main import app
from app.schemas.scenario import GeneratedScenarioSchema


class MockScenarioService:
    def generate_scenario(self, interview):
        return GeneratedScenarioSchema(
            title="Mock Scenario",
            business_context="Mock context",
            technical_requirements="Mock requirements",
            starter_code="print('hello')",
            expected_behavior="Works correctly",
            logs_or_bug_report="No logs",
            hidden_evaluation_points="Validation",
            candidate_instructions="Do the thing",
            interviewer_rubric="Rubric",
        )


client = TestClient(app)


def test_generate_scenario_success():
    app.dependency_overrides[get_scenario_service] = lambda: MockScenarioService()
    app.dependency_overrides[get_current_user] = lambda: {"id": 100, "role": "INTERVIEWER", "organization_id": 10}

    response = client.post("/api/interviews/1/generate-scenario")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Mock Scenario"
    assert body["interview_id"] == 1


def test_generate_scenario_forbidden_org():
    app.dependency_overrides[get_scenario_service] = lambda: MockScenarioService()
    app.dependency_overrides[get_current_user] = lambda: {"id": 100, "role": "INTERVIEWER", "organization_id": 999}

    response = client.post("/api/interviews/1/generate-scenario")
    assert response.status_code == 403

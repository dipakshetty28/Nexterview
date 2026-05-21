import json

from openai import OpenAI

from app.core.config import settings
from app.models.interview import Interview
from app.schemas.scenario import GeneratedScenarioSchema


class ScenarioGenerationService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def _fallback(self, interview: Interview) -> GeneratedScenarioSchema:
        return GeneratedScenarioSchema(
            title=f"{interview.role_title} {interview.interview_type} Scenario",
            business_context="Build and debug a production-facing workflow for a customer-critical service.",
            technical_requirements=f"Use {interview.stack}. Meet {interview.difficulty} difficulty constraints within {interview.duration_minutes} minutes.",
            starter_code="def handler(request):\n    # TODO: implement\n    return {'status': 'not_implemented'}",
            expected_behavior="Service handles valid requests, rejects invalid payloads, and logs failures with correlation IDs.",
            logs_or_bug_report="Intermittent 500s observed when concurrent requests update shared resources.",
            hidden_evaluation_points="Input validation, concurrency safety, error handling, and test strategy.",
            candidate_instructions="Implement a robust fix, explain tradeoffs, and provide tests for critical paths.",
            interviewer_rubric=interview.evaluation_criteria,
        )

    def generate_scenario(self, interview: Interview) -> GeneratedScenarioSchema:
        if not self.client:
            return self._fallback(interview)

        prompt = (
            "Return JSON only with fields: title, business_context, technical_requirements, starter_code, "
            "expected_behavior, logs_or_bug_report, hidden_evaluation_points, candidate_instructions, interviewer_rubric. "
            f"Interview config: role={interview.role_title}, stack={interview.stack}, difficulty={interview.difficulty}, "
            f"type={interview.interview_type}, duration={interview.duration_minutes}, criteria={interview.evaluation_criteria}."
        )

        response = self.client.responses.create(model=settings.openai_model, input=prompt)
        content = response.output_text
        parsed = json.loads(content)
        return GeneratedScenarioSchema.model_validate(parsed)

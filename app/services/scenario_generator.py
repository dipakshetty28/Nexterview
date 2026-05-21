import json
import os
from typing import Callable

from pydantic import ValidationError

from app.schemas import ScenarioStructured


class ScenarioGenerationError(Exception):
    pass


def _fallback_payload(role: str, stack: str, difficulty: str, interview_type: str, duration: int) -> dict:
    return {
        "title": f"{difficulty} {stack} {interview_type} task for {role}",
        "business_context": "A production service is facing reliability and correctness issues during peak usage.",
        "technical_requirements": f"Implement and debug in {stack}; ensure correctness, tests, and maintainability within {duration} minutes.",
        "starter_code": "# TODO: candidate starts from this scaffold\n\ndef solve():\n    pass\n",
        "expected_behavior": "System should pass tests, avoid regressions, and handle edge cases with clear reasoning.",
        "logs_or_bug_report": "ERROR: intermittent duplicate writes observed under retry bursts.",
        "hidden_evaluation_points": "AI collaboration quality, validation discipline, architecture tradeoff communication.",
        "candidate_instructions": "Use AI tools if needed, but verify outputs. Explain root cause and final fix.",
        "interviewer_rubric": "Score debugging depth, code quality, testing rigor, AI usage judgment, and communication clarity.",
    }


def generate_scenario_structured(
    role: str,
    stack: str,
    difficulty: str,
    interview_type: str,
    duration: int,
    ai_client: Callable[[str], str] | None = None,
) -> ScenarioStructured:
    if not os.getenv("OPENAI_API_KEY") or ai_client is None:
        return ScenarioStructured.model_validate(
            _fallback_payload(role, stack, difficulty, interview_type, duration)
        )

    prompt = (
        "Return ONLY valid JSON with keys: title, business_context, technical_requirements, "
        "starter_code, expected_behavior, logs_or_bug_report, hidden_evaluation_points, "
        "candidate_instructions, interviewer_rubric. "
        f"Role={role}; Stack={stack}; Difficulty={difficulty}; Type={interview_type}; Duration={duration}."
    )

    raw = ai_client(prompt)
    try:
        parsed = json.loads(raw)
        return ScenarioStructured.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ScenarioGenerationError(f"Invalid structured output: {exc}") from exc

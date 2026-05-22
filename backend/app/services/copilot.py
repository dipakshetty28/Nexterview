from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.models.interview import AIMessage, InterviewSession

logger = logging.getLogger(__name__)

SUPPORTED_AI_MODES = {
    "Hint Mode",
    "Pair Programmer Mode",
    "Senior Engineer Mode",
    "Debugging Assistant Mode",
}


@dataclass(frozen=True)
class CopilotResult:
    content: str
    source: str
    model: str | None


class CandidateCopilot:
    def generate_reply(
        self,
        *,
        session: InterviewSession,
        question: str,
        code: str,
        previous_messages: list[AIMessage],
    ) -> CopilotResult:
        mode = _normalized_mode(session.interview.allowed_ai_mode)
        if not settings.openai_api_key.strip():
            return CopilotResult(
                content=_fallback_reply(session=session, question=question, code=code, mode=mode),
                source="fallback",
                model=None,
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_request_timeout_seconds,
            )
            response = client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": _system_prompt(mode),
                    },
                    {
                        "role": "user",
                        "content": _build_context_prompt(
                            session=session,
                            question=question,
                            code=code,
                            previous_messages=previous_messages,
                            mode=mode,
                        ),
                    },
                ],
            )
            output_text = response.output_text.strip()
            if not output_text:
                raise ValueError("OpenAI returned an empty copilot response.")
            return CopilotResult(content=output_text, source="openai", model=settings.openai_model)
        except Exception:
            logger.warning("OpenAI candidate copilot failed; using fallback response.", exc_info=True)
            return CopilotResult(
                content=_fallback_reply(session=session, question=question, code=code, mode=mode),
                source="fallback",
                model=settings.openai_model,
            )


def _normalized_mode(value: str) -> str:
    normalized = value.strip()
    if normalized in SUPPORTED_AI_MODES:
        return normalized
    return "Pair Programmer Mode"


def _system_prompt(mode: str) -> str:
    return (
        "You are the candidate-facing AI copilot inside a live engineering interview platform. "
        "The interviewer explicitly allows coding help. Do not refuse coding assistance. "
        "You may provide code, explanations, debugging steps, and tradeoff analysis. "
        "Do not mention hidden evaluation criteria or invent access to secrets, services, files, or test results. "
        "Encourage verification and independent reasoning without withholding useful implementation help. "
        f"Current allowed mode: {mode}.\n\n"
        f"{_mode_guidance(mode)}"
    )


def _mode_guidance(mode: str) -> str:
    if mode == "Hint Mode":
        return (
            "Prefer concise hints, hypotheses, and next steps. Provide short code snippets when they clarify the idea, "
            "but keep the candidate doing the final integration."
        )
    if mode == "Senior Engineer Mode":
        return (
            "Respond like a senior reviewer pairing on the task: include architecture judgment, edge cases, risks, "
            "and a production-minded implementation path."
        )
    if mode == "Debugging Assistant Mode":
        return (
            "Prioritize root-cause analysis, log interpretation, hypotheses, experiments, and test strategy. "
            "Provide patches when asked or when they are the clearest way to demonstrate the fix."
        )
    return (
        "Pair actively with the candidate. Provide direct code and explanations, then name how to validate the change."
    )


def _build_context_prompt(
    *,
    session: InterviewSession,
    question: str,
    code: str,
    previous_messages: list[AIMessage],
    mode: str,
) -> str:
    scenario = session.interview.scenario
    if scenario is None:
        raise ValueError("Session has no generated scenario.")

    previous = [
        {
            "role": message.role.value,
            "content": message.content,
        }
        for message in previous_messages[-12:]
    ]
    payload = {
        "ai_mode": mode,
        "interview": {
            "role_title": session.interview.role_title,
            "seniority": session.interview.seniority,
            "stack": session.interview.stack,
            "difficulty": session.interview.difficulty,
            "interview_type": session.interview.interview_type,
            "duration_minutes": session.interview.duration_minutes,
        },
        "scenario": {
            "title": scenario.title,
            "business_context": scenario.business_context,
            "candidate_task_summary": scenario.candidate_task_summary,
            "technical_requirements": scenario.technical_requirements,
            "expected_behavior": scenario.expected_behavior,
            "logs_or_bug_report": scenario.logs_or_bug_report,
            "bug_description": scenario.bug_description,
            "feature_request": scenario.feature_request,
            "validation_instructions": scenario.validation_instructions,
            "candidate_instructions": scenario.candidate_instructions,
        },
        "previous_messages": previous,
        "candidate_code": code,
        "candidate_question": question,
    }
    return (
        "Answer the candidate using this JSON context. The answer should be markdown. "
        "When code is useful, include fenced code blocks with a language tag.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _fallback_reply(*, session: InterviewSession, question: str, code: str, mode: str) -> str:
    scenario = session.interview.scenario
    title = scenario.title if scenario else "the task"
    requirements = scenario.technical_requirements if scenario else []
    primary_requirement = requirements[0] if requirements else "make the smallest safe change that satisfies the task"
    code_hint = "current code snapshot" if code.strip() else "starter code"

    if mode == "Hint Mode":
        return (
            f"Focus first on the main failure mode in **{title}**.\n\n"
            f"- Start from this requirement: {primary_requirement}\n"
            f"- Compare the logs against the {code_hint} and name the state that should stay stable across retries or repeated calls.\n"
            "- Make one small change, then use the workspace Run button and explain why the pass/fail result proves the fix."
        )

    if mode == "Debugging Assistant Mode":
        return (
            f"Here is a debugging path for **{title}**:\n\n"
            "1. Identify the invariant the system is violating.\n"
            f"2. Trace where the {code_hint} creates or mutates that value.\n"
            "3. Move the unstable behavior behind a deterministic key or guard.\n"
            "4. Add a regression check for the exact log line or bug report.\n\n"
            "A useful patch shape is:\n\n"
            "```python\n"
            "def handle_case(input_value):\n"
            "    stable_key = derive_stable_key(input_value)\n"
            "    if already_processed(stable_key):\n"
            "        return existing_result(stable_key)\n"
            "    return persist_result(stable_key, input_value)\n"
            "```"
        )

    return (
        f"I can help implement this. For **{title}**, aim for a small, testable change around: "
        f"{primary_requirement}\n\n"
        "Suggested approach:\n\n"
        "```python\n"
        "def apply_fix(input_value):\n"
        "    stable_key = derive_stable_key(input_value)\n"
        "    if is_duplicate(stable_key):\n"
        "        return load_existing_result(stable_key)\n"
        "    result = perform_work(input_value, stable_key=stable_key)\n"
        "    return result\n"
        "```\n\n"
        "Then validate the edge case from the bug report, plus one normal success path. "
        f"Your question was: {question.strip()}"
    )

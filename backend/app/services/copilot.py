from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

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
    suggested_files: list[dict[str, str]]
    risk_flags: list[str]
    confidence: str
    included_context_size: int


class CandidateCopilot:
    def generate_reply(
        self,
        *,
        session: InterviewSession,
        question: str,
        context: dict[str, Any],
        previous_messages: list[AIMessage],
    ) -> CopilotResult:
        mode = _normalized_mode(session.interview.allowed_ai_mode)
        if not settings.openai_api_key.strip():
            return _fallback_result(
                session=session,
                question=question,
                context=context,
                previous_messages=previous_messages,
                source="fallback",
                model=None,
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_request_timeout_seconds,
            )
            context_prompt = _build_context_prompt(
                context=context,
                question=question,
                previous_messages=previous_messages,
                mode=mode,
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
                        "content": context_prompt,
                    },
                ],
            )
            output_text = response.output_text.strip()
            if not output_text:
                raise ValueError("OpenAI returned an empty copilot response.")
            parsed = _parse_structured_response(output_text, visible_paths=_visible_paths(context))
            return CopilotResult(
                content=parsed["answer"],
                suggested_files=parsed["suggested_files"],
                risk_flags=parsed["risk_flags"],
                confidence=parsed["confidence"],
                included_context_size=len(context_prompt),
                source="openai",
                model=settings.openai_model,
            )
        except Exception:
            logger.warning("OpenAI candidate copilot failed; using fallback response.", exc_info=True)
            return _fallback_result(
                session=session,
                question=question,
                context=context,
                previous_messages=previous_messages,
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
        "You may provide code, explanations, debugging steps, file-specific changes, and tradeoff analysis. "
        "Directly answer candidate questions and ask clarifying questions only when truly needed. "
        "Be practical and concise. Do not always provide a perfect final solution immediately; explain reasoning, "
        "risks, and verification steps. If the candidate asks for final code, help with code while naming assumptions "
        "and risks. Do not mention hidden evaluation criteria or invent access to secrets, services, files, or test "
        "results. Never claim you executed tests unless the provided context says the platform produced that output. "
        "Never reveal scoring, hidden rubrics, hidden tests, or interviewer-only notes. "
        f"Current allowed mode: {mode}.\n\n"
        f"{_mode_guidance(mode)}\n\n"
        "Return only strict JSON with this exact shape: "
        '{"answer":"markdown answer","suggested_files":[{"path":"repo/path","reason":"why"}],'
        '"risk_flags":["short risk"],"confidence":"low|medium|high"}. '
        "Use suggested_files only for visible project paths from the provided context."
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
    context: dict[str, Any],
    question: str,
    previous_messages: list[AIMessage],
    mode: str,
) -> str:
    previous = [
        {
            "role": message.role.value,
            "content": message.content,
            "metadata": message.message_metadata,
        }
        for message in previous_messages[-12:]
    ]
    payload = {
        "ai_mode": mode,
        **context,
        "previous_messages": previous,
        "candidate_question": question,
    }
    return (
        "Answer the candidate using this candidate-safe JSON context. The answer field should be markdown. "
        "When code is useful, include fenced code blocks with a language tag in answer. "
        "Do not reference files that are not listed in visible_project_file_tree.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _parse_structured_response(raw_text: str, *, visible_paths: set[str]) -> dict[str, Any]:
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("Copilot response must be a JSON object.")

    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Copilot response must include a non-empty answer.")

    suggested_files: list[dict[str, str]] = []
    raw_suggested_files = payload.get("suggested_files")
    if isinstance(raw_suggested_files, list):
        for item in raw_suggested_files[:6]:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            reason = item.get("reason")
            if isinstance(path, str) and path in visible_paths:
                suggested_files.append(
                    {
                        "path": path,
                        "reason": reason if isinstance(reason, str) and reason.strip() else "Relevant to this answer.",
                    }
                )

    risk_flags: list[str] = []
    raw_risk_flags = payload.get("risk_flags")
    if isinstance(raw_risk_flags, list):
        risk_flags = [flag.strip() for flag in raw_risk_flags[:8] if isinstance(flag, str) and flag.strip()]

    confidence = payload.get("confidence")
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    return {
        "answer": answer.strip(),
        "suggested_files": suggested_files,
        "risk_flags": risk_flags,
        "confidence": confidence,
    }


def _visible_paths(context: dict[str, Any]) -> set[str]:
    raw_paths = context.get("visible_project_file_tree")
    if not isinstance(raw_paths, list):
        return set()
    return {path for path in raw_paths if isinstance(path, str)}


def _fallback_result(
    *,
    session: InterviewSession,
    question: str,
    context: dict[str, Any],
    previous_messages: list[AIMessage],
    source: str,
    model: str | None,
) -> CopilotResult:
    mode = _normalized_mode(session.interview.allowed_ai_mode)
    content = _fallback_reply(session=session, question=question, context=context, mode=mode)
    suggested_files = _fallback_suggested_files(context)
    risk_flags = _fallback_risk_flags(question)
    context_prompt = _build_context_prompt(
        context=context,
        question=question,
        previous_messages=previous_messages,
        mode=mode,
    )
    return CopilotResult(
        content=content,
        suggested_files=suggested_files,
        risk_flags=risk_flags,
        confidence="medium",
        included_context_size=len(context_prompt),
        source=source,
        model=model,
    )


def _fallback_reply(*, session: InterviewSession, question: str, context: dict[str, Any], mode: str) -> str:
    scenario = session.interview.scenario
    title = scenario.title if scenario else "the task"
    requirements = scenario.technical_requirements if scenario else []
    primary_requirement = requirements[0] if requirements else "make the smallest safe change that satisfies the task"
    current_file = context.get("current_file")
    current_file_path = current_file.get("path") if isinstance(current_file, dict) else None
    code_hint = f"`{current_file_path}`" if isinstance(current_file_path, str) and current_file_path else "the current file"

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
        f"Start in {code_hint}. Suggested approach:\n\n"
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


def _fallback_suggested_files(context: dict[str, Any]) -> list[dict[str, str]]:
    current_file = context.get("current_file")
    if isinstance(current_file, dict):
        path = current_file.get("path")
        if isinstance(path, str) and path:
            return [{"path": path, "reason": "Currently open file and likely the best starting point."}]

    latest_files = context.get("latest_saved_files")
    if isinstance(latest_files, list):
        for item in latest_files:
            if isinstance(item, dict) and item.get("file_type") == "source" and isinstance(item.get("path"), str):
                return [{"path": str(item["path"]), "reason": "Visible source file related to the task."}]
    return []


def _fallback_risk_flags(question: str) -> list[str]:
    lowered = question.lower()
    if "final code" in lowered or "just give" in lowered:
        return ["Verify the generated patch against the visible checks before submitting."]
    return []

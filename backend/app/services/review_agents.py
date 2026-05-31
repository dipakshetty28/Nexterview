from __future__ import annotations

import difflib
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


SCORING_WEIGHTS: dict[str, int] = {
    "code_quality": 15,
    "correctness": 20,
    "architecture": 15,
    "debugging_process": 15,
    "ai_usage": 15,
    "prompting_skill": 10,
    "communication": 10,
}


AGENT_DEFINITIONS: list[dict[str, str]] = [
    {
        "type": "code_quality",
        "label": "Code Quality Agent",
        "focus": "Review all changed files for readability, maintainability, naming, modularity, simplicity, duplication, and error handling.",
    },
    {
        "type": "correctness",
        "label": "Correctness Agent",
        "focus": "Check whether the submitted repo fixes the bug, implements the feature request, handles edge cases, and is verified.",
    },
    {
        "type": "architecture",
        "label": "Architecture Agent",
        "focus": "Evaluate project-level design choices, separation of concerns, extensibility, tradeoffs, and system boundaries.",
    },
    {
        "type": "security",
        "label": "Security Agent",
        "focus": "Review changed files for unsafe input handling, auth mistakes, injection risks, secret exposure, and risky patterns.",
    },
    {
        "type": "performance",
        "label": "Performance Agent",
        "focus": "Review changed files for inefficient loops, unnecessary work, database misuse, pagination, caching, and scalability bottlenecks.",
    },
    {
        "type": "ai_usage",
        "label": "AI Usage Agent",
        "focus": "Review the AI transcript and telemetry to decide whether the candidate used AI productively and validated suggestions.",
    },
    {
        "type": "prompting_skill",
        "label": "Prompting Skill Agent",
        "focus": "Review prompt specificity, context, decomposition, follow-up quality, independence, and verification behavior.",
    },
    {
        "type": "debugging_process",
        "label": "Debugging Process Agent",
        "focus": "Review telemetry, test runs, notes, and code diffs for root-cause analysis, hypotheses, incremental validation, and isolation.",
    },
    {
        "type": "communication",
        "label": "Communication Agent",
        "focus": "Review the candidate notes and root-cause summary for clarity, tradeoffs, teammate usefulness, and verification detail.",
    },
    {
        "type": "hiring_recommendation",
        "label": "Hiring Recommendation Agent",
        "focus": "Combine all agent reviews into an overall hiring recommendation with evidence and risks.",
    },
]


@dataclass(frozen=True)
class AgentReviewResult:
    agent_type: str
    agent_label: str
    score: int
    strengths: list[str]
    weaknesses: list[str]
    evidence: list[str]
    risk_flags: list[str]
    recommendation: str
    explanation: str
    raw_response: dict[str, Any]


class RepoSubmissionReviewer:
    def review(self, context: dict[str, Any]) -> list[AgentReviewResult]:
        reviews: list[AgentReviewResult] = []
        for agent in AGENT_DEFINITIONS:
            if agent["type"] == "hiring_recommendation":
                continue
            reviews.append(self._review_agent(context=context, agent=agent, prior_reviews=reviews))

        hiring_context = {**context, "prior_agent_reviews": [asdict(review) for review in reviews]}
        reviews.append(
            self._review_agent(
                context=hiring_context,
                agent=next(agent for agent in AGENT_DEFINITIONS if agent["type"] == "hiring_recommendation"),
                prior_reviews=reviews,
            )
        )
        return reviews

    def _review_agent(
        self,
        *,
        context: dict[str, Any],
        agent: dict[str, str],
        prior_reviews: list[AgentReviewResult],
    ) -> AgentReviewResult:
        if settings.openai_api_key.strip():
            try:
                return _openai_agent_review(context=context, agent=agent)
            except Exception:
                logger.warning("OpenAI review agent failed; using fallback review.", exc_info=True)
        return _fallback_agent_review(context=context, agent=agent, prior_reviews=prior_reviews)


def generate_file_diffs(
    *,
    original_files: list[dict[str, Any]],
    candidate_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    original_by_path = {_validated_diff_path(file_payload): file_payload for file_payload in original_files}
    candidate_by_path = {_validated_diff_path(file_payload): file_payload for file_payload in candidate_files}
    diffs: list[dict[str, Any]] = []

    for path in sorted(set(original_by_path) | set(candidate_by_path)):
        original = original_by_path.get(path)
        candidate = candidate_by_path.get(path)
        original_content = _file_content(original)
        candidate_content = _file_content(candidate)
        if original is not None and candidate is not None and original_content == candidate_content:
            continue

        status = "modified"
        if original is None:
            status = "added"
        elif candidate is None:
            status = "deleted"

        diff_lines = list(
            difflib.unified_diff(
                original_content.splitlines(),
                candidate_content.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
        source = candidate or original or {}
        diffs.append(
            {
                "path": path,
                "status": status,
                "language": _file_string(source, "language"),
                "file_type": _file_string(source, "file_type"),
                "additions": additions,
                "deletions": deletions,
                "diff": "\n".join(diff_lines),
            }
        )

    return diffs


def summarize_ai_usage(context: dict[str, Any]) -> dict[str, Any]:
    transcript = _list_of_dicts(context.get("ai_chat_transcript"))
    telemetry_events = _list_of_dicts(context.get("telemetry_events"))
    user_messages = [message for message in transcript if message.get("role") == "user"]
    assistant_messages = [message for message in transcript if message.get("role") == "assistant"]
    prompts_with_context = [
        message
        for message in user_messages
        if isinstance(message.get("metadata"), dict) and message["metadata"].get("current_file_path")
    ]
    test_run_count = sum(1 for event in telemetry_events if event.get("event_type") == "test_run")
    confidence_values = [
        message.get("metadata", {}).get("confidence")
        for message in assistant_messages
        if isinstance(message.get("metadata"), dict)
    ]
    validated_suggestions = test_run_count > 0 and bool(assistant_messages)
    summary = (
        "Candidate used AI with file context and followed with validation signals."
        if validated_suggestions and prompts_with_context
        else "Candidate AI usage has limited validation evidence."
        if assistant_messages
        else "Candidate did not use the AI copilot in this session."
    )
    return {
        "candidate_prompt_count": len(user_messages),
        "assistant_response_count": len(assistant_messages),
        "prompts_with_file_context": len(prompts_with_context),
        "test_run_count": test_run_count,
        "response_confidence_values": [value for value in confidence_values if isinstance(value, str)],
        "validated_suggestions": validated_suggestions,
        "summary": summary,
    }


def build_score_breakdown(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reviews_by_type = {str(review.get("agent_type")): review for review in reviews}
    breakdown: list[dict[str, Any]] = []
    for agent_type, weight in SCORING_WEIGHTS.items():
        review = reviews_by_type.get(agent_type)
        score = _coerce_score(review.get("score") if review else None, default=0) if review else None
        breakdown.append(
            {
                "agent_type": agent_type,
                "label": _agent_label(agent_type),
                "weight": weight,
                "score": score,
                "weighted_score": round((score or 0) * weight / 100, 2) if score is not None else None,
            }
        )
    return breakdown


def weighted_score_from_breakdown(breakdown: list[dict[str, Any]]) -> float | None:
    if not any(item.get("score") is not None for item in breakdown):
        return None
    return round(sum(float(item.get("weighted_score") or 0) for item in breakdown), 2)


def recommendation_for_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 88:
        return "strong hire"
    if score >= 76:
        return "hire"
    if score >= 66:
        return "lean hire"
    if score >= 52:
        return "lean no hire"
    return "no hire"


def _openai_agent_review(*, context: dict[str, Any], agent: dict[str, str]) -> AgentReviewResult:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_request_timeout_seconds)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": _review_system_prompt(agent),
            },
            {
                "role": "user",
                "content": _review_user_prompt(context=context, agent=agent),
            },
        ],
    )
    output_text = response.output_text.strip()
    if not output_text:
        raise ValueError("OpenAI returned an empty review response.")
    payload = json.loads(output_text)
    return _agent_result_from_payload(payload=payload, agent=agent)


def _review_system_prompt(agent: dict[str, str]) -> str:
    return (
        "You are an internal evaluator in Nexterview, a corporate engineering interview platform. "
        "You may use interviewer-only rubric, hidden evaluation points, hidden tests, telemetry, AI transcript, "
        "candidate notes, file diffs, and GitHub branch or PR links because this review is not candidate-facing. "
        "Do not reveal secrets or invent runtime results beyond the supplied test output. "
        f"Agent: {agent['label']}. Focus: {agent['focus']} "
        "Return only strict JSON with this shape: "
        '{"score":0-100,"strengths":["..."],"weaknesses":["..."],"evidence":["..."],'
        '"risk_flags":["..."],"recommendation":"...","explanation":"..."}.'
    )


def _review_user_prompt(*, context: dict[str, Any], agent: dict[str, str]) -> str:
    return (
        f"Evaluate this repo-based submission as {agent['label']}. "
        "Use file-level evidence. Mention specific files when relevant.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )


def _agent_result_from_payload(*, payload: dict[str, Any], agent: dict[str, str]) -> AgentReviewResult:
    if not isinstance(payload, dict):
        raise ValueError("Review response must be a JSON object.")
    return AgentReviewResult(
        agent_type=agent["type"],
        agent_label=agent["label"],
        score=_coerce_score(payload.get("score"), default=65),
        strengths=_string_list(payload.get("strengths"), fallback=["Identified meaningful evidence in the submission."]),
        weaknesses=_string_list(payload.get("weaknesses"), fallback=["No major weakness was supplied by the reviewer."]),
        evidence=_string_list(payload.get("evidence"), fallback=["Reviewer used the submitted repo context."]),
        risk_flags=_string_list(payload.get("risk_flags"), fallback=[]),
        recommendation=_clean_text(payload.get("recommendation"), fallback="review complete", max_length=120),
        explanation=_clean_text(payload.get("explanation"), fallback="The reviewer completed the evaluation.", max_length=4000),
        raw_response=payload,
    )


def _fallback_agent_review(
    *,
    context: dict[str, Any],
    agent: dict[str, str],
    prior_reviews: list[AgentReviewResult],
) -> AgentReviewResult:
    changed_files = _list_of_dicts(context.get("file_diffs"))
    telemetry_events = _list_of_dicts(context.get("telemetry_events"))
    test_outputs = [str(item) for item in context.get("test_run_outputs", []) if item]
    notes = str(context.get("candidate_notes") or "")
    ai_usage = summarize_ai_usage(context)
    score = _fallback_score(agent["type"], changed_files, telemetry_events, test_outputs, notes, ai_usage, prior_reviews)
    changed_paths = [str(file_diff.get("path")) for file_diff in changed_files[:5] if file_diff.get("path")]
    evidence = [
        f"Changed files reviewed: {', '.join(changed_paths) if changed_paths else 'none detected'}.",
        f"Test run outputs available: {len(test_outputs)}.",
    ]
    if ai_usage["candidate_prompt_count"]:
        evidence.append(f"AI prompts reviewed: {ai_usage['candidate_prompt_count']}.")
    if notes:
        evidence.append("Candidate provided a root-cause or validation summary.")

    strengths = _fallback_strengths(agent["type"], changed_files, test_outputs, notes, ai_usage)
    weaknesses = _fallback_weaknesses(agent["type"], changed_files, test_outputs, notes, ai_usage)
    risk_flags = _fallback_risk_flags(agent["type"], changed_files, test_outputs, notes, ai_usage)
    recommendation = _fallback_recommendation(agent["type"], score, prior_reviews)
    return AgentReviewResult(
        agent_type=agent["type"],
        agent_label=agent["label"],
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        evidence=evidence,
        risk_flags=risk_flags,
        recommendation=recommendation,
        explanation=f"{agent['label']} evaluated the repo submission using changed files, diffs, telemetry, tests, notes, and AI transcript.",
        raw_response={
            "source": "fallback",
            "agent_focus": agent["focus"],
            "ai_usage_analysis": ai_usage if agent["type"] in {"ai_usage", "prompting_skill"} else None,
        },
    )


def _fallback_score(
    agent_type: str,
    changed_files: list[dict[str, Any]],
    telemetry_events: list[dict[str, Any]],
    test_outputs: list[str],
    notes: str,
    ai_usage: dict[str, Any],
    prior_reviews: list[AgentReviewResult],
) -> int:
    if agent_type == "hiring_recommendation" and prior_reviews:
        breakdown = build_score_breakdown([asdict(review) for review in prior_reviews])
        weighted = weighted_score_from_breakdown(breakdown)
        return _coerce_score(weighted, default=65)

    score = 62
    if changed_files:
        score += 8
    if len(changed_files) >= 2:
        score += 5
    if any("passed" in output.lower() for output in test_outputs):
        score += 10
    if any("failed" in output.lower() for output in test_outputs):
        score -= 6
    if len(notes.strip()) >= 80:
        score += 6
    if sum(1 for event in telemetry_events if event.get("event_type") == "test_run") >= 1:
        score += 5

    if agent_type == "ai_usage":
        score += 10 if ai_usage["validated_suggestions"] else -4
        score += 5 if ai_usage["prompts_with_file_context"] else 0
    if agent_type == "prompting_skill":
        score += min(8, ai_usage["prompts_with_file_context"] * 3)
    if agent_type == "communication":
        score += 8 if "root cause" in notes.lower() or "verified" in notes.lower() else -4
    if agent_type == "security":
        score -= 12 if _has_risky_security_pattern(changed_files) else 0
    if agent_type == "performance":
        score -= 8 if _has_risky_performance_pattern(changed_files) else 0

    return max(0, min(100, score))


def _fallback_strengths(
    agent_type: str,
    changed_files: list[dict[str, Any]],
    test_outputs: list[str],
    notes: str,
    ai_usage: dict[str, Any],
) -> list[str]:
    strengths = []
    if changed_files:
        strengths.append("Changed files are captured with file-level diffs for review.")
    if any("passed" in output.lower() for output in test_outputs):
        strengths.append("Candidate included passing validation output.")
    if len(notes.strip()) >= 80:
        strengths.append("Candidate supplied a meaningful root-cause or verification summary.")
    if agent_type in {"ai_usage", "prompting_skill"} and ai_usage["candidate_prompt_count"]:
        strengths.append("AI transcript is available for evaluating collaboration behavior.")
    return strengths or ["Submission has enough repo context for internal evaluation."]


def _fallback_weaknesses(
    agent_type: str,
    changed_files: list[dict[str, Any]],
    test_outputs: list[str],
    notes: str,
    ai_usage: dict[str, Any],
) -> list[str]:
    weaknesses = []
    if not changed_files:
        weaknesses.append("No changed files were detected in the submission.")
    if not test_outputs:
        weaknesses.append("No test run output was included with the final submission.")
    if len(notes.strip()) < 40:
        weaknesses.append("Candidate explanation is too thin for a corporate debugging handoff.")
    if agent_type in {"ai_usage", "prompting_skill"} and not ai_usage["candidate_prompt_count"]:
        weaknesses.append("No AI prompts were available to evaluate AI collaboration quality.")
    return weaknesses or ["No high-confidence weakness was detected by the fallback reviewer."]


def _fallback_risk_flags(
    agent_type: str,
    changed_files: list[dict[str, Any]],
    test_outputs: list[str],
    notes: str,
    ai_usage: dict[str, Any],
) -> list[str]:
    flags = []
    if agent_type == "security" and _has_risky_security_pattern(changed_files):
        flags.append("Changed files contain risky security-sensitive patterns.")
    if agent_type == "performance" and _has_risky_performance_pattern(changed_files):
        flags.append("Changed files contain potentially inefficient logic.")
    if any("failed" in output.lower() for output in test_outputs):
        flags.append("Latest submitted test output includes a failure signal.")
    if agent_type == "ai_usage" and ai_usage["candidate_prompt_count"] and not ai_usage["validated_suggestions"]:
        flags.append("AI suggestions were not clearly validated with a test run.")
    if agent_type == "communication" and len(notes.strip()) < 40:
        flags.append("Final explanation may not be useful enough for teammates.")
    return flags


def _fallback_recommendation(agent_type: str, score: int, prior_reviews: list[AgentReviewResult]) -> str:
    if agent_type == "hiring_recommendation":
        return recommendation_for_score(score) or "review complete"
    if score >= 80:
        return "strong signal"
    if score >= 65:
        return "acceptable signal"
    if score >= 50:
        return "mixed signal"
    return "weak signal"


def _has_risky_security_pattern(changed_files: list[dict[str, Any]]) -> bool:
    risky = re.compile(r"\b(eval|exec|pickle\.loads|subprocess\.Popen|shell=True|password\s*=|api[_-]?key)\b", re.IGNORECASE)
    return any(risky.search(str(file_diff.get("diff") or "")) for file_diff in changed_files)


def _has_risky_performance_pattern(changed_files: list[dict[str, Any]]) -> bool:
    risky = re.compile(r"for\s+.+\n\s+for\s+|while\s+true|select\s+\*", re.IGNORECASE)
    return any(risky.search(str(file_diff.get("diff") or "")) for file_diff in changed_files)


def _validated_diff_path(file_payload: dict[str, Any]) -> str:
    path = file_payload.get("path")
    if not isinstance(path, str):
        raise ValueError("File diff payloads require string paths.")
    cleaned = path.strip().replace("\\", "/")
    pure_path = PurePosixPath(cleaned)
    if not cleaned or cleaned.startswith("/") or pure_path.is_absolute() or ".." in pure_path.parts:
        raise ValueError("File diff paths must be relative POSIX paths without parent traversal.")
    if ":" in pure_path.parts[0]:
        raise ValueError("File diff paths must not include drive letters.")
    return cleaned


def _file_content(file_payload: dict[str, Any] | None) -> str:
    if not file_payload:
        return ""
    content = file_payload.get("content")
    return content if isinstance(content, str) else ""


def _file_string(file_payload: dict[str, Any], key: str) -> str:
    value = file_payload.get(key)
    return value if isinstance(value, str) and value else "text"


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any, *, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    cleaned = [item.strip() for item in value[:12] if isinstance(item, str) and item.strip()]
    return cleaned or fallback


def _clean_text(value: Any, *, fallback: str, max_length: int) -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.strip()
    return cleaned[:max_length] if cleaned else fallback


def _coerce_score(value: Any, *, default: int) -> int:
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return default


def _agent_label(agent_type: str) -> str:
    for agent in AGENT_DEFINITIONS:
        if agent["type"] == agent_type:
            return agent["label"]
    return agent_type.replace("_", " ").title()

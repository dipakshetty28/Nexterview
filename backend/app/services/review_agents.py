from __future__ import annotations

import difflib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
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

STRICT_RECOMMENDATIONS = {"strong_hire", "hire", "lean_hire", "lean_no_hire", "no_hire"}


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
    expected: list[str] = field(default_factory=list)
    observed: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    confidence: float = 0.6
    review_source: str = "openai"


class ReviewAgentError(RuntimeError):
    """Raised when an AI-backed reviewer cannot produce a trustworthy review."""


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
        if not settings.openai_api_key.strip():
            return _fallback_agent_review(context=context, agent=agent, prior_reviews=prior_reviews)
        try:
            return _openai_agent_review(context=context, agent=agent)
        except Exception as exc:
            logger.warning("OpenAI review agent failed; marking review as failed.", exc_info=True)
            raise ReviewAgentError(f"{agent['label']} could not produce a valid review.") from exc


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
        return "strong_hire"
    if score >= 76:
        return "hire"
    if score >= 66:
        return "lean_hire"
    if score >= 52:
        return "lean_no_hire"
    return "no_hire"


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
        "candidate notes, and file diffs because this review is not candidate-facing. "
        "Do not reveal secrets or invent runtime results beyond the supplied test output. "
        "Every score must be grounded in supplied evidence. Penalize failed tests, no meaningful code changes, "
        "thin explanations, and lazy AI usage. "
        f"Agent: {agent['label']}. Focus: {agent['focus']} "
        "Return only strict JSON with this shape: "
        '{"agent_name":"...","score":0-100,"recommendation":"strong_hire|hire|lean_hire|lean_no_hire|no_hire",'
        '"summary":"...","expected":["..."],"observed":["..."],'
        '"evidence":[{"type":"code|test|prompt|telemetry|explanation","detail":"..."}],'
        '"strengths":["..."],"weaknesses":["..."],"risk_flags":["..."],'
        '"follow_up_questions":["..."],"confidence":0.0}.'
    )


def _review_user_prompt(*, context: dict[str, Any], agent: dict[str, str]) -> str:
    return (
        f"Evaluate this repo-based submission as {agent['label']}. "
        "Use file-level evidence. Mention specific files when relevant. Compare expected behavior, visible requirements, "
        "hidden evaluation points, expected solution notes, candidate files, tests, telemetry, AI transcript, and final explanation. "
        "If tests failed, the correctness score must be low unless the supplied evidence clearly justifies otherwise. "
        "If no meaningful code changes were made, code quality and correctness must not pass by default.\n\n"
        f"{json.dumps(context, indent=2, default=str)}"
    )


def _agent_result_from_payload(*, payload: dict[str, Any], agent: dict[str, str]) -> AgentReviewResult:
    if not isinstance(payload, dict):
        raise ValueError("Review response must be a JSON object.")
    score = _coerce_score(payload.get("score"), default=65)
    evidence_items = _evidence_items(payload.get("evidence"))
    summary = _clean_text(
        payload.get("summary") or payload.get("explanation"),
        fallback="The reviewer completed the evaluation.",
        max_length=4000,
    )
    recommendation = _clean_recommendation(payload.get("recommendation"), score=score)
    confidence = _coerce_confidence(payload.get("confidence"), default=0.7)
    strict_payload = {
        **payload,
        "agent_name": _clean_text(payload.get("agent_name"), fallback=agent["label"], max_length=120),
        "score": score,
        "recommendation": recommendation,
        "summary": summary,
        "expected": _string_list(payload.get("expected"), fallback=[]),
        "observed": _string_list(payload.get("observed"), fallback=[]),
        "evidence": evidence_items,
        "follow_up_questions": _string_list(payload.get("follow_up_questions"), fallback=[]),
        "confidence": confidence,
        "review_source": "openai",
    }
    return AgentReviewResult(
        agent_type=agent["type"],
        agent_label=agent["label"],
        score=score,
        strengths=_string_list(payload.get("strengths"), fallback=["Identified meaningful evidence in the submission."]),
        weaknesses=_string_list(payload.get("weaknesses"), fallback=["No major weakness was supplied by the reviewer."]),
        evidence=_evidence_strings(evidence_items, fallback=["Reviewer used the submitted repo context."]),
        risk_flags=_string_list(payload.get("risk_flags"), fallback=[]),
        recommendation=recommendation,
        explanation=summary,
        raw_response=strict_payload,
        expected=strict_payload["expected"],
        observed=strict_payload["observed"],
        follow_up_questions=strict_payload["follow_up_questions"],
        confidence=confidence,
        review_source="openai",
    )


def _fallback_agent_review(
    *,
    context: dict[str, Any],
    agent: dict[str, str],
    prior_reviews: list[AgentReviewResult],
) -> AgentReviewResult:
    signals = _review_signals(context)
    score = _fallback_score(agent["type"], signals, prior_reviews)
    evidence_items = _fallback_evidence_items(agent["type"], signals)
    strengths = _fallback_strengths(agent["type"], signals)
    weaknesses = _fallback_weaknesses(agent["type"], signals)
    risk_flags = _fallback_risk_flags(agent["type"], signals)
    recommendation = _fallback_recommendation(agent["type"], score, prior_reviews, signals)
    expected = _fallback_expected(context)
    observed = _fallback_observed(signals)
    follow_up_questions = _fallback_follow_up_questions(agent["type"], signals)
    confidence = _fallback_confidence(signals)
    summary = _fallback_summary(agent["label"], score, signals, weaknesses)
    raw_response = {
        "agent_name": agent["label"],
        "score": score,
        "recommendation": recommendation,
        "summary": summary,
        "expected": expected,
        "observed": observed,
        "evidence": evidence_items,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risk_flags": risk_flags,
        "follow_up_questions": follow_up_questions,
        "confidence": confidence,
        "review_source": "rule_based_fallback",
        "agent_focus": agent["focus"],
        "ai_usage_analysis": signals["ai_usage"] if agent["type"] in {"ai_usage", "prompting_skill"} else None,
    }
    return AgentReviewResult(
        agent_type=agent["type"],
        agent_label=agent["label"],
        score=score,
        strengths=strengths,
        weaknesses=weaknesses,
        evidence=_evidence_strings(evidence_items, fallback=["Rule-based reviewer used the submitted repo context."]),
        risk_flags=risk_flags,
        recommendation=recommendation,
        explanation=summary,
        raw_response=raw_response,
        expected=expected,
        observed=observed,
        follow_up_questions=follow_up_questions,
        confidence=confidence,
        review_source="rule_based_fallback",
    )


def _fallback_score(
    agent_type: str,
    signals: dict[str, Any],
    prior_reviews: list[AgentReviewResult],
) -> int:
    if agent_type == "hiring_recommendation" and prior_reviews:
        breakdown = build_score_breakdown([asdict(review) for review in prior_reviews])
        weighted = weighted_score_from_breakdown(breakdown)
        score = _coerce_score(weighted, default=55)
        if signals["final_tests_failed"] or _has_serious_correctness_failure(prior_reviews):
            score = min(score, 55)
        if signals["no_meaningful_code_change"]:
            score = min(score, 45)
        if _has_serious_security_risk(prior_reviews):
            score = min(score, 55)
        return score

    changed_files = signals["changed_files"]
    test_run_count = signals["test_run_count"]
    notes = signals["notes"]
    ai_usage = signals["ai_usage"]
    no_change = signals["no_meaningful_code_change"]
    failed_tests = signals["final_tests_failed"]
    passed_tests = signals["final_tests_passed"]

    score = 50
    if changed_files:
        score += 10
    if signals["meaningful_change_count"] >= 2:
        score += 6
    if passed_tests:
        score += 12
    if failed_tests:
        score -= 20
    if len(notes.strip()) >= 80:
        score += 7
    if test_run_count >= 1:
        score += 5
    if no_change:
        score -= 25

    if agent_type == "ai_usage":
        score = 45
        if ai_usage["candidate_prompt_count"]:
            score += 10
        if ai_usage["validated_suggestions"]:
            score += 15
        if ai_usage["prompts_with_file_context"]:
            score += 8
        if signals["lazy_prompt_count"]:
            score -= 25
    if agent_type == "prompting_skill":
        score = 45 + min(15, ai_usage["prompts_with_file_context"] * 5)
        if signals["validation_prompt_count"]:
            score += 10
        if signals["lazy_prompt_count"]:
            score -= 20
    if agent_type == "communication":
        score = 45
        if len(notes.strip()) >= 80:
            score += 18
        if "root cause" in notes.lower() or "verified" in notes.lower() or "tradeoff" in notes.lower():
            score += 10
        if len(notes.strip()) < 40:
            score -= 15
    if agent_type == "security":
        score -= 18 if _has_risky_security_pattern(changed_files) else 0
    if agent_type == "performance":
        score -= 12 if _has_risky_performance_pattern(changed_files) else 0
    if agent_type == "correctness" and failed_tests:
        score = min(score, 42)
    if agent_type in {"correctness", "code_quality", "architecture", "debugging_process"} and no_change:
        score = min(score, 45)

    return max(0, min(100, score))


def _fallback_strengths(
    agent_type: str,
    signals: dict[str, Any],
) -> list[str]:
    changed_files = signals["changed_files"]
    notes = signals["notes"]
    ai_usage = signals["ai_usage"]
    strengths = []
    if signals["meaningful_change_count"]:
        strengths.append("Changed files are captured with file-level diffs for review.")
    if signals["final_tests_passed"]:
        strengths.append("Candidate included passing validation output.")
    if len(notes.strip()) >= 80:
        strengths.append("Candidate supplied a meaningful root-cause or verification summary.")
    if agent_type in {"ai_usage", "prompting_skill"} and ai_usage["candidate_prompt_count"]:
        strengths.append("AI transcript is available for evaluating collaboration behavior.")
    if agent_type == "debugging_process" and signals["test_run_count"]:
        strengths.append("Telemetry shows at least one validation attempt.")
    return strengths or ["Submission has limited positive evidence; score is intentionally conservative."]


def _fallback_weaknesses(
    agent_type: str,
    signals: dict[str, Any],
) -> list[str]:
    notes = signals["notes"]
    ai_usage = signals["ai_usage"]
    weaknesses = []
    if signals["no_meaningful_code_change"]:
        weaknesses.append("No changed files were detected in the submission.")
    if not signals["test_outputs"] and not signals["test_runs"]:
        weaknesses.append("No test run output was included with the final submission.")
    if signals["final_tests_failed"]:
        weaknesses.append("Final validation did not pass, so correctness evidence is weak.")
    if len(notes.strip()) < 40:
        weaknesses.append("Candidate explanation is too thin for a corporate debugging handoff.")
    if agent_type in {"ai_usage", "prompting_skill"} and not ai_usage["candidate_prompt_count"]:
        weaknesses.append("No AI prompts were available to evaluate AI collaboration quality.")
    if agent_type in {"ai_usage", "prompting_skill"} and signals["lazy_prompt_count"]:
        weaknesses.append("AI prompts include low-independence requests for final code or complete solutions.")
    return weaknesses or ["No high-confidence weakness was detected by the fallback reviewer."]


def _fallback_risk_flags(
    agent_type: str,
    signals: dict[str, Any],
) -> list[str]:
    changed_files = signals["changed_files"]
    notes = signals["notes"]
    ai_usage = signals["ai_usage"]
    flags = []
    if agent_type == "security" and _has_risky_security_pattern(changed_files):
        flags.append("Serious security risk: changed files contain risky security-sensitive patterns.")
    if agent_type == "performance" and _has_risky_performance_pattern(changed_files):
        flags.append("Changed files contain potentially inefficient logic.")
    if signals["final_tests_failed"]:
        flags.append("Final tests failed or errored.")
    if signals["no_meaningful_code_change"]:
        flags.append("No meaningful code changes detected.")
    if agent_type == "ai_usage" and ai_usage["candidate_prompt_count"] and not ai_usage["validated_suggestions"]:
        flags.append("AI suggestions were not clearly validated with a test run.")
    if agent_type in {"ai_usage", "prompting_skill"} and signals["lazy_prompt_count"]:
        flags.append("AI transcript includes low-effort solution-seeking prompts.")
    if agent_type == "communication" and len(notes.strip()) < 40:
        flags.append("Final explanation may not be useful enough for teammates.")
    return flags


def _fallback_recommendation(
    agent_type: str,
    score: int,
    prior_reviews: list[AgentReviewResult],
    signals: dict[str, Any],
) -> str:
    if agent_type == "hiring_recommendation":
        recommendation = recommendation_for_score(score) or "no_hire"
        if signals["final_tests_failed"] or signals["no_meaningful_code_change"] or _has_serious_security_risk(prior_reviews):
            return _cap_recommendation(recommendation, "lean_no_hire")
        return recommendation
    return recommendation_for_score(score) or "no_hire"


def _review_signals(context: dict[str, Any]) -> dict[str, Any]:
    changed_files = _list_of_dicts(context.get("file_diffs"))
    telemetry_events = _list_of_dicts(context.get("telemetry_events"))
    test_runs = _list_of_dicts(context.get("test_runs"))
    test_outputs = [str(item) for item in context.get("test_run_outputs", []) if item]
    notes = str(context.get("candidate_notes") or "")
    ai_usage = summarize_ai_usage(context)
    changed_paths = [str(file_diff.get("path")) for file_diff in changed_files if file_diff.get("path")]
    meaningful_change_count = sum(
        1
        for file_diff in changed_files
        if int(file_diff.get("additions") or 0) + int(file_diff.get("deletions") or 0) > 0
    )
    test_statuses = [str(test_run.get("status") or "").lower() for test_run in test_runs]
    output_text = "\n".join(test_outputs).lower()
    final_status = test_statuses[-1] if test_statuses else ""
    final_tests_failed = final_status in {"failed", "error", "timeout"} or bool(
        re.search(r"\b(failed|error|timeout|traceback)\b", output_text)
    )
    final_tests_passed = final_status == "passed" or bool(re.search(r"\bpassed\b", output_text)) and not final_tests_failed
    prompt_texts = [
        str(message.get("content") or "")
        for message in _list_of_dicts(context.get("ai_chat_transcript"))
        if message.get("role") == "user"
    ]
    lazy_prompt_count = sum(
        1
        for prompt in prompt_texts
        if any(
            phrase in prompt.lower()
            for phrase in (
                "give me final code",
                "write the final code",
                "solve this for me",
                "complete solution",
                "just give me the answer",
            )
        )
    )
    validation_prompt_count = sum(
        1
        for prompt in prompt_texts
        if any(keyword in prompt.lower() for keyword in ("test", "verify", "validate", "edge case", "regression"))
    )
    return {
        "changed_files": changed_files,
        "changed_paths": changed_paths,
        "meaningful_change_count": meaningful_change_count,
        "no_meaningful_code_change": meaningful_change_count == 0,
        "telemetry_events": telemetry_events,
        "test_runs": test_runs,
        "test_outputs": test_outputs,
        "test_run_count": sum(1 for event in telemetry_events if event.get("event_type") == "test_run") or len(test_runs),
        "final_tests_failed": final_tests_failed,
        "final_tests_passed": final_tests_passed,
        "notes": notes,
        "ai_usage": ai_usage,
        "lazy_prompt_count": lazy_prompt_count,
        "validation_prompt_count": validation_prompt_count,
    }


def _fallback_expected(context: dict[str, Any]) -> list[str]:
    scenario = context.get("scenario") if isinstance(context.get("scenario"), dict) else {}
    expected: list[str] = []
    for key in ("visible_requirements", "technical_requirements", "expected_behavior", "hidden_evaluation_points"):
        value = scenario.get(key)
        if isinstance(value, list):
            expected.extend(str(item) for item in value if isinstance(item, str) and item.strip())
    solution_summary = scenario.get("expected_solution_summary") or context.get("expected_solution_summary")
    if isinstance(solution_summary, str) and solution_summary.strip():
        expected.append(f"Expected solution: {solution_summary.strip()}")
    return _dedupe_strings(expected)[:12] or ["Meet the scenario requirements and pass validation."]


def _fallback_observed(signals: dict[str, Any]) -> list[str]:
    changed_paths = signals["changed_paths"]
    observed = [
        f"Changed files: {', '.join(changed_paths[:8]) if changed_paths else 'none detected'}.",
        f"Test attempts: {signals['test_run_count']}.",
        "Final tests passed." if signals["final_tests_passed"] else "Final tests did not pass or were not available.",
    ]
    if signals["ai_usage"]["candidate_prompt_count"]:
        observed.append(f"AI prompts: {signals['ai_usage']['candidate_prompt_count']}.")
    if signals["notes"]:
        observed.append("Candidate submitted a final explanation.")
    return observed


def _fallback_evidence_items(agent_type: str, signals: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        {
            "type": "code",
            "detail": f"Changed files reviewed: {', '.join(signals['changed_paths'][:8]) if signals['changed_paths'] else 'none detected'}.",
        },
        {
            "type": "test",
            "detail": (
                "Final validation passed."
                if signals["final_tests_passed"]
                else "Final validation failed, errored, or did not provide a passing signal."
            ),
        },
        {"type": "telemetry", "detail": f"Recorded test run events: {signals['test_run_count']}."},
        {
            "type": "explanation",
            "detail": (
                "Candidate final explanation was detailed enough for review."
                if len(signals["notes"].strip()) >= 80
                else "Candidate final explanation was brief or missing."
            ),
        },
    ]
    if agent_type in {"ai_usage", "prompting_skill"}:
        items.append({"type": "prompt", "detail": f"Candidate AI prompts reviewed: {signals['ai_usage']['candidate_prompt_count']}."})
    return items


def _fallback_follow_up_questions(agent_type: str, signals: dict[str, Any]) -> list[str]:
    questions = []
    if signals["final_tests_failed"]:
        questions.append("Walk me through the failing tests and what you would try next.")
    if signals["no_meaningful_code_change"]:
        questions.append("What concrete code changes did you intend to make, and why are they absent from the diff?")
    if agent_type == "ai_usage" and signals["lazy_prompt_count"]:
        questions.append("How did you validate the AI suggestions instead of copying them directly?")
    if agent_type == "architecture":
        questions.append("What boundaries or abstractions would you keep if this change grew next quarter?")
    if agent_type == "security":
        questions.append("What data leakage or input-validation risks did you check before submitting?")
    if not questions:
        questions.append("What evidence gives you the highest confidence that this solution meets the requirements?")
    return questions[:4]


def _fallback_confidence(signals: dict[str, Any]) -> float:
    confidence = 0.55
    if signals["test_runs"] or signals["test_outputs"]:
        confidence += 0.15
    if signals["changed_files"]:
        confidence += 0.1
    if signals["notes"]:
        confidence += 0.05
    return round(min(confidence, 0.85), 2)


def _fallback_summary(agent_label: str, score: int, signals: dict[str, Any], weaknesses: list[str]) -> str:
    if signals["final_tests_failed"]:
        return (
            f"{agent_label} assigned {score}/100 because final validation failed or errored. "
            "The review is conservative and grounded in test evidence, diffs, telemetry, and the candidate explanation. "
            f"Primary concern: {weaknesses[0] if weaknesses else 'failed validation'}"
        )
    if signals["no_meaningful_code_change"]:
        return (
            f"{agent_label} assigned {score}/100 because no meaningful code changes were detected. "
            "Passing by default is not allowed without concrete implementation evidence."
        )
    return (
        f"{agent_label} assigned {score}/100 using rule-based evidence from changed files, tests, telemetry, "
        "AI transcript, and final explanation."
    )


def _has_serious_correctness_failure(prior_reviews: list[AgentReviewResult]) -> bool:
    return any(review.agent_type == "correctness" and review.score < 50 for review in prior_reviews)


def _has_serious_security_risk(prior_reviews: list[AgentReviewResult]) -> bool:
    return any(
        review.agent_type == "security" and any("serious security risk" in flag.lower() for flag in review.risk_flags)
        for review in prior_reviews
    )


def _cap_recommendation(recommendation: str, cap: str) -> str:
    order = ["no_hire", "lean_no_hire", "lean_hire", "hire", "strong_hire"]
    try:
        return order[min(order.index(recommendation), order.index(cap))]
    except ValueError:
        return cap


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


def _evidence_items(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value[:16]:
        if isinstance(item, dict):
            evidence_type = _clean_text(item.get("type"), fallback="code", max_length=40)
            detail = _clean_text(item.get("detail"), fallback="", max_length=700)
            if detail:
                items.append({"type": evidence_type, "detail": detail})
        elif isinstance(item, str) and item.strip():
            items.append({"type": "code", "detail": item.strip()[:700]})
    return items


def _evidence_strings(items: list[dict[str, str]], *, fallback: list[str]) -> list[str]:
    cleaned = [
        f"{item.get('type', 'evidence').title()}: {item.get('detail', '').strip()}"
        for item in items
        if item.get("detail", "").strip()
    ]
    return cleaned or fallback


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        cleaned = item.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            deduped.append(cleaned)
            seen.add(key)
    return deduped


def _clean_recommendation(value: Any, *, score: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in STRICT_RECOMMENDATIONS:
            return normalized
    return recommendation_for_score(_coerce_score(score, default=0)) or "no_hire"


def _coerce_confidence(value: Any, *, default: float) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except (TypeError, ValueError):
        return default


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

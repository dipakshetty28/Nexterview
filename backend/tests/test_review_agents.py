from __future__ import annotations

import builtins

import pytest

from app.core.config import settings
from app.services.review_agents import RepoSubmissionReviewer


def _review_context(
    *,
    file_diffs: list[dict[str, object]] | None = None,
    test_status: str = "passed",
    test_output: str = "2 passed",
    notes: str = "Root cause: totals ignored quantity. I fixed it and verified the regression tests.",
    ai_messages: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "scenario": {
            "title": "Fix order totals",
            "business_context": "Account managers rely on accurate order totals.",
            "visible_requirements": ["Multiply price by quantity."],
            "technical_requirements": ["Keep the FastAPI endpoint response stable."],
            "expected_behavior": ["Totals include item quantity."],
            "hidden_evaluation_points": ["Candidate should preserve status filtering."],
            "interviewer_rubric": ["Correctness depends on tests and quantity handling."],
            "expected_solution_summary": "Update total calculation and keep filters intact.",
        },
        "file_diffs": file_diffs
        if file_diffs is not None
        else [
            {
                "path": "app/services/orders.py",
                "status": "modified",
                "language": "python",
                "file_type": "source",
                "additions": 2,
                "deletions": 1,
                "diff": "@@\n- total += item.price\n+ total += item.price * item.quantity",
            }
        ],
        "test_runs": [
            {
                "status": test_status,
                "command": "python -m pytest",
                "passed_count": 0 if test_status != "passed" else 2,
                "failed_count": 1 if test_status != "passed" else 0,
                "total_count": 2,
                "failure_summary": "test_order_total failed" if test_status != "passed" else "",
            }
        ],
        "test_run_outputs": [test_output],
        "telemetry_events": [{"event_type": "test_run", "payload": {"status": test_status}}],
        "candidate_notes": notes,
        "ai_chat_transcript": ai_messages or [],
    }


def test_rule_based_review_penalizes_failed_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")

    reviews = RepoSubmissionReviewer().review(
        _review_context(test_status="failed", test_output="FAILED tests/test_orders.py::test_order_total")
    )
    by_type = {review.agent_type: review for review in reviews}

    assert by_type["correctness"].score <= 42
    assert "Final tests failed or errored." in by_type["correctness"].risk_flags
    assert by_type["hiring_recommendation"].recommendation in {"lean_no_hire", "no_hire"}
    assert by_type["correctness"].raw_response["review_source"] == "rule_based_fallback"
    assert by_type["correctness"].expected
    assert by_type["correctness"].observed


def test_rule_based_review_does_not_pass_no_change_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")

    reviews = RepoSubmissionReviewer().review(
        _review_context(
            file_diffs=[],
            test_status="passed",
            test_output="2 passed",
            notes="I think the existing implementation is fine.",
            ai_messages=[
                {
                    "role": "user",
                    "content": "Give me final code for this task.",
                    "metadata": {},
                }
            ],
        )
    )
    by_type = {review.agent_type: review for review in reviews}

    assert by_type["code_quality"].score <= 45
    assert by_type["correctness"].score <= 45
    assert by_type["hiring_recommendation"].recommendation in {"lean_no_hire", "no_hire"}
    assert "No meaningful code changes detected." in by_type["correctness"].risk_flags
    assert by_type["ai_usage"].score < 50


def test_review_falls_back_when_openai_sdk_is_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    real_import = builtins.__import__

    def missing_openai_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "openai":
            raise ModuleNotFoundError("No module named 'openai'", name="openai")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_openai_import)

    reviews = RepoSubmissionReviewer().review(_review_context())
    by_type = {review.agent_type: review for review in reviews}

    assert by_type["correctness"].raw_response["review_source"] == "rule_based_fallback"
    assert by_type["hiring_recommendation"].review_source == "rule_based_fallback"

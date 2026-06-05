from __future__ import annotations

from app.schemas.calibration import CalibrationSessionRead


_CALIBRATION_SESSIONS: list[dict[str, object]] = [
    {
        "id": "calibration-strong-platform-debugging",
        "tier": "strong",
        "candidate_name": "Maya Patel",
        "role_title": "Senior Backend Platform Engineer",
        "scenario_title": "Repair duplicate payment retry handling",
        "ai_mode": "Pair Programmer Mode",
        "status": "reviewed",
        "final_score": 91,
        "recommendation": "strong hire",
        "review_summary": (
            "The candidate isolated the retry/idempotency root cause, made a small service-level fix, added "
            "focused regression coverage, and used AI to compare edge cases before validating the final behavior."
        ),
        "expected_behavior": [
            "A retry must reuse the original idempotency key for the payment request.",
            "Duplicate provider callbacks should return the already-recorded transaction instead of creating a new one.",
            "Failed payment attempts should still be retriable without hiding real provider errors.",
        ],
        "observed_behavior": [
            "Moved idempotency key creation outside the retry loop and stored processed provider event ids.",
            "Added regression tests for duplicate callbacks, provider timeout retry, and failed authorization.",
            "Final test run passed all visible cases with no broad exception swallowing.",
        ],
        "differentiators": [
            "Started with a falsifiable hypothesis from the logs instead of making a broad rewrite.",
            "Asked AI to compare two implementation approaches and then chose the lower-risk scoped fix.",
            "Explained remaining production considerations without adding unrelated hardening.",
        ],
        "final_code_path": "app/services/payments.py",
        "final_code_language": "python",
        "final_code": (
            "from __future__ import annotations\n\n"
            "from dataclasses import dataclass\n"
            "from uuid import uuid4\n\n\n"
            "@dataclass(frozen=True)\n"
            "class PaymentAttempt:\n"
            "    order_id: str\n"
            "    amount_cents: int\n"
            "    provider_event_id: str | None = None\n\n\n"
            "class DuplicatePaymentEvent(Exception):\n"
            "    pass\n\n\n"
            "def charge_order(attempt: PaymentAttempt, *, gateway, store) -> dict[str, object]:\n"
            "    if attempt.provider_event_id and store.has_event(attempt.provider_event_id):\n"
            "        return store.transaction_for_event(attempt.provider_event_id)\n\n"
            "    idempotency_key = store.idempotency_key_for_order(attempt.order_id) or str(uuid4())\n"
            "    store.save_idempotency_key(attempt.order_id, idempotency_key)\n\n"
            "    response = gateway.charge(\n"
            "        order_id=attempt.order_id,\n"
            "        amount_cents=attempt.amount_cents,\n"
            "        idempotency_key=idempotency_key,\n"
            "    )\n"
            "    store.record_transaction(attempt.order_id, response)\n"
            "    if attempt.provider_event_id:\n"
            "        store.mark_event_processed(attempt.provider_event_id, response)\n"
            "    return response\n"
        ),
        "test_result": {
            "status": "passed",
            "command": "python -m pytest",
            "passed_count": 7,
            "failed_count": 0,
            "summary": "All payment retry and duplicate callback checks passed.",
            "output": (
                "tests/test_payments.py::test_duplicate_provider_event_returns_existing_transaction PASSED\n"
                "tests/test_payments.py::test_retry_reuses_existing_idempotency_key PASSED\n"
                "tests/test_payments.py::test_failed_authorization_is_not_marked_processed PASSED\n"
                "7 passed in 0.42s"
            ),
        },
        "ai_transcript": [
            {
                "role": "user",
                "content": (
                    "The duplicate charge appears after a timeout retry. The retry loop currently calls uuid4 "
                    "inside each attempt. Compare moving the key outside the loop with storing provider event ids."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Both are useful but cover different failure modes. Reusing the idempotency key prevents the "
                    "gateway from creating a second charge during retries. Storing provider event ids protects "
                    "callback processing. Add tests for both and keep provider failures visible."
                ),
            },
            {
                "role": "user",
                "content": "I added both checks. What edge case should I add before final submission?",
            },
            {
                "role": "assistant",
                "content": (
                    "Add a failed authorization case so the system does not mark an unsuccessful event as processed. "
                    "That protects legitimate retries after a real failure."
                ),
            },
        ],
        "agent_reviews": [
            {
                "agent_type": "correctness",
                "agent_label": "Correctness Agent",
                "score": 94,
                "recommendation": "strong signal",
                "summary": "Meets the visible behavior and covers the retry and duplicate callback paths.",
                "strengths": ["Root cause matched the log evidence.", "Regression tests cover the repaired paths."],
                "weaknesses": ["Could document provider-specific idempotency guarantees more explicitly."],
                "evidence": ["Final tests passed 7/7.", "Code preserves real provider errors."],
                "risk_flags": [],
            },
            {
                "agent_type": "ai_usage",
                "agent_label": "AI Usage Agent",
                "score": 92,
                "recommendation": "strong signal",
                "summary": "Used AI to compare implementation risks, then validated suggestions with targeted tests.",
                "strengths": ["Prompt included logs, suspected code path, and alternatives.", "Candidate challenged the AI with edge cases."],
                "weaknesses": [],
                "evidence": ["Follow-up asked specifically for remaining validation risk."],
                "risk_flags": [],
            },
            {
                "agent_type": "communication",
                "agent_label": "Communication Agent",
                "score": 88,
                "recommendation": "hire",
                "summary": "Final explanation tied cause, fix, and verification together clearly.",
                "strengths": ["Concise root cause summary.", "Named residual production considerations."],
                "weaknesses": ["Could include a short migration note if event storage were new."],
                "evidence": ["Candidate distinguished retry behavior from callback idempotency."],
                "risk_flags": [],
            },
        ],
    },
    {
        "id": "calibration-average-frontend-feature",
        "tier": "average",
        "candidate_name": "Jordan Lee",
        "role_title": "Full-Stack Product Engineer",
        "scenario_title": "Add feedback form validation and review status",
        "ai_mode": "Senior Engineer Mode",
        "status": "reviewed",
        "final_score": 68,
        "recommendation": "lean hire",
        "review_summary": (
            "The candidate delivered the main workflow and passed visible tests, but the solution had uneven edge-case "
            "coverage and relied on AI for broad implementation guidance without fully validating accessibility and error states."
        ),
        "expected_behavior": [
            "Feedback form validates required rating and comment fields before submission.",
            "API returns field-level validation errors in a stable response shape.",
            "Interviewer review status updates without dropping existing feedback entries.",
        ],
        "observed_behavior": [
            "Implemented happy-path form validation and API persistence.",
            "Passed visible unit tests for successful submission and missing rating.",
            "Missed a server-side comment length test and used a generic error message for network failure.",
        ],
        "differentiators": [
            "Solved the core flow but validated mostly against visible tests.",
            "AI prompts were understandable but often asked for full components instead of comparing risk.",
            "Final explanation named what changed but did not deeply discuss tradeoffs or failure handling.",
        ],
        "final_code_path": "frontend/app/feedback/form.tsx",
        "final_code_language": "tsx",
        "final_code": (
            "\"use client\";\n\n"
            "import { useState } from \"react\";\n\n"
            "type FeedbackPayload = { rating: number; comment: string };\n\n"
            "export function FeedbackForm({ onSubmit }: { onSubmit: (payload: FeedbackPayload) => Promise<void> }) {\n"
            "  const [rating, setRating] = useState(0);\n"
            "  const [comment, setComment] = useState(\"\");\n"
            "  const [error, setError] = useState<string | null>(null);\n"
            "  const [isSubmitting, setIsSubmitting] = useState(false);\n\n"
            "  async function submitForm() {\n"
            "    if (!rating) {\n"
            "      setError(\"Choose a rating before submitting.\");\n"
            "      return;\n"
            "    }\n"
            "    if (!comment.trim()) {\n"
            "      setError(\"Add a short comment before submitting.\");\n"
            "      return;\n"
            "    }\n"
            "    setIsSubmitting(true);\n"
            "    setError(null);\n"
            "    try {\n"
            "      await onSubmit({ rating, comment: comment.trim() });\n"
            "    } catch {\n"
            "      setError(\"Feedback could not be saved. Try again.\");\n"
            "    } finally {\n"
            "      setIsSubmitting(false);\n"
            "    }\n"
            "  }\n\n"
            "  return null;\n"
            "}\n"
        ),
        "test_result": {
            "status": "passed",
            "command": "npm test",
            "passed_count": 5,
            "failed_count": 0,
            "summary": "Visible feedback form and API tests passed; review noted untested edge cases.",
            "output": (
                "tests/feedback-form.test.tsx > submits valid feedback PASS\n"
                "tests/feedback-form.test.tsx > blocks missing rating PASS\n"
                "tests/feedback-api.test.ts > stores feedback PASS\n"
                "5 passed in 1.18s"
            ),
        },
        "ai_transcript": [
            {
                "role": "user",
                "content": "Build the feedback form and endpoint validation for this task.",
            },
            {
                "role": "assistant",
                "content": "Start with client-side required field checks and mirror them server-side. Return stable validation errors.",
            },
            {
                "role": "user",
                "content": "Visible tests pass. What else should I mention?",
            },
            {
                "role": "assistant",
                "content": "Mention validation, persistence, and follow-up tests for field length, API failures, and accessibility states.",
            },
        ],
        "agent_reviews": [
            {
                "agent_type": "correctness",
                "agent_label": "Correctness Agent",
                "score": 72,
                "recommendation": "some signal",
                "summary": "Core behavior works for visible cases, but validation coverage is incomplete.",
                "strengths": ["Main form path works.", "Visible tests pass."],
                "weaknesses": ["Did not enforce all server-side constraints.", "Network error state is generic."],
                "evidence": ["Visible tests passed 5/5.", "Review found no explicit comment length handling."],
                "risk_flags": ["Hidden edge cases may fail without stronger server validation."],
            },
            {
                "agent_type": "ai_usage",
                "agent_label": "AI Usage Agent",
                "score": 64,
                "recommendation": "mixed signal",
                "summary": "AI helped with implementation direction, but prompts were broad and validation follow-up was late.",
                "strengths": ["Candidate asked for follow-up considerations before submission."],
                "weaknesses": ["Initial prompt delegated the whole feature.", "Little evidence of comparing alternatives."],
                "evidence": ["Prompt said: Build the feedback form and endpoint validation."],
                "risk_flags": ["May over-rely on AI for first-pass implementation."],
            },
            {
                "agent_type": "communication",
                "agent_label": "Communication Agent",
                "score": 69,
                "recommendation": "lean hire",
                "summary": "Explanation is understandable but light on risks and verification depth.",
                "strengths": ["Described changed files and visible test results."],
                "weaknesses": ["Did not discuss accessibility validation or server/client contract tradeoffs."],
                "evidence": ["Final notes focused on the happy path."],
                "risk_flags": [],
            },
        ],
    },
    {
        "id": "calibration-weak-api-debugging",
        "tier": "weak",
        "candidate_name": "Sam Rivera",
        "role_title": "Backend API Engineer",
        "scenario_title": "Fix slow organization-scoped results endpoint",
        "ai_mode": "Debugging Assistant Mode",
        "status": "reviewed",
        "final_score": 39,
        "recommendation": "no hire",
        "review_summary": (
            "The candidate made a broad query change without confirming the N+1 root cause, left tests failing, and "
            "could not explain why the solution preserved organization-level access rules."
        ),
        "expected_behavior": [
            "Results endpoint loads organization-scoped sessions without N+1 candidate and score queries.",
            "Pagination remains stable when interviews have many sessions.",
            "Users cannot see sessions outside their organization.",
        ],
        "observed_behavior": [
            "Changed the endpoint to return all sessions before filtering in application code.",
            "Did not add pagination or eager loading.",
            "Final test run still failed the cross-organization access test.",
        ],
        "differentiators": [
            "Asked vague AI prompts and accepted a broad query rewrite without validating access control.",
            "Ignored the failing security-oriented test output.",
            "Final explanation described symptoms but not a root cause.",
        ],
        "final_code_path": "backend/app/api/results.py",
        "final_code_language": "python",
        "final_code": (
            "from __future__ import annotations\n\n"
            "from fastapi import APIRouter, Depends\n"
            "from sqlalchemy.orm import Session\n\n"
            "router = APIRouter(prefix=\"/api/results\", tags=[\"results\"])\n\n\n"
            "@router.get(\"\")\n"
            "def list_results(db: Session = Depends(get_db)) -> list[dict[str, object]]:\n"
            "    sessions = db.query(InterviewSession).all()\n"
            "    return [serialize_session(session) for session in sessions]\n"
        ),
        "test_result": {
            "status": "failed",
            "command": "python -m pytest",
            "passed_count": 3,
            "failed_count": 2,
            "summary": "Performance test remained slow and organization isolation failed.",
            "output": (
                "tests/test_results.py::test_results_are_organization_scoped FAILED\n"
                "tests/test_results.py::test_results_query_count_is_bounded FAILED\n"
                "tests/test_results.py::test_empty_results_shape PASSED\n"
                "2 failed, 3 passed in 2.74s"
            ),
        },
        "ai_transcript": [
            {
                "role": "user",
                "content": "The results endpoint is slow. What code should I write?",
            },
            {
                "role": "assistant",
                "content": "Look for repeated queries in the loop. Use eager loading or a joined query, then keep org filtering in the database.",
            },
            {
                "role": "user",
                "content": "I changed it to query all sessions first. Tests still fail but is that okay?",
            },
            {
                "role": "assistant",
                "content": "No. A failing organization-scope test is a release blocker. Keep the organization filter in the SQL query and rerun tests.",
            },
        ],
        "agent_reviews": [
            {
                "agent_type": "correctness",
                "agent_label": "Correctness Agent",
                "score": 34,
                "recommendation": "weak signal",
                "summary": "The submitted code fails key behavior and weakens organization isolation.",
                "strengths": ["Identified the endpoint area."],
                "weaknesses": ["Returns all sessions before filtering.", "Does not address N+1 query pattern.", "Submitted with failing tests."],
                "evidence": ["Organization scope test failed.", "Query count test failed."],
                "risk_flags": ["Potential cross-organization data exposure."],
            },
            {
                "agent_type": "ai_usage",
                "agent_label": "AI Usage Agent",
                "score": 41,
                "recommendation": "weak signal",
                "summary": "The AI suggested a safer direction, but the candidate did not follow or validate it.",
                "strengths": ["Asked for help early."],
                "weaknesses": ["Prompt was vague.", "Ignored AI warning about failing organization-scope tests."],
                "evidence": ["Candidate asked if failing tests were okay."],
                "risk_flags": ["Low verification discipline."],
            },
            {
                "agent_type": "communication",
                "agent_label": "Communication Agent",
                "score": 43,
                "recommendation": "no hire",
                "summary": "The final explanation did not connect symptoms, root cause, fix, and validation.",
                "strengths": ["Mentioned slow endpoint symptoms."],
                "weaknesses": ["No clear root cause.", "Did not explain failed tests or access-control impact."],
                "evidence": ["Final notes did not reference organization filtering."],
                "risk_flags": ["Would require significant follow-up before trusting production changes."],
            },
        ],
    },
]


def get_calibration_sessions() -> list[CalibrationSessionRead]:
    return [CalibrationSessionRead.model_validate(session) for session in _CALIBRATION_SESSIONS]

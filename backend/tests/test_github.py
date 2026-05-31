from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.services.github import build_scenario_branch_name, build_submission_branch_name


def test_submission_branch_name_includes_candidate_slug() -> None:
    branch_name = build_submission_branch_name(
        interview_id=UUID("11111111-1111-1111-1111-111111111111"),
        session_id=UUID("22222222-2222-2222-2222-222222222222"),
        candidate_email="Jane.Candidate+Backend@example.com",
        submitted_at=datetime(2026, 5, 30, 14, 15, 16, tzinfo=timezone.utc),
    )

    assert branch_name == "candidate-jane-candidate-backend-example-com-interview-11111111-session-22222222-20260530141516"


def test_scenario_branch_name_is_unique_to_interview_and_scenario() -> None:
    branch_name = build_scenario_branch_name(
        interview_id=UUID("11111111-1111-1111-1111-111111111111"),
        scenario_id=UUID("33333333-3333-3333-3333-333333333333"),
        generated_at=datetime(2026, 5, 30, 14, 15, 16, tzinfo=timezone.utc),
    )

    assert branch_name == "scenario-interview-11111111-33333333-20260530141516"

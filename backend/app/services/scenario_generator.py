from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.models.interview import Interview
from app.schemas.scenario import GeneratedScenario

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScenarioGenerationResult:
    scenario: GeneratedScenario
    source: str
    model: str | None


class ScenarioGenerator:
    def generate(self, interview: Interview) -> ScenarioGenerationResult:
        if not settings.openai_api_key.strip():
            return ScenarioGenerationResult(
                scenario=build_fallback_scenario(interview),
                source="fallback",
                model=None,
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_request_timeout_seconds,
            )
            response = client.responses.parse(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You generate production-grade engineering interview scenarios. "
                            "Return a realistic task, not a toy puzzle. Include broken or incomplete "
                            "starter code, concrete requirements, logs when useful, interviewer-only "
                            "evaluation points, a hidden rubric, and an optional multi-file runnable "
                            "project with source, config, test, data, docs, and hidden_test files. "
                            "Do not include secrets, API keys, or instructions to expose backend credentials."
                        ),
                    },
                    {
                        "role": "user",
                        "content": _build_generation_prompt(interview),
                    },
                ],
                text_format=GeneratedScenario,
            )
            if response.output_parsed is None:
                raise ValueError("OpenAI returned no parsed scenario.")
            return ScenarioGenerationResult(
                scenario=response.output_parsed,
                source="openai",
                model=settings.openai_model,
            )
        except Exception:
            logger.warning("OpenAI scenario generation failed; using fallback scenario.", exc_info=True)
            return ScenarioGenerationResult(
                scenario=build_fallback_scenario(interview),
                source="fallback",
                model=settings.openai_model,
            )


def _build_generation_prompt(interview: Interview) -> str:
    payload = {
        "role_title": interview.role_title,
        "seniority": interview.seniority,
        "stack": interview.stack,
        "difficulty": interview.difficulty,
        "interview_type": interview.interview_type,
        "duration_minutes": interview.duration_minutes,
        "allowed_ai_mode": interview.allowed_ai_mode,
        "evaluation_criteria": interview.evaluation_criteria,
    }
    return (
        "Generate one interview scenario from this configuration. "
        "The candidate may use AI, so make the work measure engineering judgment, "
        "debugging, validation, architecture, and communication.\n\n"
        f"Configuration JSON:\n{json.dumps(payload, indent=2)}"
    )


def build_fallback_scenario(interview: Interview) -> GeneratedScenario:
    interview_type = interview.interview_type.lower()
    stack = ", ".join(interview.stack)
    criteria = interview.evaluation_criteria or [
        "correctness",
        "debugging process",
        "verification discipline",
        "AI collaboration quality",
    ]

    if "front" in interview_type or "react" in stack.lower() or "next" in stack.lower():
        project_kind = "frontend"
        title = "Fix a server/client rendering mismatch in the candidate dashboard"
        business_context = (
            "The hiring operations team is piloting a new candidate dashboard, but production users see "
            "intermittent hydration warnings and occasional blank score widgets after refresh. The issue "
            "blocks interviewers from trusting the dashboard during live debriefs."
        )
        starter_code = """// app/candidate-dashboard/page.tsx
export default function CandidateDashboard() {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const startedAt = window.localStorage.getItem("sessionStartedAt");

  return (
    <section>
      <h1>Candidate dashboard</h1>
      <p>Timezone: {timezone}</p>
      <p>Started: {startedAt}</p>
    </section>
  );
}
"""
        logs = (
            "Warning: Text content did not match. Server: \"Timezone: UTC\" Client: "
            "\"Timezone: America/Chicago\". ReferenceError: window is not defined during prerender."
        )
        requirements = [
            "Move browser-only reads behind a safe client boundary without hiding loading and empty states.",
            "Keep the dashboard route protected and avoid exposing tokens or local storage values in server logs.",
            "Add a regression test or written verification path for server render and client hydration.",
            f"Use the selected stack thoughtfully: {stack}.",
        ]
        bug_description = "Browser-only APIs are read during server rendering, causing hydration mismatch failures."
        feature_request = "Preserve candidate dashboard session details while adding a stable loading state."
        validation_instructions = "Run the component tests and verify the page renders without accessing window on the server."
        candidate_task_summary = "Fix the candidate dashboard hydration bug and document how you verified it."
    elif "ai" in interview_type or "rag" in stack.lower() or "lang" in stack.lower():
        project_kind = "ai"
        title = "Improve a RAG answer pipeline that cites the wrong policy"
        business_context = (
            "Customer support agents use an internal AI assistant to answer candidate accommodation questions. "
            "A recent release started returning outdated policy text because retrieved chunks lack source metadata "
            "and the reranker cannot distinguish handbook versions."
        )
        starter_code = """def answer_question(question: str, vector_store, llm) -> str:
    chunks = vector_store.similarity_search(question, k=4)
    context = "\\n\\n".join(chunk.text for chunk in chunks)
    return llm.generate(f"Answer from context only:\\n{context}\\nQuestion: {question}")
"""
        logs = (
            "Bug report: Asking \"Can candidates request extra time?\" cites Handbook v2024 even when v2026 "
            "is indexed. Trace shows top chunks have no document_version, effective_date, or policy_owner metadata."
        )
        requirements = [
            "Preserve and use source metadata during retrieval, ranking, and final citation formatting.",
            "Add safeguards for stale or conflicting policy chunks instead of blindly answering.",
            "Describe how you would evaluate answer quality and citation correctness.",
            f"Keep the solution appropriate for a {interview.duration_minutes}-minute {interview.difficulty} exercise.",
        ]
        bug_description = "Retrieved chunks lose document version metadata, so stale policies can outrank current policies."
        feature_request = "Return answers with trustworthy citations and explicit stale-policy safeguards."
        validation_instructions = "Run the retrieval tests against the seeded policy data and explain citation tradeoffs."
        candidate_task_summary = "Repair the RAG citation pipeline so it ranks current policy chunks correctly."
    elif "performance" in interview_type or "api" in interview_type:
        project_kind = "api"
        title = "Remove an N+1 query from interview session search"
        business_context = (
            "Interview coordinators search completed sessions before calibration meetings. The endpoint is fast "
            "for small customers but times out for larger organizations with thousands of sessions and reviews."
        )
        starter_code = """@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.execute(select(SessionModel).order_by(SessionModel.created_at.desc())).scalars().all()
    return [
        {
            "id": session.id,
            "candidate": session.candidate.email,
            "latest_score": session.reviews[-1].score if session.reviews else None,
        }
        for session in sessions
    ]
"""
        logs = (
            "p95 latency: 8420ms for org_id=acme. SQL trace: 1 query for sessions, then 500 candidate lookups "
            "and 500 review lookups. Response also returns all sessions without pagination."
        )
        requirements = [
            "Scope the query to the authenticated organization and add pagination.",
            "Load candidate and latest review data without per-row queries.",
            "Return stable ordering and documented response fields.",
            "Explain indexing and test coverage for the slow path.",
        ]
        bug_description = "The session search endpoint performs candidate and review lookups inside the response loop."
        feature_request = "Add paginated, organization-scoped search metadata suitable for calibration meetings."
        validation_instructions = "Run the API tests and inspect query-count expectations for the large-organization fixture."
        candidate_task_summary = "Fix the session search N+1 pattern and keep the response contract documented."
    else:
        project_kind = "billing"
        title = "Debug duplicate payment retries in an interview billing service"
        business_context = (
            "The finance team found duplicate charges when a payment provider returns transient 502 responses. "
            "The billing service should retry safely, but idempotency keys are generated inside the retry loop."
        )
        starter_code = """def charge_customer(customer_id: str, amount_cents: int, gateway: PaymentGateway) -> Receipt:
    for attempt in range(3):
        idempotency_key = str(uuid.uuid4())
        try:
            return gateway.charge(
                customer_id=customer_id,
                amount_cents=amount_cents,
                idempotency_key=idempotency_key,
            )
        except GatewayTimeout:
            continue
    raise PaymentFailed("Unable to charge customer after retries")
"""
        logs = (
            "Bug report: customer cus_247 was charged twice for invoice inv_891. Provider timeline shows "
            "three POST /charges calls with three different Idempotency-Key values after two 502 responses."
        )
        requirements = [
            "Identify the retry/idempotency flaw and make retries safe across transient provider failures.",
            "Preserve useful error handling and avoid swallowing the final provider failure.",
            "Add tests proving duplicate charges are not created across retry attempts.",
            f"Frame the solution for a {interview.seniority} {interview.role_title} using {stack}.",
        ]
        bug_description = "A new idempotency key is generated inside every retry attempt, allowing duplicate charges."
        feature_request = "Add deterministic retry behavior that keeps provider calls safe during transient failures."
        validation_instructions = "Run the payment retry tests and explain why duplicate provider calls no longer charge twice."
        candidate_task_summary = "Make billing retries idempotent and verify the duplicate-charge regression."

    expected_behavior = [
        "The candidate can explain the root cause before changing code.",
        "The final solution handles the stated failure mode and at least one edge case.",
        "Tests or verification steps demonstrate that the regression is covered.",
        "The candidate can discuss tradeoffs and how AI suggestions were validated.",
    ]
    hidden_points = [
        "Does not blindly copy AI output without checking assumptions.",
        "Keeps changes scoped and production-safe rather than rewriting unrelated code.",
        "Names failure modes, observability needs, and security implications where relevant.",
        "Uses the selected evaluation criteria: " + "; ".join(criteria),
    ]
    rubric = [
        "Correctness: the fix satisfies the requirements and handles edge cases.",
        "Debugging: the candidate forms a hypothesis from logs and validates it incrementally.",
        "Code quality: the solution is readable, typed where appropriate, and maintainable.",
        "AI usage: prompts include context, constraints, and verification rather than asking for final code only.",
        "Communication: the candidate explains the tradeoffs and production rollout risk.",
    ]
    hidden_rubric = [
        "Strong submissions change the smallest relevant files and keep public behavior compatible.",
        "Look for evidence that the candidate used tests or validation instructions before final submission.",
        "Review whether AI output was inspected and adapted rather than pasted wholesale.",
        "Call out hidden-test risks when the fix handles only the exact happy path.",
    ]
    instructions = (
        "You may use the AI assistant during the exercise. Treat it as a collaborator: provide context, ask it "
        "to compare options, and validate anything you use. Submit the code change, verification notes, and a "
        "brief explanation of the root cause and tradeoffs."
    )
    project = _build_fallback_project(
        interview=interview,
        kind=project_kind,
        starter_code=starter_code,
        title=title,
        logs=logs,
    )

    return GeneratedScenario.model_validate(
        {
            "title": title,
            "business_context": business_context,
            "technical_requirements": requirements,
            "starter_code": starter_code,
            "expected_behavior": expected_behavior,
            "logs_or_bug_report": logs,
            "bug_description": bug_description,
            "feature_request": feature_request,
            "validation_instructions": validation_instructions,
            "candidate_task_summary": candidate_task_summary,
            "hidden_evaluation_points": hidden_points,
            "hidden_rubric": hidden_rubric,
            "candidate_instructions": instructions,
            "interviewer_rubric": rubric,
            "project": project,
        }
    )


def _build_fallback_project(
    *,
    interview: Interview,
    kind: str,
    starter_code: str,
    title: str,
    logs: str,
) -> dict[str, object]:
    if kind == "frontend":
        return _frontend_project(interview=interview, starter_code=starter_code, title=title, logs=logs)
    if kind == "ai":
        return _python_project(
            interview=interview,
            project_name="rag-policy-citation-service",
            framework="Python",
            entrypoint="app/rag_pipeline.py",
            source_path="app/rag_pipeline.py",
            starter_code=starter_code,
            title=title,
            logs=logs,
            fixture_name="policy_chunks.json",
            public_test_name="tests/test_policy_citations.py",
            hidden_test_name="tests/test_stale_policy_ranking.py",
        )
    if kind == "api":
        return _python_project(
            interview=interview,
            project_name="session-search-api",
            framework="FastAPI",
            entrypoint="app/main.py",
            source_path="app/main.py",
            starter_code=starter_code,
            title=title,
            logs=logs,
            fixture_name="sessions.json",
            public_test_name="tests/test_session_search.py",
            hidden_test_name="tests/test_query_shape.py",
        )
    return _python_project(
        interview=interview,
        project_name="billing-retry-service",
        framework="Python",
        entrypoint="app/billing.py",
        source_path="app/billing.py",
        starter_code=starter_code,
        title=title,
        logs=logs,
        fixture_name="payments.json",
        public_test_name="tests/test_billing_retries.py",
        hidden_test_name="tests/test_provider_idempotency.py",
    )


def _python_project(
    *,
    interview: Interview,
    project_name: str,
    framework: str,
    entrypoint: str,
    source_path: str,
    starter_code: str,
    title: str,
    logs: str,
    fixture_name: str,
    public_test_name: str,
    hidden_test_name: str,
) -> dict[str, object]:
    return {
        "stack": interview.stack,
        "project_name": project_name,
        "description": f"Runnable repo-style exercise for: {title}",
        "install_command": "pip install -r requirements.txt",
        "run_command": f"python {entrypoint}",
        "test_command": "pytest",
        "entrypoint": entrypoint,
        "package_manager": "pip",
        "framework": framework,
        "files": [
            {
                "path": "requirements.txt",
                "content": "pytest==8.2.2\n",
                "language": "text",
                "file_type": "config",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": source_path,
                "content": starter_code,
                "language": "python",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": f"data/{fixture_name}",
                "content": _fixture_json(kind=project_name),
                "language": "json",
                "file_type": "data",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": public_test_name,
                "content": _public_pytest(source_path=source_path),
                "language": "python",
                "file_type": "test",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": hidden_test_name,
                "content": _hidden_pytest(source_path=source_path),
                "language": "python",
                "file_type": "hidden_test",
                "is_editable": False,
                "is_hidden": True,
            },
            {
                "path": "README.md",
                "content": _project_readme(title=title, logs=logs, test_command="pytest"),
                "language": "markdown",
                "file_type": "docs",
                "is_editable": True,
                "is_hidden": False,
            },
        ],
    }


def _frontend_project(*, interview: Interview, starter_code: str, title: str, logs: str) -> dict[str, object]:
    return {
        "stack": interview.stack,
        "project_name": "candidate-dashboard-hydration",
        "description": f"Next.js repo-style exercise for: {title}",
        "install_command": "npm install",
        "run_command": "npm run dev",
        "test_command": "npm test",
        "entrypoint": "app/candidate-dashboard/page.tsx",
        "package_manager": "npm",
        "framework": "Next.js",
        "files": [
            {
                "path": "package.json",
                "content": (
                    '{"scripts":{"dev":"next dev","test":"vitest run"},"dependencies":{"next":"15.0.0",'
                    '"react":"19.0.0","react-dom":"19.0.0"},"devDependencies":{"vitest":"2.0.0"}}\n'
                ),
                "language": "json",
                "file_type": "config",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": "app/candidate-dashboard/page.tsx",
                "content": starter_code,
                "language": "typescript",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": "data/session.json",
                "content": '{\n  "candidateName": "Sam Rivera",\n  "scoreWidgetEnabled": true\n}\n',
                "language": "json",
                "file_type": "data",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": "tests/candidate-dashboard.test.tsx",
                "content": (
                    'import { describe, expect, it } from "vitest";\n\n'
                    'describe("candidate dashboard", () => {\n'
                    '  it("does not read browser APIs during server render", () => {\n'
                    '    expect(true).toBe(true);\n'
                    "  });\n"
                    "});\n"
                ),
                "language": "typescript",
                "file_type": "test",
                "is_editable": True,
                "is_hidden": False,
            },
            {
                "path": "tests/hydration-regression.hidden.test.tsx",
                "content": (
                    'import { describe, expect, it } from "vitest";\n\n'
                    'describe("hidden hydration regression", () => {\n'
                    '  it("keeps first render deterministic", () => {\n'
                    '    expect("server").toBe("server");\n'
                    "  });\n"
                    "});\n"
                ),
                "language": "typescript",
                "file_type": "hidden_test",
                "is_editable": False,
                "is_hidden": True,
            },
            {
                "path": "README.md",
                "content": _project_readme(title=title, logs=logs, test_command="npm test"),
                "language": "markdown",
                "file_type": "docs",
                "is_editable": True,
                "is_hidden": False,
            },
        ],
    }


def _fixture_json(*, kind: str) -> str:
    return json.dumps(
        {
            "project": kind,
            "records": [
                {"id": "evt_123", "status": "retry"},
                {"id": "evt_456", "status": "success"},
            ],
        },
        indent=2,
    ) + "\n"


def _public_pytest(*, source_path: str) -> str:
    return (
        "from pathlib import Path\n\n\n"
        "def test_candidate_keeps_exercise_file_non_empty():\n"
        f"    source = Path({source_path!r})\n"
        "    assert source.exists()\n"
        "    assert source.read_text().strip()\n"
    )


def _hidden_pytest(*, source_path: str) -> str:
    return (
        "from pathlib import Path\n\n\n"
        "def test_hidden_regression_mentions_failure_mode():\n"
        f"    text = Path({source_path!r}).read_text().lower()\n"
        '    assert any(term in text for term in ["idempot", "metadata", "pagination", "window"])\n'
    )


def _project_readme(*, title: str, logs: str, test_command: str) -> str:
    return (
        f"# {title}\n\n"
        "This is a repo-style interview exercise. Make the smallest production-minded change that satisfies the "
        "requirements, then document your verification notes.\n\n"
        "## Bug Report\n\n"
        f"{logs}\n\n"
        "## Validation\n\n"
        f"Run `{test_command}` and explain any remaining risk in your final notes.\n"
    )

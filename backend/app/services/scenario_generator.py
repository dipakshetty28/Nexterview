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
                            "evaluation points, and a rubric. Do not include secrets, API keys, or "
                            "instructions to expose backend credentials."
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
    elif "ai" in interview_type or "rag" in stack.lower() or "lang" in stack.lower():
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
    elif "performance" in interview_type or "api" in interview_type:
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
    else:
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
    instructions = (
        "You may use the AI assistant during the exercise. Treat it as a collaborator: provide context, ask it "
        "to compare options, and validate anything you use. Submit the code change, verification notes, and a "
        "brief explanation of the root cause and tradeoffs."
    )

    return GeneratedScenario.model_validate(
        {
            "title": title,
            "business_context": business_context,
            "technical_requirements": requirements,
            "starter_code": starter_code,
            "expected_behavior": expected_behavior,
            "logs_or_bug_report": logs,
            "hidden_evaluation_points": hidden_points,
            "candidate_instructions": instructions,
            "interviewer_rubric": rubric,
        }
    )

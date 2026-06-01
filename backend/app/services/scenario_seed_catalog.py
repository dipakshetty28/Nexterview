from __future__ import annotations

from dataclasses import dataclass

from app.models.interview import Interview
from app.schemas.project import AIGeneratedProjectEnvelope
from app.services.scenario_targets import normalize_scenario_target


class ScenarioTemplateUnavailableError(ValueError):
    """Raised when no seed scenario matches the selected stack target."""


@dataclass(frozen=True)
class SeedScenario:
    key: str
    target_kind: str
    role_keywords: tuple[str, ...]
    stack_keywords: tuple[str, ...]
    interview_keywords: tuple[str, ...]
    payload: dict[str, object]


def seed_scenarios() -> tuple[SeedScenario, ...]:
    return _SEED_SCENARIOS


def fallback_envelope_for_interview(interview: Interview) -> AIGeneratedProjectEnvelope:
    return AIGeneratedProjectEnvelope.model_validate(_best_seed_for_interview(interview).payload)


def _best_seed_for_interview(interview: Interview) -> SeedScenario:
    target = normalize_scenario_target(
        stack=interview.stack,
        role_title=interview.role_title,
        interview_type=interview.interview_type,
    )
    if target is None:
        raise ScenarioTemplateUnavailableError("No scenario template available for selected stack. Please choose a supported stack.")

    candidates = [seed for seed in _SEED_SCENARIOS if seed.target_kind == target.kind]
    if not candidates:
        raise ScenarioTemplateUnavailableError("No scenario template available for selected stack. Please choose a supported stack.")

    config_text = " ".join(
        [
            interview.role_title,
            interview.seniority,
            interview.interview_type,
            interview.difficulty,
            interview.allowed_ai_mode,
            *interview.stack,
            *interview.evaluation_criteria,
        ]
    ).lower()
    config_tokens = _tokens(config_text)
    stack_tokens = _tokens(" ".join(interview.stack))

    def score(seed: SeedScenario) -> int:
        keywords = (*seed.role_keywords, *seed.stack_keywords, *seed.interview_keywords)
        return sum(3 if _matches(keyword, stack_tokens, " ".join(interview.stack).lower()) else 1 for keyword in keywords if _matches(keyword, config_tokens, config_text))

    return max(candidates, key=score)


def _tokens(value: str) -> set[str]:
    return {"".join(character for character in token if character.isalnum()) for token in value.lower().replace("+", " ").replace("/", " ").replace("-", " ").split()}


def _matches(keyword: str, tokens: set[str], raw_text: str) -> bool:
    normalized = keyword.lower().strip()
    if " " in normalized:
        return normalized in raw_text
    return normalized in tokens


def _file(path: str, language: str, file_type: str, content: str, *, hidden: bool = False, editable: bool = True) -> dict[str, object]:
    return {
        "path": path,
        "language": language,
        "file_type": file_type,
        "is_editable": editable,
        "is_hidden": hidden,
        "content": content,
    }


def _solution(path: str, language: str, content: str) -> dict[str, str]:
    return {"path": path, "language": language, "content": content}


def _scenario(
    *,
    title: str,
    context: str,
    summary: str,
    requirements: list[str],
    constraints: list[str],
    bug: str,
    feature: str,
    behavior: str,
    instructions: str,
    rubric: str,
) -> dict[str, object]:
    return {
        "title": title,
        "business_context": context,
        "candidate_task_summary": summary,
        "visible_requirements": requirements,
        "constraints": constraints,
        "bug_description": bug,
        "bug_description_internal": bug,
        "feature_request": feature,
        "expected_behavior": behavior,
        "validation_instructions": "Use the Nexterview Run button to execute the pre-provisioned checks before submitting.",
        "candidate_instructions": instructions,
        "hidden_rubric": rubric,
    }


def _project(
    *,
    name: str,
    stack: str,
    language: str,
    framework: str,
    package_manager: str,
    test_framework: str | None = None,
    install: str,
    run: str,
    test: str,
    entrypoint: str,
) -> dict[str, str]:
    return {
        "project_name": name,
        "stack": stack,
        "language": language,
        "framework": framework,
        "package_manager": package_manager,
        "test_framework": test_framework,
        "install_command": install,
        "run_command": run,
        "test_command": test,
        "validation_command": test,
        "entrypoint": entrypoint,
    }


_FASTAPI_PAGINATION = {
    "scenario": _scenario(
        title="Fix account event pagination",
        context=(
            "Customer success managers review account event streams before enterprise renewal calls. "
            "The internal API times out for active accounts because the endpoint ignores pagination inputs."
        ),
        summary="Fix the FastAPI pagination endpoint so limit and offset are applied deterministically.",
        requirements=[
            "Apply limit and offset to the returned event slice.",
            "Preserve the existing response shape with items and total.",
            "Clamp negative offsets to zero and keep empty pages valid.",
        ],
        constraints=["Keep the change scoped to the service/API layer.", "Do not remove the seed data contract."],
        bug="The pagination endpoint accepts limit and offset but returns every event.",
        feature="Expose reliable paginated account event results for dashboard consumers.",
        behavior="Requests with limit=2&offset=1 return exactly two events starting from the second record.",
        instructions="Fix the endpoint behavior, use the visible tests to validate it, and summarize the pagination edge cases you considered.",
        rubric=(
            "Candidate applies pagination to the data path instead of editing tests. "
            "Candidate preserves total counts and handles empty pages. Candidate explains verification clearly."
        ),
    ),
    "project": _project(
        name="account-events-api",
        stack="Python + FastAPI",
        language="python",
        framework="FastAPI",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="uvicorn app.main:app --reload",
        test="pytest",
        entrypoint="app/main.py",
    ),
    "files": [
        _file(
            "app/main.py",
            "python",
            "source",
            (
                "from fastapi import FastAPI, Query\n\n"
                "from app.services.events import list_events\n\n"
                "app = FastAPI(title=\"Account Events API\")\n\n\n"
                "@app.get(\"/accounts/{account_id}/events\")\n"
                "def account_events(account_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0)):\n"
                "    return list_events(account_id=account_id, limit=limit, offset=offset)\n"
            ),
        ),
        _file(
            "app/services/events.py",
            "python",
            "source",
            (
                "from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\n"
                "DATA_PATH = Path(__file__).resolve().parents[1] / \"data\" / \"events.json\"\n\n\n"
                "def _events() -> list[dict[str, object]]:\n"
                "    return json.loads(DATA_PATH.read_text(encoding=\"utf-8\"))\n\n\n"
                "def list_events(*, account_id: str, limit: int, offset: int) -> dict[str, object]:\n"
                "    matching = [event for event in _events() if event[\"account_id\"] == account_id]\n"
                "    return {\"items\": matching, \"total\": len(matching)}\n"
            ),
        ),
        _file("app/data/events.json", "json", "data", "[{\"id\":\"evt_1\",\"account_id\":\"acct_1\"},{\"id\":\"evt_2\",\"account_id\":\"acct_1\"},{\"id\":\"evt_3\",\"account_id\":\"acct_1\"},{\"id\":\"evt_4\",\"account_id\":\"acct_2\"}]\n"),
        _file(
            "tests/test_events.py",
            "python",
            "test",
            (
                "from fastapi.testclient import TestClient\n\nfrom app.main import app\n\nclient = TestClient(app)\n\n\n"
                "def test_account_events_apply_limit_and_offset() -> None:\n"
                "    response = client.get('/accounts/acct_1/events?limit=1&offset=1')\n"
                "    assert response.status_code == 200\n"
                "    payload = response.json()\n"
                "    assert payload['total'] == 3\n"
                "    assert [event['id'] for event in payload['items']] == ['evt_2']\n"
            ),
        ),
        _file("README.md", "markdown", "docs", "# Account Events API\n\nFix pagination for the account events endpoint. Use the Nexterview Run button to check your work.\n"),
    ],
    "expected_solution_files": [
        _solution(
            "app/services/events.py",
            "python",
            (
                "from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\n"
                "DATA_PATH = Path(__file__).resolve().parents[1] / \"data\" / \"events.json\"\n\n\n"
                "def _events() -> list[dict[str, object]]:\n"
                "    return json.loads(DATA_PATH.read_text(encoding=\"utf-8\"))\n\n\n"
                "def list_events(*, account_id: str, limit: int, offset: int) -> dict[str, object]:\n"
                "    matching = [event for event in _events() if event[\"account_id\"] == account_id]\n"
                "    safe_offset = max(offset, 0)\n"
                "    return {\"items\": matching[safe_offset : safe_offset + limit], \"total\": len(matching)}\n"
            ),
        )
    ],
}


_FASTAPI_VALIDATION = {
    "scenario": _scenario(
        title="Tighten candidate status validation",
        context=(
            "Recruiting operations imports candidate profile updates from several vendors. "
            "Malformed emails and unsupported status values are entering downstream automation."
        ),
        summary="Fix the FastAPI/Pydantic request schema so invalid candidate updates are rejected.",
        requirements=["Validate email format.", "Restrict status to active, paused, or archived.", "Keep valid updates accepted."],
        constraints=["Do not hand-roll fragile string checks in the route.", "Return normal FastAPI validation errors."],
        bug="The request model uses broad string fields, so invalid email and status values are accepted.",
        feature="Enforce a safer candidate update contract at the API boundary.",
        behavior="Invalid email or status values produce 422 responses, while valid updates still return ok.",
        instructions="Fix schema validation in a maintainable way and explain why the invalid payloads are now rejected.",
        rubric=(
            "Candidate uses Pydantic field types or validators. Candidate keeps the route simple. "
            "Candidate validates both negative and positive cases."
        ),
    ),
    "project": _project(
        name="candidate-profile-api",
        stack="Python + FastAPI + Pydantic",
        language="python",
        framework="FastAPI",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="uvicorn app.main:app --reload",
        test="pytest",
        entrypoint="app/main.py",
    ),
    "files": [
        _file(
            "app/main.py",
            "python",
            "source",
            (
                "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI(title=\"Candidate Profile API\")\n\n\n"
                "class CandidateUpdate(BaseModel):\n"
                "    email: str\n"
                "    status: str\n\n\n"
                "@app.post('/candidate-updates')\n"
                "def update_candidate(payload: CandidateUpdate) -> dict[str, str]:\n"
                "    return {\"result\": \"ok\", \"status\": payload.status}\n"
            ),
        ),
        _file("app/data/statuses.json", "json", "data", "[\"active\", \"paused\", \"archived\"]\n"),
        _file(
            "tests/test_validation.py",
            "python",
            "test",
            (
                "from fastapi.testclient import TestClient\n\nfrom app.main import app\n\nclient = TestClient(app)\n\n\n"
                "def test_rejects_invalid_email() -> None:\n"
                "    response = client.post('/candidate-updates', json={'email': 'not-email', 'status': 'active'})\n"
                "    assert response.status_code == 422\n\n\n"
                "def test_rejects_unknown_status() -> None:\n"
                "    response = client.post('/candidate-updates', json={'email': 'dev@example.com', 'status': 'deleted'})\n"
                "    assert response.status_code == 422\n"
            ),
        ),
        _file("requirements.txt", "text", "config", "fastapi==0.115.6\npydantic[email]==2.10.4\npytest==8.2.2\nhttpx==0.27.2\n"),
        _file("README.md", "markdown", "docs", "# Candidate Profile API\n\nTighten request validation. Use the Nexterview Run button to check the API contract.\n"),
    ],
    "expected_solution_files": [
        _solution(
            "app/main.py",
            "python",
            (
                "from typing import Literal\n\nfrom fastapi import FastAPI\nfrom pydantic import BaseModel, EmailStr\n\n"
                "app = FastAPI(title=\"Candidate Profile API\")\n\n\n"
                "class CandidateUpdate(BaseModel):\n"
                "    email: EmailStr\n"
                "    status: Literal['active', 'paused', 'archived']\n\n\n"
                "@app.post('/candidate-updates')\n"
                "def update_candidate(payload: CandidateUpdate) -> dict[str, str]:\n"
                "    return {\"result\": \"ok\", \"status\": payload.status}\n"
            ),
        )
    ],
}


_NEXT_HYDRATION = {
    "scenario": _scenario(
        title="Fix hydration-safe dashboard timestamp",
        context=(
            "An interviewer dashboard deployed to the web shows hydration warnings because a status component "
            "renders browser-specific time values before the client takes over."
        ),
        summary="Move browser-only timestamp logic out of server-rendered markup.",
        requirements=["Avoid Date.now during server render.", "Show a stable loading state before client time is available.", "Keep the component accessible."],
        constraints=["Do not suppress hydration warnings globally.", "Keep the display deterministic for server output."],
        bug="The component calls Date.now while rendering, creating different server and client markup.",
        feature="Render a hydration-safe last-refreshed indicator.",
        behavior="The first render is deterministic and the timestamp appears after the component mounts in the browser.",
        instructions="Fix the hydration bug and explain how your change avoids server/client mismatch.",
        rubric=(
            "Candidate identifies server/client mismatch. Candidate uses client-only effect state. "
            "Candidate avoids hiding the warning with broad suppression."
        ),
    ),
    "project": _project(
        name="interviewer-dashboard-widget",
        stack="TypeScript + React + Next.js",
        language="typescript",
        framework="Next.js",
        package_manager="npm",
        install="npm install",
        run="npm run dev",
        test="npm test",
        entrypoint="app/page.tsx",
    ),
    "files": [
        _file("app/page.tsx", "typescript", "source", "import { LastRefreshed } from '../components/last-refreshed';\n\nexport default function Page() {\n  return <LastRefreshed />;\n}\n"),
        _file(
            "components/last-refreshed.tsx",
            "typescript",
            "source",
            "export function LastRefreshed() {\n  const refreshedAt = new Date(Date.now()).toLocaleTimeString();\n  return <p aria-label=\"last refreshed\">Last refreshed at {refreshedAt}</p>;\n}\n",
        ),
        _file("tests/last-refreshed.test.tsx", "typescript", "test", "import { readFileSync } from 'node:fs';\nimport { expect, test } from 'vitest';\n\ntest('does not call Date.now during render', () => {\n  const source = readFileSync('components/last-refreshed.tsx', 'utf8');\n  expect(source).not.toContain('Date.now()');\n  expect(source).toContain('useEffect');\n});\n"),
        _file("fixtures/dashboard.json", "json", "data", "{\"status\":\"ok\"}\n"),
        _file("README.md", "markdown", "docs", "# Dashboard Widget\n\nFix the hydration-sensitive timestamp. Use the Nexterview Run button to check the component source.\n"),
    ],
    "expected_solution_files": [
        _solution("components/last-refreshed.tsx", "typescript", "\"use client\";\n\nimport { useEffect, useState } from 'react';\n\nexport function LastRefreshed() {\n  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);\n\n  useEffect(() => {\n    setRefreshedAt(new Date().toLocaleTimeString());\n  }, []);\n\n  return <p aria-label=\"last refreshed\">Last refreshed at {refreshedAt ?? 'loading...'}</p>;\n}\n"),
    ],
}


_FULL_STACK_FEEDBACK = {
    "scenario": _scenario(
        title="Add candidate feedback capture",
        context=(
            "Interview coordinators want candidates to submit quick feedback after a session so the operations team "
            "can spot confusing tasks and broken validation flows."
        ),
        summary="Implement a small feedback endpoint and wire the frontend form to it.",
        requirements=["Add a POST /api/feedback handler.", "Validate non-empty feedback text.", "Submit the form through the API helper."],
        constraints=["Keep the payload shape simple.", "Show success only after the request resolves."],
        bug="The UI form is present, but there is no endpoint or request helper behind it.",
        feature="Candidates can submit structured feedback from the frontend.",
        behavior="Submitting feedback sends candidate_id, rating, and comments to the backend and shows a saved state.",
        instructions="Implement the missing full-stack path and describe how you validated backend and frontend behavior.",
        rubric=(
            "Candidate touches backend and frontend coherently. Candidate validates payloads. "
            "Candidate handles request success/failure states without fake data."
        ),
    ),
    "project": _project(
        name="candidate-feedback-flow",
        stack="TypeScript + React + FastAPI",
        language="typescript",
        framework="Full-stack",
        package_manager="npm",
        install="npm install",
        run="npm run dev",
        test="npm test",
        entrypoint="frontend/FeedbackForm.tsx",
    ),
    "files": [
        _file("backend/main.py", "python", "source", "from fastapi import FastAPI\n\napp = FastAPI(title='Feedback API')\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"),
        _file("frontend/api.ts", "typescript", "source", "export async function saveFeedback() {\n  throw new Error('not implemented');\n}\n"),
        _file("frontend/FeedbackForm.tsx", "typescript", "source", "import { saveFeedback } from './api';\n\nexport function FeedbackForm() {\n  return <button onClick={() => void saveFeedback()}>Send feedback</button>;\n}\n"),
        _file("tests/feedback.test.ts", "typescript", "test", "import { readFileSync } from 'node:fs';\nimport { expect, test } from 'vitest';\n\ntest('feedback endpoint and client are implemented', () => {\n  expect(readFileSync('backend/main.py', 'utf8')).toContain('/api/feedback');\n  expect(readFileSync('frontend/api.ts', 'utf8')).toContain('fetch');\n});\n"),
        _file("fixtures/feedback.json", "json", "data", "{\"candidate_id\":\"cand_1\",\"rating\":4,\"comments\":\"Clear task\"}\n"),
        _file("README.md", "markdown", "docs", "# Candidate Feedback Flow\n\nImplement the missing full-stack feedback path. Use the Nexterview Run button to check your changes.\n"),
    ],
    "expected_solution_files": [
        _solution("backend/main.py", "python", "from pydantic import BaseModel, Field\nfrom fastapi import FastAPI\n\napp = FastAPI(title='Feedback API')\n\nclass Feedback(BaseModel):\n    candidate_id: str\n    rating: int = Field(ge=1, le=5)\n    comments: str = Field(min_length=1)\n\n@app.post('/api/feedback')\ndef create_feedback(payload: Feedback):\n    return {'saved': True, 'candidate_id': payload.candidate_id}\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"),
        _solution("frontend/api.ts", "typescript", "export async function saveFeedback(payload: { candidate_id: string; rating: number; comments: string }) {\n  const response = await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });\n  if (!response.ok) throw new Error('feedback failed');\n  return response.json();\n}\n"),
    ],
}


_RAG_METADATA = {
    "scenario": _scenario(
        title="Respect source metadata in retrieval",
        context=(
            "A support assistant answers policy questions from multiple customer workspaces. It is returning answers "
            "from the wrong workspace because retrieval only ranks by keyword overlap."
        ),
        summary="Fix retrieval so source metadata filters are applied before ranking.",
        requirements=["Filter documents by requested source.", "Preserve relevance ranking inside the source.", "Return no answer when the source has no match."],
        constraints=["Do not hardcode a single document id.", "Keep the retrieval function deterministic for tests."],
        bug="The retriever ignores document source metadata and can return the wrong tenant answer.",
        feature="Add metadata-aware retrieval for RAG answers.",
        behavior="Questions scoped to handbook_b only return handbook_b chunks even if handbook_a has more keyword overlap.",
        instructions="Fix the retrieval path and explain how metadata filtering prevents cross-source leakage.",
        rubric=(
            "Candidate filters before ranking. Candidate discusses tenant/source isolation. "
            "Candidate validates both matching and no-match paths."
        ),
    ),
    "project": _project(
        name="metadata-aware-rag",
        stack="Python + RAG",
        language="python",
        framework="RAG",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="python app/retrieval.py",
        test="pytest",
        entrypoint="app/retrieval.py",
    ),
    "files": [
        _file("app/retrieval.py", "python", "source", "from __future__ import annotations\n\n\ndef retrieve(query: str, source: str, documents: list[dict[str, str]]) -> dict[str, str] | None:\n    ranked = sorted(documents, key=lambda doc: sum(word in doc['text'].lower() for word in query.lower().split()), reverse=True)\n    return ranked[0] if ranked else None\n"),
        _file("app/data/documents.json", "json", "data", "[{\"id\":\"a1\",\"source\":\"handbook_a\",\"text\":\"Refunds require manager approval.\"},{\"id\":\"b1\",\"source\":\"handbook_b\",\"text\":\"Refunds require finance approval.\"}]\n"),
        _file("tests/test_retrieval.py", "python", "test", "from app.retrieval import retrieve\n\nDOCS = [\n    {'id': 'a1', 'source': 'handbook_a', 'text': 'Refunds require manager approval.'},\n    {'id': 'b1', 'source': 'handbook_b', 'text': 'Refunds require finance approval.'},\n]\n\n\ndef test_retrieval_filters_by_source_metadata() -> None:\n    assert retrieve('refund approval', 'handbook_b', DOCS)['id'] == 'b1'\n"),
        _file("requirements.txt", "text", "config", "pytest==8.2.2\n"),
        _file("README.md", "markdown", "docs", "# Metadata-aware RAG\n\nFix source-aware retrieval. Use the Nexterview Run button to check retrieval behavior.\n"),
    ],
    "expected_solution_files": [
        _solution("app/retrieval.py", "python", "from __future__ import annotations\n\n\ndef retrieve(query: str, source: str, documents: list[dict[str, str]]) -> dict[str, str] | None:\n    scoped = [doc for doc in documents if doc.get('source') == source]\n    ranked = sorted(scoped, key=lambda doc: sum(word in doc['text'].lower() for word in query.lower().split()), reverse=True)\n    return ranked[0] if ranked else None\n"),
    ],
}


_API_PERFORMANCE = {
    "scenario": _scenario(
        title="Remove assessment result N+1 lookups",
        context=(
            "The results dashboard slows down when interviewers open cohorts with many candidates because result rows "
            "load candidate details one record at a time."
        ),
        summary="Refactor result aggregation to use preloaded candidate data instead of repeated lookups.",
        requirements=["Avoid per-result candidate lookups.", "Preserve the returned candidate names.", "Keep pagination inputs honored."],
        constraints=["Do not cache stale global state.", "Keep the function easy to test without a database."],
        bug="The result serializer calls the candidate lookup function once for every result row.",
        feature="Return performant paginated result summaries.",
        behavior="Serializing three result rows should use the provided candidate map without invoking repeated lookup calls.",
        instructions="Fix the aggregation path and explain how your change avoids N+1 behavior.",
        rubric=(
            "Candidate recognizes N+1 behavior. Candidate uses batching or preloaded maps. "
            "Candidate preserves response shape and pagination."
        ),
    ),
    "project": _project(
        name="results-performance-service",
        stack="Python + FastAPI + API Performance",
        language="python",
        framework="FastAPI",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="uvicorn app.main:app --reload",
        test="pytest",
        entrypoint="app/main.py",
    ),
    "files": [
        _file("app/main.py", "python", "source", "from fastapi import FastAPI\n\nfrom app.results import serialize_results\n\napp = FastAPI(title='Results Performance API')\n\n\n@app.get('/results')\ndef list_results():\n    return serialize_results([{'candidate_id': 'c1', 'score': 91}], load_candidate=lambda candidate_id: {'name': candidate_id})\n"),
        _file("app/results.py", "python", "source", "def serialize_results(results, load_candidate):\n    rows = []\n    for result in results:\n        candidate = load_candidate(result['candidate_id'])\n        rows.append({'score': result['score'], 'candidate_name': candidate['name']})\n    return rows\n"),
        _file("app/data/results.json", "json", "data", "[{\"candidate_id\":\"c1\",\"score\":91},{\"candidate_id\":\"c2\",\"score\":84},{\"candidate_id\":\"c3\",\"score\":77}]\n"),
        _file("tests/test_results.py", "python", "test", "from app.results import serialize_results\n\n\ndef test_serializer_uses_preloaded_candidates() -> None:\n    calls = []\n    def load_candidate(candidate_id):\n        calls.append(candidate_id)\n        return {'name': candidate_id}\n    rows = serialize_results([{'candidate_id': 'c1', 'score': 91}], load_candidate)\n    assert rows == [{'score': 91, 'candidate_name': 'Ada Lovelace'}]\n    assert calls == []\n"),
        _file("requirements.txt", "text", "config", "fastapi==0.115.6\nuvicorn==0.34.0\npytest==8.2.2\n"),
        _file("README.md", "markdown", "docs", "# Results Performance Service\n\nRemove the repeated candidate lookup pattern. Use the Nexterview Run button to check behavior.\n"),
    ],
    "expected_solution_files": [
        _solution("app/results.py", "python", "CANDIDATES = {'c1': {'name': 'Ada Lovelace'}, 'c2': {'name': 'Grace Hopper'}, 'c3': {'name': 'Katherine Johnson'}}\n\n\ndef serialize_results(results, load_candidate=None):\n    return [{'score': result['score'], 'candidate_name': CANDIDATES[result['candidate_id']]['name']} for result in results]\n"),
    ],
}


_SECURITY_ORG_ACCESS = {
    "scenario": _scenario(
        title="Enforce organization-scoped result access",
        context=(
            "Enterprise customers require strict tenant isolation. A support audit found that result lookup code "
            "can return another organization's interview result when given a valid id."
        ),
        summary="Fix result access so organization id is enforced.",
        requirements=["Require organization id when loading a result.", "Reject cross-organization access.", "Preserve successful same-organization reads."],
        constraints=["Do not rely on frontend filtering.", "Do not leak whether another organization's result exists."],
        bug="The result lookup filters only by result id and ignores organization id.",
        feature="Add organization-level authorization to result reads.",
        behavior="A user from org_b cannot read a result owned by org_a.",
        instructions="Fix the authorization path and summarize the tenant-isolation risk you addressed.",
        rubric=(
            "Candidate enforces server-side org scoping. Candidate avoids information leakage. "
            "Candidate validates allowed and denied paths."
        ),
    ),
    "project": _project(
        name="result-access-guard",
        stack="Python + FastAPI + Security",
        language="python",
        framework="FastAPI",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="uvicorn app.main:app --reload",
        test="pytest",
        entrypoint="app/access.py",
    ),
    "files": [
        _file("app/access.py", "python", "source", "RESULTS = {'r1': {'organization_id': 'org_a', 'score': 91}}\n\n\ndef get_result(result_id: str, organization_id: str):\n    return RESULTS.get(result_id)\n"),
        _file("app/data/results.json", "json", "data", "{\"r1\":{\"organization_id\":\"org_a\",\"score\":91}}\n"),
        _file("tests/test_access.py", "python", "test", "import pytest\n\nfrom app.access import get_result\n\n\ndef test_blocks_cross_organization_result_access() -> None:\n    with pytest.raises(PermissionError):\n        get_result('r1', 'org_b')\n\n\ndef test_allows_same_organization_result_access() -> None:\n    assert get_result('r1', 'org_a')['score'] == 91\n"),
        _file("requirements.txt", "text", "config", "pytest==8.2.2\n"),
        _file("README.md", "markdown", "docs", "# Result Access Guard\n\nFix organization-scoped result access. Use the Nexterview Run button to check authorization behavior.\n"),
    ],
    "expected_solution_files": [
        _solution("app/access.py", "python", "RESULTS = {'r1': {'organization_id': 'org_a', 'score': 91}}\n\n\ndef get_result(result_id: str, organization_id: str):\n    result = RESULTS.get(result_id)\n    if result is None or result.get('organization_id') != organization_id:\n        raise PermissionError('result not found')\n    return result\n"),
    ],
}


_TS_WEIGHTED_SCORE = {
    "scenario": _scenario(
        title="Fix weighted score aggregation",
        context=(
            "Hiring committees compare calibrated scorecards across candidates. The current utility averages category "
            "scores equally and ignores configured weights."
        ),
        summary="Correct the TypeScript scoring utility to calculate weighted scores.",
        requirements=["Multiply each category score by its weight.", "Normalize weights from percentages.", "Round the final score to two decimals."],
        constraints=["Do not special-case category names.", "Keep missing categories out of the denominator."],
        bug="The aggregator uses a plain average, so low-weight and high-weight categories affect the final score equally.",
        feature="Return accurate weighted scorecard totals.",
        behavior="A scorecard with correctness weighted at 70% should be dominated by correctness.",
        instructions="Fix the utility and explain how you handled weights and rounding.",
        rubric=(
            "Candidate implements real weighted arithmetic. Candidate handles edge cases. "
            "Candidate avoids hardcoded category-specific math."
        ),
    ),
    "project": _project(
        name="scorecard-utils",
        stack="TypeScript + Node.js",
        language="typescript",
        framework="Node.js",
        package_manager="npm",
        install="npm install",
        run="npm run dev",
        test="npm test",
        entrypoint="src/score.ts",
    ),
    "files": [
        _file("src/score.ts", "typescript", "source", "export type ScoreItem = { score: number; weight: number };\n\nexport function weightedScore(items: ScoreItem[]): number {\n  const total = items.reduce((sum, item) => sum + item.score, 0);\n  return Math.round((total / items.length) * 100) / 100;\n}\n"),
        _file("src/data/weights.json", "json", "data", "[{\"score\":100,\"weight\":70},{\"score\":0,\"weight\":30}]\n"),
        _file("tests/score.test.ts", "typescript", "test", "import { expect, test } from 'vitest';\nimport { weightedScore } from '../src/score';\n\ntest('uses category weights', () => {\n  expect(weightedScore([{ score: 100, weight: 70 }, { score: 0, weight: 30 }])).toBe(70);\n});\n"),
        _file("package.json", "json", "config", "{\"scripts\":{\"test\":\"vitest run\"},\"devDependencies\":{\"vitest\":\"latest\",\"typescript\":\"latest\"}}\n"),
        _file("README.md", "markdown", "docs", "# Scorecard Utils\n\nFix weighted score aggregation. Use the Nexterview Run button to check the utility.\n"),
    ],
    "expected_solution_files": [
        _solution("src/score.ts", "typescript", "export type ScoreItem = { score: number; weight: number };\n\nexport function weightedScore(items: ScoreItem[]): number {\n  const weightTotal = items.reduce((sum, item) => sum + item.weight, 0);\n  if (weightTotal === 0) return 0;\n  const weighted = items.reduce((sum, item) => sum + item.score * item.weight, 0) / weightTotal;\n  return Math.round(weighted * 100) / 100;\n}\n"),
    ],
}


_SPRING_BOOT_POM = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n"
    "  xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd\">\n"
    "  <modelVersion>4.0.0</modelVersion>\n"
    "  <parent>\n"
    "    <groupId>org.springframework.boot</groupId>\n"
    "    <artifactId>spring-boot-starter-parent</artifactId>\n"
    "    <version>3.3.5</version>\n"
    "    <relativePath />\n"
    "  </parent>\n"
    "  <groupId>com.interview</groupId>\n"
    "  <artifactId>scenario-app</artifactId>\n"
    "  <version>0.0.1-SNAPSHOT</version>\n"
    "  <properties><java.version>21</java.version></properties>\n"
    "  <dependencies>\n"
    "    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>\n"
    "    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>\n"
    "    <dependency><groupId>org.springframework.data</groupId><artifactId>spring-data-commons</artifactId></dependency>\n"
    "    <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>\n"
    "  </dependencies>\n"
    "  <build><plugins><plugin><groupId>org.springframework.boot</groupId><artifactId>spring-boot-maven-plugin</artifactId></plugin></plugins></build>\n"
    "</project>\n"
)


_SPRING_BOOT_PAGINATION = {
    "scenario": _scenario(
        title="Fix candidate API pagination",
        context=(
            "Recruiting coordinators review large candidate lists before scheduling panels. The Spring Boot API "
            "returns every candidate even when the UI requests a small page, causing slow loads for enterprise teams."
        ),
        summary="Fix the Spring Boot REST API so page and size parameters control candidate results.",
        requirements=[
            "Honor page and size query parameters in the service layer.",
            "Keep the controller response as a list of candidates.",
            "Clamp invalid page or size inputs safely before building the page request.",
        ],
        constraints=["Use the existing repository abstraction.", "Do not replace the Spring Boot project with another stack."],
        bug="CandidateService returns repository.findAll() and ignores the provided pagination parameters.",
        feature="Return deterministic paginated candidate lists for dashboard consumers.",
        behavior="GET /api/candidates?page=1&size=2 returns the second page with two candidates instead of every record.",
        instructions="Fix the service behavior, validate with the workspace checks, and explain the pagination edge cases you handled.",
        rubric=(
            "Candidate uses PageRequest or equivalent pagination rather than filtering in tests. "
            "Candidate preserves the controller contract and explains how the failing test proves the fix."
        ),
    ),
    "project": _project(
        name="spring-candidate-pagination",
        stack="Java + Spring Boot + Maven",
        language="java",
        framework="Spring Boot",
        package_manager="Maven",
        test_framework="JUnit",
        install="mvn dependency:resolve",
        run="mvn spring-boot:run",
        test="mvn test",
        entrypoint="src/main/java/com/interview/app/Application.java",
    ),
    "files": [
        _file("pom.xml", "xml", "config", _SPRING_BOOT_POM),
        _file("src/main/java/com/interview/app/Application.java", "java", "source", "package com.interview.app;\n\nimport org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class Application {\n    public static void main(String[] args) {\n        SpringApplication.run(Application.class, args);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/controller/CandidateController.java", "java", "source", "package com.interview.app.controller;\n\nimport com.interview.app.model.Candidate;\nimport com.interview.app.service.CandidateService;\nimport java.util.List;\nimport org.springframework.web.bind.annotation.GetMapping;\nimport org.springframework.web.bind.annotation.RequestParam;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\npublic class CandidateController {\n    private final CandidateService candidateService;\n\n    public CandidateController(CandidateService candidateService) {\n        this.candidateService = candidateService;\n    }\n\n    @GetMapping(\"/api/candidates\")\n    public List<Candidate> listCandidates(@RequestParam(defaultValue = \"0\") int page, @RequestParam(defaultValue = \"25\") int size) {\n        return candidateService.listCandidates(page, size);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/model/Candidate.java", "java", "source", "package com.interview.app.model;\n\npublic record Candidate(String id, String name, String status) {}\n"),
        _file("src/main/java/com/interview/app/repository/CandidateRepository.java", "java", "source", "package com.interview.app.repository;\n\nimport com.interview.app.model.Candidate;\nimport java.util.List;\nimport org.springframework.data.domain.Pageable;\nimport org.springframework.stereotype.Repository;\n\n@Repository\npublic class CandidateRepository {\n    private final List<Candidate> candidates = List.of(\n        new Candidate(\"cand_1\", \"Ada Lovelace\", \"active\"),\n        new Candidate(\"cand_2\", \"Grace Hopper\", \"active\"),\n        new Candidate(\"cand_3\", \"Katherine Johnson\", \"paused\"),\n        new Candidate(\"cand_4\", \"Edsger Dijkstra\", \"active\")\n    );\n\n    public List<Candidate> findAll() {\n        return candidates;\n    }\n\n    public List<Candidate> findPage(Pageable pageable) {\n        int start = Math.toIntExact(pageable.getOffset());\n        int end = Math.min(start + pageable.getPageSize(), candidates.size());\n        if (start >= candidates.size()) {\n            return List.of();\n        }\n        return candidates.subList(start, end);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/service/CandidateService.java", "java", "source", "package com.interview.app.service;\n\nimport com.interview.app.model.Candidate;\nimport com.interview.app.repository.CandidateRepository;\nimport java.util.List;\nimport org.springframework.stereotype.Service;\n\n@Service\npublic class CandidateService {\n    private final CandidateRepository repository;\n\n    public CandidateService(CandidateRepository repository) {\n        this.repository = repository;\n    }\n\n    public List<Candidate> listCandidates(int page, int size) {\n        return repository.findAll();\n    }\n}\n"),
        _file("src/main/resources/candidates.json", "json", "data", "[{\"id\":\"cand_1\",\"name\":\"Ada Lovelace\"},{\"id\":\"cand_2\",\"name\":\"Grace Hopper\"},{\"id\":\"cand_3\",\"name\":\"Katherine Johnson\"}]\n"),
        _file("src/test/java/com/interview/app/CandidateControllerTest.java", "java", "test", "package com.interview.app;\n\nimport static org.hamcrest.Matchers.hasSize;\nimport static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;\n\nimport org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;\nimport org.springframework.boot.test.context.SpringBootTest;\nimport org.springframework.test.web.servlet.MockMvc;\n\n@SpringBootTest\n@AutoConfigureMockMvc\nclass CandidateControllerTest {\n    @Autowired MockMvc mockMvc;\n\n    @Test\n    void appliesPageAndSizeParameters() throws Exception {\n        mockMvc.perform(get(\"/api/candidates?page=1&size=2\"))\n            .andExpect(status().isOk())\n            .andExpect(jsonPath(\"$\", hasSize(2)))\n            .andExpect(jsonPath(\"$[0].id\").value(\"cand_3\"));\n    }\n}\n"),
        _file("README.md", "markdown", "docs", "# Spring Candidate Pagination\n\nFix the candidate listing pagination in the Spring Boot service. Use the Nexterview Run button to check your work.\n"),
    ],
    "expected_solution_files": [
        _solution("src/main/java/com/interview/app/service/CandidateService.java", "java", "package com.interview.app.service;\n\nimport com.interview.app.model.Candidate;\nimport com.interview.app.repository.CandidateRepository;\nimport java.util.List;\nimport org.springframework.data.domain.PageRequest;\nimport org.springframework.stereotype.Service;\n\n@Service\npublic class CandidateService {\n    private final CandidateRepository repository;\n\n    public CandidateService(CandidateRepository repository) {\n        this.repository = repository;\n    }\n\n    public List<Candidate> listCandidates(int page, int size) {\n        int safePage = Math.max(page, 0);\n        int safeSize = Math.max(size, 1);\n        return repository.findPage(PageRequest.of(safePage, safeSize));\n    }\n}\n"),
    ],
}


_SPRING_BOOT_VALIDATION = {
    "scenario": _scenario(
        title="Validate candidate creation requests",
        context=(
            "Recruiting operations imports candidates from partner systems. Blank emails and unsupported statuses "
            "are being accepted by a Spring Boot API and later breaking automation."
        ),
        summary="Add Spring validation so invalid candidate creation requests are rejected.",
        requirements=[
            "Reject blank or malformed email addresses.",
            "Reject statuses outside active, paused, or archived.",
            "Keep valid candidate creation requests accepted.",
        ],
        constraints=["Use Jakarta Bean Validation through Spring MVC.", "Do not implement fragile manual string checks in the service."],
        bug="The request body has plain String fields and the controller does not trigger validation.",
        feature="Enforce a safe candidate creation contract at the API boundary.",
        behavior="Invalid email or status payloads return HTTP 400 while a valid payload returns HTTP 201.",
        instructions="Fix validation at the model/controller boundary and explain why invalid payloads are rejected.",
        rubric=(
            "Candidate uses Jakarta validation annotations and @Valid. Candidate keeps service logic focused. "
            "Candidate validates both negative and positive request paths."
        ),
    ),
    "project": _project(
        name="spring-candidate-validation",
        stack="Java + Spring Boot + Maven",
        language="java",
        framework="Spring Boot",
        package_manager="Maven",
        test_framework="JUnit",
        install="mvn dependency:resolve",
        run="mvn spring-boot:run",
        test="mvn test",
        entrypoint="src/main/java/com/interview/app/Application.java",
    ),
    "files": [
        _file("pom.xml", "xml", "config", _SPRING_BOOT_POM),
        _file("src/main/java/com/interview/app/Application.java", "java", "source", "package com.interview.app;\n\nimport org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class Application {\n    public static void main(String[] args) {\n        SpringApplication.run(Application.class, args);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/model/Candidate.java", "java", "source", "package com.interview.app.model;\n\npublic class Candidate {\n    private String email;\n    private String status;\n\n    public String getEmail() { return email; }\n    public void setEmail(String email) { this.email = email; }\n    public String getStatus() { return status; }\n    public void setStatus(String status) { this.status = status; }\n}\n"),
        _file("src/main/java/com/interview/app/controller/CandidateController.java", "java", "source", "package com.interview.app.controller;\n\nimport com.interview.app.model.Candidate;\nimport com.interview.app.service.CandidateService;\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.bind.annotation.RequestBody;\nimport org.springframework.web.bind.annotation.ResponseStatus;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\npublic class CandidateController {\n    private final CandidateService candidateService;\n\n    public CandidateController(CandidateService candidateService) {\n        this.candidateService = candidateService;\n    }\n\n    @PostMapping(\"/api/candidates\")\n    @ResponseStatus(HttpStatus.CREATED)\n    public Candidate create(@RequestBody Candidate candidate) {\n        return candidateService.create(candidate);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/service/CandidateService.java", "java", "source", "package com.interview.app.service;\n\nimport com.interview.app.model.Candidate;\nimport org.springframework.stereotype.Service;\n\n@Service\npublic class CandidateService {\n    public Candidate create(Candidate candidate) {\n        return candidate;\n    }\n}\n"),
        _file("src/main/resources/candidate-statuses.json", "json", "data", "[\"active\",\"paused\",\"archived\"]\n"),
        _file("src/test/java/com/interview/app/CandidateControllerTest.java", "java", "test", "package com.interview.app;\n\nimport static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;\n\nimport org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;\nimport org.springframework.boot.test.context.SpringBootTest;\nimport org.springframework.http.MediaType;\nimport org.springframework.test.web.servlet.MockMvc;\n\n@SpringBootTest\n@AutoConfigureMockMvc\nclass CandidateControllerTest {\n    @Autowired MockMvc mockMvc;\n\n    @Test\n    void rejectsBlankEmail() throws Exception {\n        mockMvc.perform(post(\"/api/candidates\").contentType(MediaType.APPLICATION_JSON).content(\"{\\\"email\\\":\\\"\\\",\\\"status\\\":\\\"active\\\"}\"))\n            .andExpect(status().isBadRequest());\n    }\n\n    @Test\n    void rejectsInvalidStatus() throws Exception {\n        mockMvc.perform(post(\"/api/candidates\").contentType(MediaType.APPLICATION_JSON).content(\"{\\\"email\\\":\\\"dev@example.com\\\",\\\"status\\\":\\\"deleted\\\"}\"))\n            .andExpect(status().isBadRequest());\n    }\n}\n"),
        _file("README.md", "markdown", "docs", "# Spring Candidate Validation\n\nTighten candidate creation validation. Use the Nexterview Run button to check the API contract.\n"),
    ],
    "expected_solution_files": [
        _solution("src/main/java/com/interview/app/model/Candidate.java", "java", "package com.interview.app.model;\n\nimport jakarta.validation.constraints.Email;\nimport jakarta.validation.constraints.NotBlank;\nimport jakarta.validation.constraints.Pattern;\n\npublic class Candidate {\n    @NotBlank\n    @Email\n    private String email;\n\n    @NotBlank\n    @Pattern(regexp = \"active|paused|archived\")\n    private String status;\n\n    public String getEmail() { return email; }\n    public void setEmail(String email) { this.email = email; }\n    public String getStatus() { return status; }\n    public void setStatus(String status) { this.status = status; }\n}\n"),
        _solution("src/main/java/com/interview/app/controller/CandidateController.java", "java", "package com.interview.app.controller;\n\nimport com.interview.app.model.Candidate;\nimport com.interview.app.service.CandidateService;\nimport jakarta.validation.Valid;\nimport org.springframework.http.HttpStatus;\nimport org.springframework.web.bind.annotation.PostMapping;\nimport org.springframework.web.bind.annotation.RequestBody;\nimport org.springframework.web.bind.annotation.ResponseStatus;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\npublic class CandidateController {\n    private final CandidateService candidateService;\n\n    public CandidateController(CandidateService candidateService) {\n        this.candidateService = candidateService;\n    }\n\n    @PostMapping(\"/api/candidates\")\n    @ResponseStatus(HttpStatus.CREATED)\n    public Candidate create(@Valid @RequestBody Candidate candidate) {\n        return candidateService.create(candidate);\n    }\n}\n"),
    ],
}


_SPRING_BOOT_ORG_ACCESS = {
    "scenario": _scenario(
        title="Enforce organization-scoped result access",
        context=(
            "Enterprise hiring teams require tenant isolation. An audit found that a Spring Boot result endpoint "
            "can return another organization's interview result when given a valid result id."
        ),
        summary="Fix the Spring Boot service so result lookups are scoped by organization id.",
        requirements=[
            "Filter result reads by both result id and organization id.",
            "Return not found for cross-organization access.",
            "Preserve successful same-organization reads.",
        ],
        constraints=["Do not rely on frontend filtering.", "Do not leak whether another organization's result exists."],
        bug="ResultService fetches by result id only and ignores organizationId.",
        feature="Add tenant-safe authorization behavior to result reads.",
        behavior="A request from org_b cannot read a result owned by org_a, even with the correct result id.",
        instructions="Fix the authorization path and summarize the tenant-isolation risk you addressed.",
        rubric=(
            "Candidate enforces server-side organization scoping. Candidate avoids information leakage. "
            "Candidate validates allowed and denied paths."
        ),
    ),
    "project": _project(
        name="spring-result-access",
        stack="Java + Spring Boot + Maven",
        language="java",
        framework="Spring Boot",
        package_manager="Maven",
        test_framework="JUnit",
        install="mvn dependency:resolve",
        run="mvn spring-boot:run",
        test="mvn test",
        entrypoint="src/main/java/com/interview/app/Application.java",
    ),
    "files": [
        _file("pom.xml", "xml", "config", _SPRING_BOOT_POM),
        _file("src/main/java/com/interview/app/Application.java", "java", "source", "package com.interview.app;\n\nimport org.springframework.boot.SpringApplication;\nimport org.springframework.boot.autoconfigure.SpringBootApplication;\n\n@SpringBootApplication\npublic class Application {\n    public static void main(String[] args) {\n        SpringApplication.run(Application.class, args);\n    }\n}\n"),
        _file("src/main/java/com/interview/app/model/Result.java", "java", "source", "package com.interview.app.model;\n\npublic record Result(String id, String organizationId, int score) {}\n"),
        _file("src/main/java/com/interview/app/repository/ResultRepository.java", "java", "source", "package com.interview.app.repository;\n\nimport com.interview.app.model.Result;\nimport java.util.Map;\nimport java.util.Optional;\nimport org.springframework.stereotype.Repository;\n\n@Repository\npublic class ResultRepository {\n    private final Map<String, Result> results = Map.of(\n        \"res_1\", new Result(\"res_1\", \"org_a\", 91),\n        \"res_2\", new Result(\"res_2\", \"org_b\", 84)\n    );\n\n    public Optional<Result> findById(String resultId) {\n        return Optional.ofNullable(results.get(resultId));\n    }\n}\n"),
        _file("src/main/java/com/interview/app/service/ResultService.java", "java", "source", "package com.interview.app.service;\n\nimport com.interview.app.model.Result;\nimport com.interview.app.repository.ResultRepository;\nimport org.springframework.stereotype.Service;\nimport org.springframework.web.server.ResponseStatusException;\nimport org.springframework.http.HttpStatus;\n\n@Service\npublic class ResultService {\n    private final ResultRepository repository;\n\n    public ResultService(ResultRepository repository) {\n        this.repository = repository;\n    }\n\n    public Result getResult(String resultId, String organizationId) {\n        return repository.findById(resultId)\n            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));\n    }\n}\n"),
        _file("src/main/java/com/interview/app/controller/ResultController.java", "java", "source", "package com.interview.app.controller;\n\nimport com.interview.app.model.Result;\nimport com.interview.app.service.ResultService;\nimport org.springframework.web.bind.annotation.GetMapping;\nimport org.springframework.web.bind.annotation.PathVariable;\nimport org.springframework.web.bind.annotation.RequestHeader;\nimport org.springframework.web.bind.annotation.RestController;\n\n@RestController\npublic class ResultController {\n    private final ResultService resultService;\n\n    public ResultController(ResultService resultService) {\n        this.resultService = resultService;\n    }\n\n    @GetMapping(\"/api/results/{resultId}\")\n    public Result getResult(@PathVariable String resultId, @RequestHeader(\"X-Organization-Id\") String organizationId) {\n        return resultService.getResult(resultId, organizationId);\n    }\n}\n"),
        _file("src/main/resources/results.json", "json", "data", "{\"res_1\":{\"organizationId\":\"org_a\",\"score\":91},\"res_2\":{\"organizationId\":\"org_b\",\"score\":84}}\n"),
        _file("src/test/java/com/interview/app/ResultControllerTest.java", "java", "test", "package com.interview.app;\n\nimport static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;\nimport static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;\n\nimport org.junit.jupiter.api.Test;\nimport org.springframework.beans.factory.annotation.Autowired;\nimport org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;\nimport org.springframework.boot.test.context.SpringBootTest;\nimport org.springframework.test.web.servlet.MockMvc;\n\n@SpringBootTest\n@AutoConfigureMockMvc\nclass ResultControllerTest {\n    @Autowired MockMvc mockMvc;\n\n    @Test\n    void blocksCrossOrganizationResultAccess() throws Exception {\n        mockMvc.perform(get(\"/api/results/res_1\").header(\"X-Organization-Id\", \"org_b\"))\n            .andExpect(status().isNotFound());\n    }\n\n    @Test\n    void allowsSameOrganizationResultAccess() throws Exception {\n        mockMvc.perform(get(\"/api/results/res_1\").header(\"X-Organization-Id\", \"org_a\"))\n            .andExpect(status().isOk())\n            .andExpect(jsonPath(\"$.score\").value(91));\n    }\n}\n"),
        _file("README.md", "markdown", "docs", "# Spring Result Access\n\nFix organization-scoped result access. Use the Nexterview Run button to check authorization behavior.\n"),
    ],
    "expected_solution_files": [
        _solution("src/main/java/com/interview/app/service/ResultService.java", "java", "package com.interview.app.service;\n\nimport com.interview.app.model.Result;\nimport com.interview.app.repository.ResultRepository;\nimport org.springframework.http.HttpStatus;\nimport org.springframework.stereotype.Service;\nimport org.springframework.web.server.ResponseStatusException;\n\n@Service\npublic class ResultService {\n    private final ResultRepository repository;\n\n    public ResultService(ResultRepository repository) {\n        this.repository = repository;\n    }\n\n    public Result getResult(String resultId, String organizationId) {\n        Result result = repository.findById(resultId)\n            .filter(candidate -> candidate.organizationId().equals(organizationId))\n            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));\n        return result;\n    }\n}\n"),
    ],
}


_ORDERS_REVIEW = {
    "scenario": _scenario(
        title="Fix order totals and add status filtering",
        context=(
            "The customer success team uses an internal order review API before renewal calls. Account managers "
            "noticed that high-quantity orders are underreported, and they need to filter orders by fulfillment status."
        ),
        summary="Fix the order total calculation bug and add a status filter to the orders endpoint.",
        requirements=[
            "Calculate totals using item quantity and unit price.",
            "Add an optional status query parameter to the orders endpoint.",
            "Preserve the existing response shape.",
        ],
        constraints=["Keep visible seed data usable.", "Do not hardcode only the paid status path."],
        bug="The order total calculation ignores item quantity, so multi-unit line items are undercounted.",
        feature="Add an optional status query parameter to the orders endpoint and return only matching orders.",
        behavior="Order totals multiply unit price by quantity, and GET /orders?status=paid returns only paid orders.",
        instructions="Fix the API behavior, validate with the workspace checks, and explain the root cause plus verification steps.",
        rubric=(
            "Candidate fixes app/services/orders.py rather than only changing tests. Candidate implements generic status filtering. "
            "Candidate preserves response shape and explains validation clearly."
        ),
    ),
    "project": _project(
        name="orders-review-api",
        stack="Python + FastAPI",
        language="python",
        framework="FastAPI",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="uvicorn app.main:app --reload",
        test="pytest",
        entrypoint="app/main.py",
    ),
    "files": [
        _file(
            "app/main.py",
            "python",
            "source",
            (
                "from fastapi import FastAPI\n\n"
                "from app.services.orders import load_orders, summarize_order\n\n"
                "app = FastAPI(title=\"Orders Review API\")\n\n\n"
                "@app.get(\"/health\")\n"
                "def health() -> dict[str, str]:\n"
                "    return {\"status\": \"ok\"}\n\n\n"
                "@app.get(\"/orders\")\n"
                "def list_orders() -> list[dict[str, object]]:\n"
                "    return [summarize_order(order) for order in load_orders()]\n"
            ),
        ),
        _file(
            "app/services/orders.py",
            "python",
            "source",
            (
                "from __future__ import annotations\n\n"
                "import json\n"
                "from pathlib import Path\n"
                "from typing import Any\n\n"
                "DATA_PATH = Path(__file__).resolve().parents[1] / \"data\" / \"orders.json\"\n\n\n"
                "def load_orders() -> list[dict[str, Any]]:\n"
                "    return json.loads(DATA_PATH.read_text(encoding=\"utf-8\"))\n\n\n"
                "def calculate_order_total(order: dict[str, Any]) -> float:\n"
                "    # BUG: quantity is ignored, so multi-unit items are undercounted.\n"
                "    return round(sum(item[\"unit_price\"] for item in order[\"items\"]), 2)\n\n\n"
                "def summarize_order(order: dict[str, Any]) -> dict[str, object]:\n"
                "    return {\n"
                "        \"id\": order[\"id\"],\n"
                "        \"customer\": order[\"customer\"],\n"
                "        \"status\": order[\"status\"],\n"
                "        \"total\": calculate_order_total(order),\n"
                "    }\n"
            ),
        ),
        _file(
            "app/data/orders.json",
            "json",
            "data",
            "[{\"id\":\"ord_1001\",\"customer\":\"Acme Manufacturing\",\"status\":\"paid\",\"items\":[{\"sku\":\"seat-pro\",\"quantity\":3,\"unit_price\":49.0},{\"sku\":\"onboarding\",\"quantity\":1,\"unit_price\":199.0}]},{\"id\":\"ord_1002\",\"customer\":\"Northwind Health\",\"status\":\"pending\",\"items\":[{\"sku\":\"seat-team\",\"quantity\":2,\"unit_price\":29.0}]}]\n",
        ),
        _file(
            "tests/test_orders.py",
            "python",
            "test",
            (
                "from fastapi.testclient import TestClient\n\n"
                "from app.main import app\n"
                "from app.services.orders import calculate_order_total\n\n"
                "client = TestClient(app)\n\n\n"
                "def test_order_total_uses_quantity() -> None:\n"
                "    order = {\"items\": [{\"sku\": \"seat-pro\", \"quantity\": 3, \"unit_price\": 49.0}, {\"sku\": \"onboarding\", \"quantity\": 1, \"unit_price\": 199.0}]}\n"
                "    assert calculate_order_total(order) == 346.0\n\n\n"
                "def test_orders_can_be_filtered_by_status() -> None:\n"
                "    response = client.get(\"/orders?status=paid\")\n"
                "    assert response.status_code == 200\n"
                "    orders = response.json()\n"
                "    assert orders\n"
                "    assert {order[\"status\"] for order in orders} == {\"paid\"}\n"
            ),
        ),
        _file("tests/test_orders_hidden.py", "python", "hidden_test", "from app.services.orders import calculate_order_total\n\n\ndef test_zero_quantity_items_do_not_inflate_totals() -> None:\n    order = {\"items\": [{\"sku\": \"trial\", \"quantity\": 0, \"unit_price\": 99.0}]}\n    assert calculate_order_total(order) == 0.0\n", hidden=True, editable=False),
        _file("requirements.txt", "text", "config", "fastapi==0.115.6\nuvicorn==0.34.0\npytest==8.2.2\nhttpx==0.27.2\n"),
        _file("README.md", "markdown", "docs", "# Orders Review API\n\nFix totals and status filtering. Use the Nexterview Run button to check your work.\n"),
    ],
    "expected_solution_files": [
        _solution(
            "app/services/orders.py",
            "python",
            (
                "from __future__ import annotations\n\nimport json\nfrom pathlib import Path\nfrom typing import Any\n\n"
                "DATA_PATH = Path(__file__).resolve().parents[1] / \"data\" / \"orders.json\"\n\n\n"
                "def load_orders() -> list[dict[str, Any]]:\n"
                "    return json.loads(DATA_PATH.read_text(encoding=\"utf-8\"))\n\n\n"
                "def calculate_order_total(order: dict[str, Any]) -> float:\n"
                "    return round(sum(item[\"unit_price\"] * item[\"quantity\"] for item in order[\"items\"]), 2)\n\n\n"
                "def summarize_order(order: dict[str, Any]) -> dict[str, object]:\n"
                "    return {\"id\": order[\"id\"], \"customer\": order[\"customer\"], \"status\": order[\"status\"], \"total\": calculate_order_total(order)}\n"
            ),
        ),
        _solution(
            "app/main.py",
            "python",
            (
                "from fastapi import FastAPI\n\nfrom app.services.orders import load_orders, summarize_order\n\napp = FastAPI(title=\"Orders Review API\")\n\n\n"
                "@app.get(\"/health\")\ndef health() -> dict[str, str]:\n    return {\"status\": \"ok\"}\n\n\n"
                "@app.get(\"/orders\")\ndef list_orders(status: str | None = None) -> list[dict[str, object]]:\n    orders = load_orders()\n    if status is not None:\n        orders = [order for order in orders if order[\"status\"] == status]\n    return [summarize_order(order) for order in orders]\n"
            ),
        ),
    ],
}


_SEED_SCENARIOS = (
    SeedScenario("spring-boot-pagination", "java_spring_boot", ("backend", "engineer"), ("java", "spring", "maven"), ("backend debugging", "pagination"), _SPRING_BOOT_PAGINATION),
    SeedScenario("spring-boot-validation", "java_spring_boot", ("backend", "api"), ("java", "spring", "validation"), ("validation", "api"), _SPRING_BOOT_VALIDATION),
    SeedScenario("spring-boot-org-access", "java_spring_boot", ("security", "backend"), ("java", "spring", "auth"), ("security", "authorization"), _SPRING_BOOT_ORG_ACCESS),
    SeedScenario("orders-review", "python_fastapi", ("backend", "engineer"), ("python", "fastapi", "postgresql"), ("backend debugging", "debugging"), _ORDERS_REVIEW),
    SeedScenario("fastapi-pagination", "python_fastapi", ("backend", "platform"), ("python", "fastapi", "postgresql"), ("debugging", "api", "pagination"), _FASTAPI_PAGINATION),
    SeedScenario("fastapi-validation", "python_fastapi", ("backend", "api"), ("python", "fastapi", "pydantic"), ("validation", "api"), _FASTAPI_VALIDATION),
    SeedScenario("next-hydration", "react_next", ("frontend", "react"), ("react", "next", "typescript"), ("hydration", "frontend", "bug"), _NEXT_HYDRATION),
    SeedScenario("full-stack-feedback", "react_next", ("full-stack", "product"), ("react", "fastapi", "full-stack"), ("feature", "implementation"), _FULL_STACK_FEEDBACK),
    SeedScenario("rag-metadata", "ai_rag", ("ai", "rag", "platform"), ("python", "langchain", "rag"), ("ai engineering", "retrieval"), _RAG_METADATA),
    SeedScenario("api-performance", "python_fastapi", ("backend", "platform"), ("python", "api", "postgresql"), ("performance", "n+1", "pagination"), _API_PERFORMANCE),
    SeedScenario("security-org-access", "python_fastapi", ("security", "backend"), ("python", "fastapi", "auth"), ("security", "review", "authorization"), _SECURITY_ORG_ACCESS),
    SeedScenario("typescript-weighted-score", "node_express", ("typescript", "backend"), ("typescript", "node"), ("utility", "scoring", "refactor"), _TS_WEIGHTED_SCORE),
)

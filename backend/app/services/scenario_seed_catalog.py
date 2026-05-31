from __future__ import annotations

from dataclasses import dataclass

from app.models.interview import Interview
from app.schemas.project import AIGeneratedProjectEnvelope


@dataclass(frozen=True)
class SeedScenario:
    key: str
    role_keywords: tuple[str, ...]
    stack_keywords: tuple[str, ...]
    interview_keywords: tuple[str, ...]
    payload: dict[str, object]


def seed_scenarios() -> tuple[SeedScenario, ...]:
    return _SEED_SCENARIOS


def fallback_envelope_for_interview(interview: Interview) -> AIGeneratedProjectEnvelope:
    return AIGeneratedProjectEnvelope.model_validate(_best_seed_for_interview(interview).payload)


def _best_seed_for_interview(interview: Interview) -> SeedScenario:
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

    return max(_SEED_SCENARIOS, key=score)


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
        stack="Python + API Performance",
        language="python",
        framework="Service",
        package_manager="pip",
        install="pip install -r requirements.txt",
        run="python app/results.py",
        test="pytest",
        entrypoint="app/results.py",
    ),
    "files": [
        _file("app/results.py", "python", "source", "def serialize_results(results, load_candidate):\n    rows = []\n    for result in results:\n        candidate = load_candidate(result['candidate_id'])\n        rows.append({'score': result['score'], 'candidate_name': candidate['name']})\n    return rows\n"),
        _file("app/data/results.json", "json", "data", "[{\"candidate_id\":\"c1\",\"score\":91},{\"candidate_id\":\"c2\",\"score\":84},{\"candidate_id\":\"c3\",\"score\":77}]\n"),
        _file("tests/test_results.py", "python", "test", "from app.results import serialize_results\n\n\ndef test_serializer_uses_preloaded_candidates() -> None:\n    calls = []\n    def load_candidate(candidate_id):\n        calls.append(candidate_id)\n        return {'name': candidate_id}\n    rows = serialize_results([{'candidate_id': 'c1', 'score': 91}], load_candidate)\n    assert rows == [{'score': 91, 'candidate_name': 'Ada Lovelace'}]\n    assert calls == []\n"),
        _file("requirements.txt", "text", "config", "pytest==8.2.2\n"),
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
    SeedScenario("orders-review", ("backend", "engineer"), ("python", "fastapi", "postgresql"), ("backend debugging", "debugging"), _ORDERS_REVIEW),
    SeedScenario("fastapi-pagination", ("backend", "platform"), ("python", "fastapi", "postgresql"), ("debugging", "api", "pagination"), _FASTAPI_PAGINATION),
    SeedScenario("fastapi-validation", ("backend", "api"), ("python", "fastapi", "pydantic"), ("validation", "api"), _FASTAPI_VALIDATION),
    SeedScenario("next-hydration", ("frontend", "react"), ("react", "next", "typescript"), ("hydration", "frontend", "bug"), _NEXT_HYDRATION),
    SeedScenario("full-stack-feedback", ("full-stack", "product"), ("react", "fastapi", "full-stack"), ("feature", "implementation"), _FULL_STACK_FEEDBACK),
    SeedScenario("rag-metadata", ("ai", "rag", "platform"), ("python", "langchain", "rag"), ("ai engineering", "retrieval"), _RAG_METADATA),
    SeedScenario("api-performance", ("backend", "platform"), ("python", "api", "postgresql"), ("performance", "n+1", "pagination"), _API_PERFORMANCE),
    SeedScenario("security-org-access", ("security", "backend"), ("python", "fastapi", "auth"), ("security", "review", "authorization"), _SECURITY_ORG_ACCESS),
    SeedScenario("typescript-weighted-score", ("typescript", "backend"), ("typescript", "node"), ("utility", "scoring", "refactor"), _TS_WEIGHTED_SCORE),
)

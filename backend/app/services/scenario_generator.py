from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import settings
from app.models.interview import Interview
from app.schemas.project import AIGeneratedProjectEnvelope, GeneratedProjectFile, GeneratedScenarioProject
from app.schemas.scenario import GeneratedScenario, ScenarioFilePayload
from app.services.scenario_seed_catalog import fallback_envelope_for_interview

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
            response = client.responses.create(
                model=settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": _system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": _build_generation_prompt(interview),
                    },
                ],
            )
            output_text = response.output_text.strip()
            if not output_text:
                raise ValueError("OpenAI returned an empty project generation response.")
            return ScenarioGenerationResult(
                scenario=parse_generated_project_json(output_text, interview=interview),
                source="openai",
                model=settings.openai_model,
            )
        except Exception:
            logger.warning("OpenAI project generation failed; using fallback project.", exc_info=True)
            return ScenarioGenerationResult(
                scenario=build_fallback_scenario(interview),
                source="fallback",
                model=settings.openai_model,
            )


def parse_generated_project_json(raw_json: str, *, interview: Interview) -> GeneratedScenario:
    try:
        envelope = AIGeneratedProjectEnvelope.model_validate_json(raw_json)
    except ValidationError:
        logger.warning("Generated project JSON failed validation.", exc_info=True)
        raise

    return _scenario_from_envelope(envelope=envelope, interview=interview)


def build_fallback_scenario(interview: Interview) -> GeneratedScenario:
    envelope = fallback_envelope_for_interview(interview)
    return _scenario_from_envelope(envelope=envelope, interview=interview)


def _scenario_from_envelope(*, envelope: AIGeneratedProjectEnvelope, interview: Interview) -> GeneratedScenario:
    entrypoint_file = _entrypoint_file(envelope)
    hidden_rubric = _text_to_items(envelope.scenario.hidden_rubric)
    expected_behavior = _text_to_items(envelope.scenario.expected_behavior)
    validation_steps = _text_to_items(envelope.scenario.validation_instructions)
    visible_requirements = envelope.scenario.visible_requirements or [
        f"Fix the intentional bug: {envelope.scenario.bug_description}",
        f"Implement the requested behavior: {envelope.scenario.feature_request}",
        *validation_steps[:2],
    ]
    technical_requirements = [
        *visible_requirements,
        f"Primary language/framework: {_primary_language(envelope, interview)} / {envelope.project.framework}",
    ]
    hidden_evaluation_points = hidden_rubric or [
        "Candidate identifies and fixes the actual bug in code.",
        "Candidate implements the feature request without breaking existing behavior.",
    ]
    interviewer_rubric = [
        *hidden_evaluation_points[:3],
        "Candidate explains verification steps and any remaining production risk.",
    ]

    project = GeneratedScenarioProject.model_validate(
        {
            "stack": _stack_items(envelope.project.stack, interview.stack),
            "project_name": envelope.project.project_name,
            "description": envelope.scenario.candidate_task_summary,
            "run_command": envelope.project.run_command,
            "test_command": envelope.project.test_command,
            "install_command": envelope.project.install_command,
            "entrypoint": envelope.project.entrypoint,
            "package_manager": envelope.project.package_manager,
            "framework": envelope.project.framework,
            "files": envelope.files,
        }
    )

    return GeneratedScenario.model_validate(
        {
            "title": envelope.scenario.title,
            "role_title": interview.role_title,
            "seniority": interview.seniority,
            "interview_type": interview.interview_type,
            "difficulty": interview.difficulty,
            "stack": project.stack,
            "language": _primary_language(envelope, interview),
            "framework": envelope.project.framework,
            "ai_mode": interview.allowed_ai_mode,
            "business_context": envelope.scenario.business_context,
            "technical_requirements": technical_requirements[:6],
            "visible_requirements": visible_requirements[:8],
            "starter_code": entrypoint_file.content,
            "starter_files_json": _starter_files(envelope.files),
            "test_files_json": _test_files(envelope.files),
            "expected_solution_files_json": [
                ScenarioFilePayload.model_validate(solution_file.model_dump())
                for solution_file in envelope.expected_solution_files
            ],
            "expected_behavior": expected_behavior,
            "logs_or_bug_report": envelope.scenario.bug_description,
            "bug_description": envelope.scenario.bug_description,
            "bug_description_internal": envelope.scenario.bug_description_internal or envelope.scenario.bug_description,
            "feature_request": envelope.scenario.feature_request,
            "validation_instructions": envelope.scenario.validation_instructions,
            "validation_command": envelope.project.validation_command or envelope.project.test_command,
            "constraints": envelope.scenario.constraints,
            "candidate_task_summary": envelope.scenario.candidate_task_summary,
            "expected_solution_summary": _solution_summary(envelope),
            "scenario_fit": _scenario_fit(interview, envelope),
            "hidden_evaluation_points": hidden_evaluation_points,
            "hidden_rubric": hidden_rubric,
            "candidate_instructions": envelope.scenario.candidate_instructions,
            "interviewer_rubric": interviewer_rubric,
            "project": project,
        }
    )


def _system_prompt() -> str:
    return (
        "You generate production-grade repo-based engineering interview simulations. "
        "Return only strict JSON, with no markdown fences or commentary. The JSON must match exactly this shape: "
        '{"scenario":{"title":"...","business_context":"...","candidate_task_summary":"...",'
        '"visible_requirements":["..."],"constraints":["..."],"bug_description":"...",'
        '"bug_description_internal":"...","feature_request":"...","expected_behavior":"...",'
        '"validation_instructions":"...","candidate_instructions":"...","hidden_rubric":"..."},'
        '"project":{"project_name":"...","stack":"...","language":"...","framework":"...","package_manager":"...",'
        '"install_command":"...","run_command":"...","test_command":"...","validation_command":"...",'
        '"entrypoint":"..."},'
        '"files":[{"path":"package.json","language":"json","file_type":"config","is_editable":true,'
        '"is_hidden":false,"content":"..."}],'
        '"expected_solution_files":[{"path":"src/file.ts","language":"typescript","content":"..."}]}. '
        "Generate 5 to 12 files. Include realistic folder structure, at least one JSON seed data file, one README.md "
        "or TASK.md, and at least one test or validation file. Put the intentional bug inside actual source code. "
        "Include one feature request that requires editing at least one additional file. Hidden files may be included "
        "only for interviewer-only tests and must use file_type hidden_test, is_hidden true, and is_editable false. "
        "The visible tests must fail against the starter files and pass against expected_solution_files. "
        "expected_solution_files are private interviewer/platform metadata and must include the corrected contents "
        "for each editable file that should change. "
        "The install_command, run_command, and test_command fields are internal platform runner metadata only. "
        "Do not put dependency installation, local server, or CLI test commands in candidate_instructions, "
        "validation_instructions, README.md, TASK.md, or any candidate-facing docs. Describe the candidate environment "
        "as already provisioned and tell candidates to use the platform Run button to see pass/fail checks."
    )


def _build_generation_prompt(interview: Interview) -> str:
    variation = _controlled_variation(interview)
    payload = {
        "role_title": interview.role_title,
        "seniority": interview.seniority,
        "stack": interview.stack,
        "difficulty": interview.difficulty,
        "interview_type": interview.interview_type,
        "duration_minutes": interview.duration_minutes,
        "allowed_ai_mode": interview.allowed_ai_mode,
        "evaluation_criteria": interview.evaluation_criteria,
        "supported_stack_selection": _stack_generation_guidance(interview.stack),
        "controlled_variation": variation,
    }
    return (
        "Generate one small but realistic runnable interview project from this configuration. "
        "Supported targets include React + Next.js, Python + FastAPI, TypeScript/Node, full-stack, platform, "
        "security, and AI/RAG engineering tasks. "
        "If the selected stack does not clearly match one of those, generate a generic TypeScript/Node project. "
        "The task must be role-aware, stack-aware, difficulty-aware, and interview-type-aware. "
        "Avoid generic LeetCode prompts, vague build-a-function tasks, and repeated payment retry bugs. "
        "Use the controlled variation values for domain, failure type, and task type unless the interview "
        "configuration strongly suggests a better fit. "
        "Do not include secrets, API keys, Docker credentials, or instructions to expose backend credentials. "
        "Assume dependencies are already installed in a mini interview environment; the candidate should edit files "
        "and press Run in Nexterview to view pass/fail checks.\n\n"
        f"Configuration JSON:\n{json.dumps(payload, indent=2)}"
    )


def _stack_generation_guidance(stack: list[str]) -> str:
    normalized = " ".join(stack).lower()
    if "react" in normalized or "next" in normalized:
        return "Generate a React + Next.js project."
    if "fastapi" in normalized or "python" in normalized:
        return "Generate a Python + FastAPI project."
    if "express" in normalized or "node" in normalized:
        return "Generate a Node.js + Express project."
    return "Generate a generic TypeScript/Node project."


def _entrypoint_file(envelope: AIGeneratedProjectEnvelope):
    for project_file in envelope.files:
        if project_file.path == envelope.project.entrypoint:
            return project_file
    raise ValueError("Validated project envelope is missing its entrypoint file.")


def _primary_language(envelope: AIGeneratedProjectEnvelope, interview: Interview) -> str:
    if envelope.project.language:
        return envelope.project.language
    stack_text = " ".join(interview.stack).lower()
    if "python" in stack_text or "fastapi" in stack_text:
        return "python"
    if "typescript" in stack_text or "react" in stack_text or "next" in stack_text or "node" in stack_text:
        return "typescript"
    if "java" in stack_text:
        return "java"
    if "go" in stack_text:
        return "go"
    return envelope.files[0].language


def _starter_files(files: list[GeneratedProjectFile]) -> list[ScenarioFilePayload]:
    return [
        ScenarioFilePayload(path=file.path, language=file.language, content=file.content)
        for file in files
        if not file.is_hidden and file.file_type.value not in {"test", "hidden_test"}
    ]


def _test_files(files: list[GeneratedProjectFile]) -> list[ScenarioFilePayload]:
    return [
        ScenarioFilePayload(path=file.path, language=file.language, content=file.content)
        for file in files
        if not file.is_hidden and file.file_type.value == "test"
    ]


def _solution_summary(envelope: AIGeneratedProjectEnvelope) -> str:
    changed_paths = ", ".join(solution_file.path for solution_file in envelope.expected_solution_files)
    return f"Expected solution updates: {changed_paths}."


def _scenario_fit(interview: Interview, envelope: AIGeneratedProjectEnvelope) -> str:
    return (
        f"Generated for {interview.seniority} {interview.role_title} using {', '.join(interview.stack)}. "
        f"The project targets {envelope.project.framework} and the {interview.interview_type} interview type, "
        f"with {interview.allowed_ai_mode} available to the candidate."
    )


def _controlled_variation(interview: Interview) -> dict[str, str]:
    domains = [
        "fintech",
        "healthcare",
        "logistics",
        "hiring",
        "ecommerce",
        "data platform",
        "internal tooling",
        "developer tools",
    ]
    failure_types = [
        "validation bug",
        "async bug",
        "auth bug",
        "N+1 query",
        "hydration bug",
        "state bug",
        "serialization bug",
        "race condition",
        "retrieval bug",
        "pagination bug",
        "caching bug",
    ]
    task_types = [
        "bug fix",
        "feature implementation",
        "refactor",
        "performance fix",
        "security fix",
    ]
    seed = sum(ord(character) for character in f"{interview.role_title}|{interview.stack}|{interview.interview_type}")
    return {
        "domain": domains[seed % len(domains)],
        "failure_type": failure_types[(seed // 3) % len(failure_types)],
        "task_type": task_types[(seed // 7) % len(task_types)],
    }


def _stack_items(raw_stack: str, interview_stack: list[str]) -> list[str]:
    parts = [part.strip() for part in re.split(r",|\+|/", raw_stack) if part.strip()]
    if parts:
        return parts[:12]
    return interview_stack or ["TypeScript", "Node.js"]


def _text_to_items(text: str) -> list[str]:
    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip(" -\t")]
    if len(lines) >= 2:
        return lines

    sentence_parts = re.split(r"(?<=[.!?])\s+|;\s+", text.strip())
    items = [part.strip() for part in sentence_parts if len(part.strip()) >= 8]
    if len(items) >= 2:
        return items
    return [text.strip(), "Candidate validates the behavior with the supplied project checks."]


def _fallback_fastapi_project() -> dict[str, object]:
    return {
        "scenario": {
            "title": "Fix order totals and add status filtering",
            "business_context": (
                "The customer success team uses an internal order review API before renewal calls. Account managers "
                "noticed that high-quantity orders are underreported, and they need to filter orders by fulfillment "
                "status before exporting account notes."
            ),
            "candidate_task_summary": (
                "Fix the order total calculation bug and add a status filter to the orders endpoint."
            ),
            "bug_description": (
                "The order total calculation ignores item quantity, so multi-unit line items are undercounted."
            ),
            "feature_request": (
                "Add an optional status query parameter to the orders endpoint and return only matching orders."
            ),
            "expected_behavior": (
                "Order totals multiply unit price by quantity for every item. "
                "GET /orders?status=paid returns only paid orders. "
                "Unknown statuses return an empty list without failing the request."
            ),
            "validation_instructions": (
                "Use the Run button in the workspace to execute the pre-provisioned checks against the current files "
                "and seed data. Confirm the order total calculation and status filtering checks pass before submitting."
            ),
            "candidate_instructions": (
                "You may use the AI copilot, but validate its suggestions against the tests. Keep the change scoped, "
                "update the API behavior, and explain the root cause plus verification steps in your submission."
            ),
            "hidden_rubric": (
                "Candidate fixes the bug in app/services/orders.py rather than only changing tests. "
                "Candidate implements status filtering in the API path without hardcoding paid orders. "
                "Candidate preserves the existing response shape and uses the JSON seed data. "
                "Candidate documents verification and edge cases clearly."
            ),
        },
        "project": {
            "project_name": "orders-review-api",
            "stack": "Python + FastAPI",
            "framework": "FastAPI",
            "package_manager": "pip",
            "install_command": "pip install -r requirements.txt",
            "run_command": "uvicorn app.main:app --reload",
            "test_command": "pytest",
            "entrypoint": "app/main.py",
        },
        "files": [
            {
                "path": "app/main.py",
                "language": "python",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
                "content": (
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
            },
            {
                "path": "app/services/orders.py",
                "language": "python",
                "file_type": "source",
                "is_editable": True,
                "is_hidden": False,
                "content": (
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
            },
            {
                "path": "app/data/orders.json",
                "language": "json",
                "file_type": "data",
                "is_editable": True,
                "is_hidden": False,
                "content": (
                    "[\n"
                    "  {\n"
                    "    \"id\": \"ord_1001\",\n"
                    "    \"customer\": \"Acme Manufacturing\",\n"
                    "    \"status\": \"paid\",\n"
                    "    \"items\": [\n"
                    "      {\"sku\": \"seat-pro\", \"quantity\": 3, \"unit_price\": 49.0},\n"
                    "      {\"sku\": \"onboarding\", \"quantity\": 1, \"unit_price\": 199.0}\n"
                    "    ]\n"
                    "  },\n"
                    "  {\n"
                    "    \"id\": \"ord_1002\",\n"
                    "    \"customer\": \"Northwind Health\",\n"
                    "    \"status\": \"pending\",\n"
                    "    \"items\": [\n"
                    "      {\"sku\": \"seat-team\", \"quantity\": 2, \"unit_price\": 29.0}\n"
                    "    ]\n"
                    "  }\n"
                    "]\n"
                ),
            },
            {
                "path": "tests/test_orders.py",
                "language": "python",
                "file_type": "test",
                "is_editable": True,
                "is_hidden": False,
                "content": (
                    "from fastapi.testclient import TestClient\n\n"
                    "from app.main import app\n"
                    "from app.services.orders import calculate_order_total\n\n"
                    "client = TestClient(app)\n\n\n"
                    "def test_order_total_uses_quantity() -> None:\n"
                    "    order = {\n"
                    "        \"items\": [\n"
                    "            {\"sku\": \"seat-pro\", \"quantity\": 3, \"unit_price\": 49.0},\n"
                    "            {\"sku\": \"onboarding\", \"quantity\": 1, \"unit_price\": 199.0},\n"
                    "        ]\n"
                    "    }\n"
                    "    assert calculate_order_total(order) == 346.0\n\n\n"
                    "def test_orders_can_be_filtered_by_status() -> None:\n"
                    "    response = client.get(\"/orders?status=paid\")\n"
                    "    assert response.status_code == 200\n"
                    "    orders = response.json()\n"
                    "    assert orders\n"
                    "    assert {order[\"status\"] for order in orders} == {\"paid\"}\n"
                ),
            },
            {
                "path": "tests/test_orders_hidden.py",
                "language": "python",
                "file_type": "hidden_test",
                "is_editable": False,
                "is_hidden": True,
                "content": (
                    "from app.services.orders import calculate_order_total\n\n\n"
                    "def test_zero_quantity_items_do_not_inflate_totals() -> None:\n"
                    "    order = {\"items\": [{\"sku\": \"trial\", \"quantity\": 0, \"unit_price\": 99.0}]}\n"
                    "    assert calculate_order_total(order) == 0.0\n"
                ),
            },
            {
                "path": "requirements.txt",
                "language": "text",
                "file_type": "config",
                "is_editable": True,
                "is_hidden": False,
                "content": "fastapi==0.115.6\nuvicorn==0.34.0\npytest==8.2.2\nhttpx==0.27.2\n",
            },
            {
                "path": "README.md",
                "language": "markdown",
                "file_type": "docs",
                "is_editable": True,
                "is_hidden": False,
                "content": (
                    "# Orders Review API\n\n"
                    "## Task\n\n"
                    "Fix the incorrect order total calculation and add an optional status filter to `GET /orders`.\n\n"
                    "## Workspace checks\n\n"
                    "The interview environment is already provisioned. Use the Nexterview Run button to execute "
                    "the visible checks against the current files and seed data.\n\n"
                    "The intentional bug is in `app/services/orders.py`: quantity is ignored when calculating totals.\n"
                ),
            },
        ],
    }

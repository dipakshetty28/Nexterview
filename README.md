# Nexterview

Nexterview is the foundation for an AI-native engineering interview platform. This increment includes real email/password authentication, organization membership, JWT access tokens, bcrypt password hashing, role-based access control, interviewer interview management, backend-only AI scenario generation and copilot responses, candidate invite/session access, a candidate multi-file interview workspace with telemetry, optional GitHub starter-branch creation on scenario generation, and candidate-specific GitHub branch/PR creation on final submission.

## Current Scope

- FastAPI backend with SQLAlchemy 2, Alembic, Pydantic v2, and PostgreSQL
- Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts, react-resizable-panels, and App Router frontend
- Docker Compose for PostgreSQL, Redis, backend, and frontend
- Health endpoint at `GET /api/health`
- Auth endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
- Protected backend routes:
  - `GET /api/dashboard`
  - `GET /api/admin/users` for `ADMIN` users
- Interview management endpoints for `ADMIN` and `INTERVIEWER` users:
  - `POST /api/interviews`
  - `GET /api/interviews`
  - `GET /api/interviews/{id}`
  - `GET /api/interviews/{id}/submissions`
  - `DELETE /api/interviews/{id}`
  - `POST /api/interviews/{id}/invite`
  - `POST /api/interviews/{id}/generate-scenario`
- Internal repo-review endpoints for `ADMIN` and `INTERVIEWER` users:
  - `POST /api/submissions/{id}/review`
  - `GET /api/submissions/{id}/reviews`
  - `GET /api/results`
  - `GET /api/results/{session_id}`
- Candidate invite/session endpoints:
  - `GET /api/invite/{token}`
  - `POST /api/invite/{token}/start`
  - `GET /api/sessions/{id}`
  - `GET /api/sessions/{id}/workspace`
  - `PUT /api/sessions/{id}/files/{file_id}`
  - `POST /api/sessions/{id}/events`
  - `POST /api/sessions/{id}/ai`
  - `POST /api/sessions/{id}/run-tests`
  - `POST /api/sessions/{id}/submit`
- Users, organizations, and organization memberships
- Interviews, invite tokens, interview sessions, stored generated scenarios, scenario projects, project files, session file snapshots, telemetry events, AI messages, submissions with file-level diffs, internal agent reviews, and persisted weighted scores
- OpenAI Responses API integration on the backend with strict Pydantic JSON validation for generated repo projects
- Graceful deterministic scenario and copilot fallbacks when `OPENAI_API_KEY` is missing or generation fails
- Roles: `ADMIN`, `INTERVIEWER`, `CANDIDATE`
- Frontend login, register, auth state, protected dashboard route, interviewer management route, interviewer results dashboard with Recharts score/status visualizations, invite page, repo submission result page, and a resizable Monaco-powered candidate IDE workspace with task, editor, AI copilot, file tree, output, required final explanation, snapshot autosave, pass/fail run output, and final submit confirmation
- Optional GitHub publishing that creates a starter branch from the configured default branch when a scenario is generated, then creates a candidate-specific submission branch and pull request against that starter branch so reviewers see only candidate changes
- Structured AI copilot responses with markdown answers, suggested file chips, confidence, risk flags, and telemetry for later prompting-skill analytics
- Repo-aware multi-agent review that evaluates original project files, submitted files, generated diffs, AI transcript, telemetry, test outputs, candidate notes, and GitHub branch/PR links while allowing internal-only rubric context
- V1 post-submit review scheduling uses FastAPI background tasks; Redis-backed RQ/Celery remains a future production hardening step
- Seed script with demo users and a sample generated interview scenario

## Architecture

```text
frontend/   Next.js App Router UI and auth state
backend/    FastAPI API, SQLAlchemy models, Alembic migrations, tests
postgres    Primary relational database
redis       Local Redis service reserved for future queues/session events
```

## Environment

Copy the example files before running locally:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Backend variables:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nexterview
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_REQUEST_TIMEOUT_SECONDS=30
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
BCRYPT_ROUNDS=12
FRONTEND_URL=http://localhost:3000
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ORIGINS=
ENVIRONMENT=development
GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_DEFAULT_BRANCH=main
GITHUB_CREATE_PR=false
```

Frontend variables:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Do not use `change-me` secrets outside local development. `OPENAI_API_KEY` is read only by the backend; never add it to `frontend/.env` or expose it through `NEXT_PUBLIC_*` variables.

`BACKEND_CORS_ORIGINS` is the production-ready CORS allowlist. Keep local browser origins in it for development, and set deployed frontend origins explicitly in production.

GitHub publishing is optional. Leave `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPO` empty to store generated projects and submitted files only in PostgreSQL. To enable GitHub publishing, set those values on the backend. When a scenario is generated, Nexterview creates a starter branch from `GITHUB_DEFAULT_BRANCH` containing the generated repo project files, including hidden validation files for reviewer context. When a candidate submits, Nexterview creates a candidate-specific branch from the starter branch, commits changed visible workspace files, and creates a pull request back to the starter branch so the PR diff isolates candidate changes. Candidate branches include a sanitized candidate email slug plus interview/session identifiers. The token should have access to the configured repository and permission to read repository contents, create branches, write contents, and create pull requests. `GITHUB_CREATE_PR=true` still enables pull requests for legacy fallback submissions when no starter branch exists. The token is read only by the backend and must never be exposed through frontend environment variables.

## Local Setup

Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

Run the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Windows Command Prompt quick start:

```cmd
cd C:\Users\dipak\OneDrive\Documents\Nexterview
docker compose up -d postgres redis
cd backend
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nexterview
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m scripts.seed
.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second Command Prompt window:

```cmd
cd C:\Users\dipak\OneDrive\Documents\Nexterview\frontend
npm install
set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Service URLs:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health: http://localhost:8000/api/health
- OpenAPI: http://localhost:8000/docs

## Docker Setup

```bash
docker compose up --build
```

The backend container runs Alembic migrations before starting Uvicorn.

To seed demo users in Docker:

```bash
docker compose exec backend python scripts/seed.py
```

## Demo Credentials

All seeded users use this password:

```text
Nexterview123!
```

Accounts:

- `admin@nexterview.dev` with `ADMIN`
- `interviewer@nexterview.dev` with `INTERVIEWER`
- `candidate@nexterview.dev` with `CANDIDATE`

Demo invite flow:

1. Log in as `admin@nexterview.dev` or `interviewer@nexterview.dev`.
2. Open `/interviews`, generate a scenario, open the interview detail page, enter `candidate@nexterview.dev`, and generate an invite link.
3. Open the invite link, log in as `candidate@nexterview.dev`, and start the interview.
4. The candidate lands on `/sessions/{id}` with task context, a nested project file tree, Monaco editor, notes, timer, AI copilot, test simulation, autosave, and final submit.

## API Contracts

Register an organization owner:

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "owner@example.com",
  "password": "StrongPass123!",
  "full_name": "Example Owner",
  "organization_name": "Example Org"
}
```

Login:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "owner@example.com",
  "password": "StrongPass123!"
}
```

Current user:

```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

The auth response includes `access_token`, `token_type`, and the authenticated user with organization memberships.

Create an interview:

```http
POST /api/interviews
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "role_title": "Backend Platform Engineer",
  "seniority": "Senior",
  "stack": ["Python", "FastAPI", "PostgreSQL", "Redis"],
  "difficulty": "Intermediate",
  "interview_type": "Backend debugging",
  "duration_minutes": 75,
  "allowed_ai_mode": "Pair Programmer Mode",
  "evaluation_criteria": [
    "Correctness and edge-case handling",
    "Debugging process and verification discipline",
    "AI collaboration quality and ability to validate suggestions"
  ]
}
```

Generate and store a scenario:

```http
POST /api/interviews/{id}/generate-scenario
Authorization: Bearer <access_token>
```

The response includes:

- `title`
- `business_context`
- `technical_requirements`
- `starter_code`
- `expected_behavior`
- `logs_or_bug_report`
- `bug_description`
- `feature_request`
- `validation_instructions`
- `candidate_task_summary`
- `hidden_evaluation_points`
- `hidden_rubric`
- `candidate_instructions`
- `interviewer_rubric`
- optional `project` metadata with stack, commands, entrypoint, package manager, framework, and generated files

The AI generation response must be strict JSON shaped as `{ "scenario": ..., "project": ..., "files": [...] }`. The backend validates that payload with Pydantic, requires 5 to 12 files, requires a JSON seed data file, requires a test or validation file, and requires `README.md` or `TASK.md`. Supported generation targets are React + Next.js, Python + FastAPI, and Node.js + Express; unknown stacks fall back to a generic TypeScript/Node prompt.

The generated scenario is stored in PostgreSQL and linked one-to-one with the interview. Generated repo projects are stored as `scenario_projects` and `project_files`. If GitHub publishing is configured, scenario generation also creates a starter branch from `GITHUB_DEFAULT_BRANCH` and stores `starter_branch_name`, `starter_commit_sha`, `starter_repository_url`, `starter_push_status`, and `starter_push_error` on `scenario_projects`. Scenario generation still succeeds when GitHub is not configured or publishing fails. When a candidate starts an interview, the backend creates idempotent `session_file_snapshots` from those project files so future multi-file editing can track candidate changes per session. If the OpenAI key is absent or the provider call fails, the backend returns and stores a deterministic FastAPI orders project with an intentional quantity-calculation bug and a status-filter feature request.

Read candidate submission results for an interview:

```http
GET /api/interviews/{id}/submissions
Authorization: Bearer <interviewer_access_token>
```

The response includes each candidate session status plus final submission metadata when available: `branch_name`, `base_branch_name`, `commit_sha`, `repository_url`, `pull_request_url`, `push_status`, and `push_error`. This endpoint is for `ADMIN` and `INTERVIEWER` users in the interview organization.

Run internal review agents for a submitted repo:

```http
POST /api/submissions/{submission_id}/review
Authorization: Bearer <interviewer_access_token>
```

The review context includes the scenario, candidate instructions, bug description, feature request, validation instructions, original project files, submitted files, file-level diffs, AI chat transcript, telemetry events, test run outputs, candidate notes/root cause summary, and GitHub starter/submission branch or PR links when available. Internal review agents may use `hidden_rubric`, `hidden_evaluation_points`, and `interviewer_rubric`; the candidate-facing copilot never receives those fields.

Candidate submission automatically schedules the same internal review flow after the final solution is saved. The manual `POST /api/submissions/{submission_id}/review` endpoint remains available and idempotent for retries or older submissions. V1 uses FastAPI background tasks rather than RQ/Celery so local demos do not require worker processes; production queue hardening is still future work.

Read review results:

```http
GET /api/results
Authorization: Bearer <interviewer_access_token>

GET /api/submissions/{submission_id}/reviews
Authorization: Bearer <interviewer_access_token>

GET /api/results/{session_id}
Authorization: Bearer <interviewer_access_token>
```

`GET /api/results` returns an organization-scoped interviewer dashboard list of interview sessions with candidate info, status, submitted/reviewed timestamps, final score, recommendation, GitHub PR status, and flattened risk flags. `GET /api/results/{session_id}` returns the result detail payload with changed files, submitted code files, unified diffs, GitHub push metadata including the submission branch and PR base branch, agent reviews, weighted score breakdown, AI chat transcript, telemetry timeline, prompt quality summary, AI usage analysis, submitted test output, candidate notes, and cross-agent risk flags. The backend stores the final weighted result in the `scores` table. The weighted score uses the current rubric weights: Code Quality 15%, Correctness 20%, Architecture 15%, Debugging 15%, AI Usage 15%, Prompting Skill 10%, and Communication 10%. Security and Performance agents report risks but are not separate weighted categories.

Candidates cannot access review endpoints or the interviewer results dashboard unless a future explicit sharing flow is added.

Delete an interview:

```http
DELETE /api/interviews/{id}
Authorization: Bearer <interviewer_access_token>
```

Deleting an interview cascades through its generated scenario, project files, invite tokens, candidate sessions, workspace snapshots, telemetry, AI messages, and submissions.

Generate a candidate invite link:

```http
POST /api/interviews/{id}/invite
Authorization: Bearer <interviewer_access_token>
Content-Type: application/json

{
  "candidate_email": "candidate@example.com",
  "expires_in_days": 14
}
```

The candidate must already have an active `CANDIDATE` account in the interview organization. The response includes `invite_url`, `session_id`, and expiration metadata.

Open an invite:

```http
GET /api/invite/{token}
```

Start a session from an invite:

```http
POST /api/invite/{token}/start
Authorization: Bearer <candidate_access_token>
```

Read a candidate session:

```http
GET /api/sessions/{id}
Authorization: Bearer <candidate_access_token>
```

The session response includes the candidate-safe task scenario, visible generated project files, `latest_code`, `notes`, `last_autosaved_at`, `ai_messages`, and the final `submission` when one exists. Candidate endpoints do not include hidden rubrics, hidden evaluation points, interviewer rubrics, hidden project files, or local install/run/test commands; candidates see a pre-provisioned workspace and use the platform Run button for pass/fail checks.

Read the candidate workspace:

```http
GET /api/sessions/{id}/workspace
Authorization: Bearer <candidate_access_token>
```

The workspace response includes project metadata and visible `session_file_snapshots`. File IDs in this response are session snapshot IDs, not immutable `project_files` IDs. Candidate edits update snapshots only; original generated project files remain unchanged. Internal runner commands remain backend-owned metadata and are returned as `null` in candidate workspace payloads.

Autosave a workspace file:

```http
PUT /api/sessions/{id}/files/{file_id}
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "content": "from fastapi import FastAPI\n\napp = FastAPI()\n"
}
```

The backend rejects hidden files, read-only files, and submitted sessions. Successful saves update `session_file_snapshots.current_content`, refresh `last_autosaved_at`, and record `file_edited` plus `file_saved` telemetry.

Save a candidate room event:

```http
POST /api/sessions/{id}/events
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "event_type": "code_edit",
  "payload": {
    "code": "def handle_webhook(event):\n    return event\n"
  }
}
```

Supported telemetry event types are `session_started`, `code_edit`, `file_opened`, `file_edited`, `file_saved`, `note_updated`, `test_run`, `ai_prompt_sent`, and `submission_created`. `code_edit` autosaves legacy single-file code; workspace file saves use the dedicated file endpoint. `note_updated` autosaves the root cause notes. `test_run`, `ai_prompt_sent`, and `submission_created` are created through their dedicated endpoints.

Ask the candidate AI copilot:

```http
POST /api/sessions/{id}/ai
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "question": "Can you help me make retries idempotent?",
  "current_file_path": "app/services/orders.py",
  "current_file_content": "def calculate_order_total(order):\n    return sum(item['unit_price'] for item in order['items'])\n",
  "latest_test_output": "5/7 workspace checks passed using `app/data/orders.json`.",
  "notes": "Quantity handling looks suspicious."
}
```

The copilot receives only candidate-safe context: scenario title, business context, candidate instructions, visible bug and feature request, validation instructions, visible project file tree, currently open file path/content, latest saved visible workspace files, previous AI messages, the candidate question, latest test output, and candidate notes/root cause summary. It never receives hidden rubrics, hidden evaluation points, hidden tests, or interviewer-only notes.

Copilot responses are stored in `ai_messages`. Assistant message `content` contains the markdown answer, and `message_metadata` stores `suggested_files`, `risk_flags`, `confidence`, and provider source. The API response also includes a structured `response` object:

```json
{
  "answer": "Markdown answer with code when useful.",
  "suggested_files": [{"path": "app/services/orders.py", "reason": "Likely source of the quantity bug."}],
  "risk_flags": ["Verify status filtering before submitting."],
  "confidence": "medium"
}
```

The backend records `ai_prompt_sent` telemetry with prompt text, included context size, current file path, AI mode, response confidence, and timestamp. The OpenAI key stays backend-only; the frontend only calls Nexterview's API.

Run the workspace checks:

```http
POST /api/sessions/{id}/run-tests
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "code": "def handle_webhook(event):\n    return event\n"
}
```

For multi-file sessions, omit `code` or send `{}`. The backend runs deterministic pass/fail workspace checks against the current visible workspace snapshots, changed files, bug/feature signals, validation files, and generated seed data. The candidate experience treats dependencies as already installed in the interview environment.

Submit the final solution:

```http
POST /api/sessions/{id}/submit
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "notes": "Root cause and verification summary.",
  "test_output": "7/7 workspace checks passed using `app/data/orders.json`."
}
```

For multi-file sessions, `code` and `submitted_files` are optional. If `submitted_files` is omitted and the session has file snapshots, the backend stores the current visible session snapshots as the submission. Single-file clients can continue sending `code`. When GitHub is configured and the generated scenario has a pushed starter branch, the backend creates a candidate branch named `candidate-{candidate_slug}-interview-{interview_id_short}-session-{session_id_short}-{timestamp}`, commits changed visible workspace files on top of the starter branch, pushes the branch, and creates a pull request against the starter branch. If the starter branch is unavailable, the submission still falls back to the configured default branch behavior and only creates a fallback PR when `GITHUB_CREATE_PR=true`. If GitHub is disabled or the push fails, the submission still succeeds and stores submitted files in PostgreSQL with `push_status` and a safe `push_error` when applicable. Hidden files, unsafe paths, environment files, and private key material are not committed from candidate submissions.

Final submissions also store generated file-level diffs. After the submission is saved, Nexterview schedules the internal multi-agent review, stores per-agent records in `agent_reviews`, and stores the final weighted score in `scores`. Interviewers can open `/results/{session_id}` from the interview detail page, inspect changed files and diffs, review AI usage analysis, rerun the review if needed, and see the weighted score breakdown plus hiring recommendation.

Candidate session statuses are `invited`, `started`, `submitted`, and `reviewed`. Candidates can only access sessions where they are the session owner. Submitted or reviewed sessions no longer accept code edits, note updates, test runs, or duplicate final submissions.

## Verification

Backend syntax check:

```bash
cd backend
python -m compileall app scripts tests
```

Backend tests require PostgreSQL and do not use SQLite:

```bash
createdb nexterview_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/nexterview_test pytest
```

Frontend type check and production build:

```bash
cd frontend
npm run typecheck
npm run build
```

Health check:

```bash
curl http://localhost:8000/api/health
```

CORS preflight check from Windows Command Prompt:

```cmd
curl -i -X OPTIONS http://localhost:8000/api/interviews ^
  -H "Origin: http://localhost:3000" ^
  -H "Access-Control-Request-Method: GET" ^
  -H "Access-Control-Request-Headers: authorization,content-type"
```

The response should include:

```text
access-control-allow-origin: http://localhost:3000
access-control-allow-credentials: true
```

Auth smoke test:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nexterview.dev","password":"Nexterview123!"}'
```

Interview scenario smoke test:

```bash
curl -X POST http://localhost:8000/api/interviews/<interview_id>/generate-scenario \
  -H "Authorization: Bearer <access_token>"
```

Interview delete smoke test:

```bash
curl -X DELETE http://localhost:8000/api/interviews/<interview_id> \
  -H "Authorization: Bearer <interviewer_access_token>"
```

Candidate invite smoke test:

```bash
curl -X POST http://localhost:8000/api/interviews/<interview_id>/invite \
  -H "Authorization: Bearer <interviewer_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"candidate_email":"candidate@nexterview.dev"}'
```

Candidate room smoke test:

```bash
curl http://localhost:8000/api/sessions/<session_id>/workspace \
  -H "Authorization: Bearer <candidate_access_token>"

curl -X PUT http://localhost:8000/api/sessions/<session_id>/files/<workspace_file_id> \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"# updated candidate snapshot\n"}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/events \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"file_opened","payload":{"file_id":"<workspace_file_id>","path":"app/main.py"}}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/run-tests \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/ai \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"Can you suggest a safe implementation approach?","code":"def handle_webhook(event):\n    return event\n"}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/submit \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Root cause and verification summary.","test_output":"Simulation completed."}'
```

Repo review smoke test:

```bash
curl -X POST http://localhost:8000/api/submissions/<submission_id>/review \
  -H "Authorization: Bearer <interviewer_access_token>"

curl http://localhost:8000/api/results/<session_id> \
  -H "Authorization: Bearer <interviewer_access_token>"
```

## Deployment Notes

Frontend on Vercel:

```bash
cd frontend
vercel
vercel env add NEXT_PUBLIC_API_BASE_URL
vercel --prod
```

Backend on Render:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Provision PostgreSQL with Render Postgres or Neon and set `DATABASE_URL`. Provision Redis with Render Redis or Upstash and set `REDIS_URL`. Set `JWT_SECRET` to a long random value in the deployment environment.

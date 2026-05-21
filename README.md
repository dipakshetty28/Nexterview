# Nexterview

Nexterview is the foundation for an AI-native engineering interview platform. This increment includes real email/password authentication, organization membership, JWT access tokens, bcrypt password hashing, role-based access control, interviewer interview management, backend-only AI scenario generation, candidate invite/session access, and a candidate interview room with telemetry.

## Current Scope

- FastAPI backend with SQLAlchemy 2, Alembic, Pydantic v2, and PostgreSQL
- Next.js 15, React 19, TypeScript, Tailwind CSS, and App Router frontend
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
  - `POST /api/interviews/{id}/invite`
  - `POST /api/interviews/{id}/generate-scenario`
- Candidate invite/session endpoints:
  - `GET /api/invite/{token}`
  - `POST /api/invite/{token}/start`
  - `GET /api/sessions/{id}`
  - `POST /api/sessions/{id}/events`
  - `POST /api/sessions/{id}/run-tests`
  - `POST /api/sessions/{id}/submit`
- Users, organizations, and organization memberships
- Interviews, invite tokens, interview sessions, stored generated scenarios, telemetry events, and submissions
- OpenAI Responses API integration on the backend with Pydantic structured output validation
- Graceful deterministic scenario fallback when `OPENAI_API_KEY` is missing or generation fails
- Roles: `ADMIN`, `INTERVIEWER`, `CANDIDATE`
- Frontend login, register, auth state, protected dashboard route, interviewer management route, invite page, and Monaco-powered candidate interview room
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
```

Frontend variables:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Do not use `change-me` secrets outside local development. `OPENAI_API_KEY` is read only by the backend; never add it to `frontend/.env` or expose it through `NEXT_PUBLIC_*` variables.

`BACKEND_CORS_ORIGINS` is the production-ready CORS allowlist. Keep local browser origins in it for development, and set deployed frontend origins explicitly in production.

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
2. Open `/interviews`, enter `candidate@nexterview.dev`, and generate an invite link.
3. Open the invite link, log in as `candidate@nexterview.dev`, and start the interview.
4. The candidate lands on `/sessions/{id}` with task context, a Monaco editor, notes, timer, AI copilot placeholder, test simulation, autosave, and final submit.

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
- `hidden_evaluation_points`
- `candidate_instructions`
- `interviewer_rubric`

The generated scenario is stored in PostgreSQL and linked one-to-one with the interview. If the OpenAI key is absent or the provider call fails, the backend returns and stores a realistic deterministic fallback scenario with `generation_source` set to `fallback`.

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

The session response includes the candidate-safe task scenario, `latest_code`, `notes`, `last_autosaved_at`, and the final `submission` when one exists.

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

Supported telemetry event types are `session_started`, `code_edit`, `note_updated`, `test_run`, and `submission_created`. `code_edit` autosaves `latest_code`; `note_updated` autosaves the root cause notes. `test_run` and `submission_created` are created through their dedicated endpoints.

Run the deterministic test simulation:

```http
POST /api/sessions/{id}/run-tests
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "code": "def handle_webhook(event):\n    return event\n"
}
```

Submit the final solution:

```http
POST /api/sessions/{id}/submit
Authorization: Bearer <candidate_access_token>
Content-Type: application/json

{
  "code": "def handle_webhook(event):\n    return event\n",
  "notes": "Root cause and verification summary.",
  "test_output": "4/4 simulated checks passed."
}
```

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

Candidate invite smoke test:

```bash
curl -X POST http://localhost:8000/api/interviews/<interview_id>/invite \
  -H "Authorization: Bearer <interviewer_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"candidate_email":"candidate@nexterview.dev"}'
```

Candidate room smoke test:

```bash
curl -X POST http://localhost:8000/api/sessions/<session_id>/events \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"code_edit","payload":{"code":"def handle_webhook(event):\n    return event\n"}}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/run-tests \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"def handle_webhook(event):\n    return event\n"}'

curl -X POST http://localhost:8000/api/sessions/<session_id>/submit \
  -H "Authorization: Bearer <candidate_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code":"def handle_webhook(event):\n    return event\n","notes":"Root cause and verification summary.","test_output":"Simulation completed."}'
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

# Nexterview

Nexterview is the foundation for an AI-native engineering interview platform. It now includes authenticated organization access plus interviewer interview management for manually authored scenarios.

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
  - `GET /api/interviews` for `ADMIN` and `INTERVIEWER` users
- Users, organizations, and organization memberships
- Interviews, scenarios, and interview sessions
- Roles: `ADMIN`, `INTERVIEWER`, `CANDIDATE`
- Frontend login, register, auth state, protected dashboard, create interview, and interview detail routes
- Seed script with demo users and a sample interview

## Architecture

```text
frontend/   Next.js App Router UI and auth state
backend/    FastAPI API, SQLAlchemy models, Alembic migrations, seed scripts, tests
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
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
BCRYPT_ROUNDS=12
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

Frontend variables:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Do not use `change-me` secrets outside local development.

## Local Setup

Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

When running backend commands from a local virtual environment, use `localhost` in `DATABASE_URL`. Docker-only service names such as `postgres` resolve only inside Compose containers.

Run the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Run the frontend:

```bash
cd frontend
npm install
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
docker compose exec backend python -m scripts.seed
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

List interviews visible to the current interviewer/admin:

```http
GET /api/interviews
Authorization: Bearer <access_token>
```

Create an interview with a manually authored scenario:

```http
POST /api/interviews
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "Backend Debugging Loop",
  "role_title": "Senior Backend Engineer",
  "seniority": "SENIOR",
  "stack": ["Python", "FastAPI", "PostgreSQL"],
  "interview_type": "BACKEND_DEBUGGING",
  "difficulty": "HARD",
  "duration_minutes": 75,
  "ai_mode": "DEBUGGING_ASSISTANT",
  "scenario": {
    "title": "Retry loop creates duplicate payments",
    "business_context": "A payment service creates duplicate transactions when processor timeouts happen during retries.",
    "candidate_instructions": "Find the root cause, explain the failure mode, and propose a safe fix.",
    "technical_requirements": "Preserve idempotency keys across retries and prevent duplicate transaction records.",
    "evaluation_rubric": "Assess root-cause analysis, verification discipline, safeguards, and communication."
  }
}
```

Interview management endpoints:

- `GET /api/interviews`
- `POST /api/interviews`
- `GET /api/interviews/{id}`
- `PATCH /api/interviews/{id}`
- `DELETE /api/interviews/{id}`

Interviews are always scoped to the authenticated user's organization memberships. Candidates cannot use interviewer management endpoints.

## Verification

Backend syntax check:

```bash
cd backend
python -m compileall app scripts tests
```

Backend tests require PostgreSQL and do not use SQLite:

```bash
docker exec nexterview-postgres-1 createdb -U postgres nexterview_test
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

Auth smoke test:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nexterview.dev","password":"Nexterview123!"}'
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

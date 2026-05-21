# Project Status

## Product
AI-native engineering interview platform.

Core thesis:
We do not block AI in interviews. We evaluate whether engineers can use AI responsibly, verify its output, debug systems, and demonstrate real engineering judgment.

## Completed
Completed through Step 5 / Codex Prompt 3:
- Repo foundation exists
- FastAPI backend exists
- Next.js frontend exists
- Docker/Postgres/Redis foundation exists
- Auth and role-based access exist
- Organization model exists
- Interviewer dashboard exists
- Create Interview flow exists
- Interview model exists
- Scenario model exists
- InterviewSession model exists
- Interview detail page exists
- Manual scenario creation exists

## Current Phase
Next step is Step 6:
AI-powered scenario generation.

## Important Product Direction
This is not a LeetCode clone.
The platform should evaluate:
- coding ability
- debugging ability
- architecture judgment
- AI usage quality
- prompting skill
- verification discipline
- communication

## Current Users/Roles
- ADMIN
- INTERVIEWER
- CANDIDATE

## Current Tech Stack
Frontend:
- Next.js 15
- React 19
- TypeScript
- Tailwind

Backend:
- FastAPI
- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT auth
- Pydantic v2

Infrastructure:
- Docker Compose
- Postgres
- Redis

## Next Step
Implement AI-powered scenario generation only.

Do not implement candidate interview room yet.
Do not implement AI copilot yet.
Do not implement multi-agent review yet.
Do not redesign existing app.
Do not rewrite the repo.

## Required Step 6 Feature
Add backend + frontend support for generating realistic engineering interview scenarios from interview config.

Scenario generation should use:
- role title
- seniority
- stack
- interview type
- difficulty
- duration
- allowed AI mode

Generated scenario should include:
- title
- business_context
- technical_requirements
- starter_code
- expected_behavior
- logs_or_bug_report
- hidden_evaluation_points
- candidate_instructions
- interviewer_rubric

## AI Requirements
- Use OpenAI from backend only.
- Do not expose API key to frontend.
- Use structured JSON output.
- Validate output with Pydantic.
- Store generated scenario in database.
- Gracefully fallback to seeded/static scenario if OpenAI key is missing.
- Add env vars:
  - OPENAI_API_KEY
  - OPENAI_MODEL

## Quality Rules
- Keep changes small and focused.
- Update migrations if schema changes.
- Update README if setup changes.
- Add tests with mocked AI service.
- Do not use SQLite.
- Do not hardcode secrets.
- Do not break existing auth/interview dashboard.
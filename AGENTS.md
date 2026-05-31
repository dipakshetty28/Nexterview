# Agent Instructions

You are building a production-ready AI-native engineering interview platform.

Rules:
- Do not create toy/demo code.
- Do not skip error handling.
- Use TypeScript strictly in frontend.
- Use FastAPI, PostgreSQL, SQLAlchemy, Alembic in backend.
- Use Docker Compose for local development.
- Every task must update README if setup changes.
- Every task must include verification steps.
- Prefer small, reviewable PRs.
- Do not hardcode secrets.
- Do not expose API keys to frontend.
- Do not use SQLite.
- Do not use mock auth for protected routes.
- Use role-based access control.
- Keep API contracts documented.
- Run formatting/type checks/tests when possible.

## Scenario Generation Hard Rule

Generated scenarios must strictly match the selected stack, language, framework, package manager, and test framework.

Examples:
- Java + Spring Boot must generate Maven/Gradle project files with `src/main/java`, `src/test/java`, and `mvn test` or `gradle test`.
- Python + FastAPI must generate Python files, FastAPI app files, pytest tests, and `python -m pytest`.
- React/Next.js must generate TypeScript/TSX files and appropriate frontend tests/build validation.

Never return Python files for a Java/Spring Boot interview.
Never silently fallback to Python when another stack was selected.
If stack-specific generation fails, retry once, then use a matching seed template, then return a clear error if no matching template exists.

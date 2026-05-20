This file is the source of truth. Build incrementally. Do not implement everything in one PR.

You are a world-class founding engineer, product architect, AI systems architect, DevOps architect, and senior full-stack engineer.

Build a production-ready AI-native technical interview platform.

This is NOT a LeetCode clone.
This is an AI-era engineering evaluation platform where candidates are allowed to use AI, but the platform measures how well they use AI, validate AI output, debug systems, understand architecture, write code, communicate tradeoffs, and solve realistic engineering tasks.

The product must be demo-ready and organization-ready.

PRODUCT NAME:
AI Engineering Interview Platform

CORE THESIS:
Traditional coding interviews are broken in the AI era. This platform evaluates real engineering capability, including coding, debugging, system design, AI collaboration, prompting skill, verification discipline, code quality, architecture judgment, and communication.

PRIMARY USERS:
1. Candidate
2. Interviewer
3. Admin / Organization Owner

CORE WORKFLOW:
1. Organization creates account
2. Interviewer logs in
3. Interviewer creates an interview
4. Interviewer selects:
   - role title
   - stack
   - difficulty
   - interview type
   - duration
   - allowed AI mode
   - evaluation criteria
5. Platform generates realistic engineering task
6. Candidate receives invite link
7. Candidate logs in
8. Candidate enters coding environment
9. Candidate sees:
   - task description
   - code editor
   - terminal / test runner simulation
   - AI copilot chat
   - logs / bug report / requirements
10. Candidate solves task using code and AI copilot
11. Platform records telemetry:
   - code edits
   - AI prompts
   - AI responses
   - time taken
   - test runs
   - failed attempts
   - final submission
12. Candidate submits
13. Multiple AI agents review submission independently
14. Interviewer sees final dashboard:
   - code quality score
   - debugging score
   - architecture score
   - AI usage score
   - prompting skill score
   - verification score
   - security score
   - communication score
   - hire / no-hire recommendation
   - full session replay
   - code diff
   - AI conversation transcript
   - agent reviews

TECH STACK:
Frontend:
- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- Monaco Editor
- React Markdown
- Zustand or React Query
- Recharts for analytics

Backend:
- FastAPI
- Python 3.11+
- PostgreSQL
- SQLAlchemy 2.x
- Alembic migrations
- Pydantic v2
- JWT authentication
- Role-based access control
- OpenAI API integration
- Background jobs using Celery or RQ
- Redis for queues and session events

Infrastructure:
- Docker
- Docker Compose
- Postgres container
- Redis container
- Backend container
- Frontend container
- Production deployment ready
- Render / Railway / Fly.io backend support
- Vercel frontend support
- Environment variable based config
- CORS configured safely
- Health check endpoints
- Logging
- Error handling

DATABASE:
Use PostgreSQL.

Create proper models:
- users
- organizations
- organization_members
- interviews
- interview_sessions
- scenarios
- submissions
- telemetry_events
- ai_messages
- agent_reviews
- scores
- invite_tokens

USER ROLES:
1. ADMIN
   - manage organization
   - manage users
   - see all interviews
2. INTERVIEWER
   - create interviews
   - invite candidates
   - review submissions
3. CANDIDATE
   - access assigned interview only
   - solve tasks
   - use AI copilot
   - submit solution

AUTH REQUIREMENTS:
- Email/password login
- JWT access token
- Secure password hashing using bcrypt
- Protected routes
- Role-based route guards
- Candidate invite token flow
- Logout
- Current user endpoint

INTERVIEW TYPES:
Support at least:
1. Full-stack feature implementation
2. Backend debugging
3. API design
4. Frontend bug fix
5. System design written task
6. AI engineering task
7. Refactoring task
8. Security review task

STACK SELECTION:
Interviewer can select:
- Python + FastAPI
- Node.js + Express
- React + Next.js
- Java + Spring Boot
- C# + .NET
- Go
- PostgreSQL
- Redis
- AWS
- Docker
- Kubernetes
- LangChain / LangGraph / CrewAI
- Generic full-stack

TASK GENERATION:
When interviewer creates an interview, generate a realistic task based on:
- role
- seniority
- stack
- interview type
- difficulty
- duration

Generated task should include:
- title
- business context
- technical requirements
- broken starter code
- expected behavior
- hidden evaluation points
- sample tests
- interviewer rubric
- candidate instructions
- constraints
- logs or bug reports if debugging task

IMPORTANT:
The generated task must feel like real engineering work, not toy LeetCode.

Example task:
"Debug an intermittent payment retry bug where duplicate transactions are created because idempotency keys are generated inside the retry loop."

CANDIDATE ENVIRONMENT:
Candidate page must include:
- task description
- Monaco code editor
- file tabs
- AI copilot side panel
- test run button
- submit button
- notes / root cause summary
- timer
- event tracking

AI COPILOT:
The candidate must have a chatbot on the side.

AI copilot behavior:
- It can provide code
- It can explain concepts
- It can suggest debugging steps
- It can analyze logs
- It can be helpful
- It should not simply solve everything perfectly every time
- It should sometimes give incomplete or questionable suggestions, like real AI tools

Track every candidate prompt and AI response.

AI COPILOT MODES:
Support:
1. Hint Mode
2. Pair Programmer Mode
3. Senior Engineer Mode
4. Debugging Assistant Mode

The interviewer can choose allowed AI mode.

TELEMETRY:
Track:
- session_started
- task_viewed
- code_edit
- ai_prompt_sent
- ai_response_received
- test_run
- test_failed
- test_passed
- note_updated
- submission_created
- tab_switch
- time_spent
- final_submit

Store telemetry in database.

MULTI-AGENT REVIEW SYSTEM:
After submission, run multiple AI review agents.

Agents:

1. Code Quality Agent
Evaluates:
- readability
- maintainability
- naming
- modularity
- simplicity
- duplication
- error handling

2. Correctness Agent
Evaluates:
- whether requirements are met
- logic correctness
- edge cases
- broken assumptions
- test coverage

3. Architecture Agent
Evaluates:
- design choices
- separation of concerns
- scalability
- extensibility
- tradeoffs
- system boundaries

4. Security Agent
Evaluates:
- injection risks
- auth issues
- unsafe input handling
- secrets exposure
- dependency risks

5. Performance Agent
Evaluates:
- inefficient logic
- database misuse
- unnecessary loops
- caching opportunities
- scalability bottlenecks

6. AI Usage Agent
Evaluates:
- whether candidate used AI productively
- whether candidate blindly copied AI output
- whether candidate validated AI suggestions
- whether prompts were specific and contextual
- whether candidate improved on AI responses

7. Prompting Skill Agent
Evaluates:
- clarity of prompts
- problem decomposition
- context provided
- follow-up quality
- whether candidate asked lazy questions
- whether candidate tried to get final code without understanding

8. Debugging Process Agent
Evaluates:
- root cause analysis
- hypothesis formation
- use of logs
- incremental testing
- ability to isolate issue

9. Communication Agent
Evaluates:
- final explanation
- tradeoff discussion
- root cause summary
- clarity for teammates

10. Hiring Recommendation Agent
Combines all reviews and gives:
- strong hire
- hire
- lean hire
- lean no hire
- no hire
with detailed explanation.

SCORING:
Each agent returns:
- score from 0 to 100
- strengths
- weaknesses
- evidence
- risk flags
- recommendation
- detailed explanation

Final score should include:
- Code Quality: 15%
- Correctness: 20%
- Architecture: 15%
- Debugging: 15%
- AI Usage: 15%
- Prompting Skill: 10%
- Communication: 10%

INTERVIEWER DASHBOARD:
Must include:
- list of interviews
- create interview button
- candidate sessions
- status
- score
- recommendation
- duration
- AI usage summary

INTERVIEW RESULT PAGE:
Show:
- candidate info
- interview info
- final recommendation
- score breakdown
- agent reviews
- submitted code
- code diff if available
- AI chat transcript
- telemetry timeline
- prompt quality analysis
- test results
- final candidate explanation
- risk flags
- interviewer notes

ADMIN DASHBOARD:
Show:
- organization users
- interviews
- usage metrics
- candidates
- settings

UI QUALITY:
Make it look like a serious B2B SaaS product.

Design style:
- dark modern interface
- clean layout
- dashboard cards
- professional sidebar
- charts
- tables
- badges
- score pills
- clean typography
- no toy/demo feel

PAGES REQUIRED:
Public:
- Landing page
- Pricing placeholder
- Login
- Register

Authenticated:
- Dashboard
- Create Interview
- Interview Detail
- Candidate Invite Page
- Candidate Interview Session
- Results Page
- Admin Settings
- User Management

API ENDPOINTS:
Auth:
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me

Organizations:
- GET /api/org
- POST /api/org/members
- GET /api/org/members

Interviews:
- POST /api/interviews
- GET /api/interviews
- GET /api/interviews/{id}
- POST /api/interviews/{id}/invite
- POST /api/interviews/{id}/generate-scenario

Candidate:
- GET /api/invite/{token}
- POST /api/sessions/start
- GET /api/sessions/{id}
- POST /api/sessions/{id}/events
- POST /api/sessions/{id}/ai
- POST /api/sessions/{id}/run-tests
- POST /api/sessions/{id}/submit

Reviews:
- POST /api/submissions/{id}/review
- GET /api/submissions/{id}/reviews
- GET /api/results/{session_id}

AI:
- POST /api/ai/generate-task
- POST /api/ai/copilot
- POST /api/ai/review

SECURITY:
- Never expose API keys to frontend
- Store secrets only in environment variables
- Hash passwords
- Validate role access
- Candidate can access only own session
- Interviewer can access only organization interviews
- Add CORS whitelist
- Add basic rate limiting
- Add input validation

ENVIRONMENT VARIABLES:
Backend:
DATABASE_URL=
REDIS_URL=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
JWT_SECRET=
FRONTEND_URL=
CORS_ORIGINS=
ENVIRONMENT=development

Frontend:
NEXT_PUBLIC_API_BASE_URL=

DOCKER:
Create:
- docker-compose.yml
- frontend/Dockerfile
- backend/Dockerfile

Docker Compose should start:
- postgres
- redis
- backend
- frontend

MIGRATIONS:
Use Alembic.
Include initial migration for all tables.

SEED DATA:
Add seed script:
- creates admin user
- creates sample organization
- creates sample interviewer
- creates sample candidate
- creates sample interview
- creates sample completed session with reviews

TESTING:
Add basic tests:
- backend auth test
- interview creation test
- candidate session test
- submission review test

README:
Create a professional README with:
- product overview
- architecture
- features
- local setup
- environment variables
- Docker setup
- deployment steps
- demo credentials
- screenshots placeholder
- roadmap

DEPLOYMENT:
Add deployment instructions for:
Frontend:
- Vercel

Backend:
- Render or Railway

Database:
- Render Postgres or Neon

Redis:
- Upstash or Render Redis

Must include exact commands.

PRODUCTION READINESS:
Add:
- health endpoint
- structured logging
- error handling
- loading states
- empty states
- protected routes
- graceful failed AI response handling
- graceful DB connection handling
- clear setup instructions

IMPORTANT PRODUCT BEHAVIOR:
Do not block AI usage.
The platform should treat AI usage as a signal.
Bad AI usage should reduce score.
Good AI usage should increase score.

AI USAGE SCORING EXAMPLES:
High score:
- candidate gives AI logs, code context, hypothesis
- asks AI to compare alternatives
- validates AI answer
- writes tests
- explains why fix works

Low score:
- candidate asks "give me final code"
- copies code without testing
- cannot explain solution
- ignores failed tests
- repeatedly asks vague questions

PROMPT QUALITY SCORING:
Evaluate candidate prompts based on:
- specificity
- context
- debugging reasoning
- constraints
- follow-up quality
- independence
- verification behavior

REALISTIC TASK EXAMPLES:
Include at least 5 seed scenarios:

1. Backend Debugging:
Duplicate payment creation due to retry/idempotency bug.

2. Full-stack Feature:
Add candidate feedback form with validation, API, database model, and UI.

3. React Bug:
Hydration error caused by browser-only logic rendering on server.

4. AI Engineering:
RAG chatbot returns wrong answer because retrieval chunks lack metadata and ranking.

5. API Performance:
Endpoint is slow due to N+1 database query and missing pagination.

DELIVERABLE:
Generate the complete production-ready repository.

Output:
- full folder structure
- all code files
- backend code
- frontend code
- database models
- migrations
- Docker setup
- README
- deployment guide
- seed data
- sample scenarios
- working UI
- working API

Do not give pseudo-code.
Do not give partial snippets.
Do not skip files.
Do not simplify into a toy app.
Build it like a real startup MVP that can be demoed to organizations.

QUALITY BAR:
The product should be impressive enough to demo tomorrow to:
- hiring manager
- CTO
- startup founder
- investor
- engineering director

FINAL REQUIREMENT:
After generating the product, explain:
1. how to run locally
2. how to deploy
3. demo login credentials
4. what to show in demo
5. next 10 features to build
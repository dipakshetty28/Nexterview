from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.interview import AIMode, Difficulty, Interview, InterviewSession, InterviewSessionStatus, InterviewType, Scenario, Seniority
from app.models.organization import Organization, OrganizationMember
from app.models.user import User, UserRole

DEMO_PASSWORD = "Nexterview123!"


def _get_or_create_organization(db: Session) -> Organization:
    organization = db.execute(select(Organization).where(Organization.slug == "nexterview-demo")).scalar_one_or_none()
    if organization is not None:
        return organization

    organization = Organization(name="Nexterview Demo", slug="nexterview-demo")
    db.add(organization)
    db.flush()
    return organization


def _upsert_user(db: Session, *, email: str, full_name: str, role: UserRole, organization: Organization) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            hashed_password=hash_password(DEMO_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name
        user.role = role
        user.is_active = True
        user.hashed_password = hash_password(DEMO_PASSWORD)

    membership = db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization.id,
            OrganizationMember.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        db.add(OrganizationMember(organization=organization, user=user, role=role))
    else:
        membership.role = role

    return user


def _upsert_demo_interview(db: Session, *, organization: Organization, interviewer: User, candidate: User) -> None:
    interview = db.execute(
        select(Interview).where(
            Interview.organization_id == organization.id,
            Interview.title == "Backend Debugging: Payment Retry Idempotency",
        )
    ).scalar_one_or_none()
    if interview is None:
        interview = Interview(
            organization=organization,
            created_by=interviewer,
            title="Backend Debugging: Payment Retry Idempotency",
            role_title="Senior Backend Engineer",
            seniority=Seniority.SENIOR,
            stack=["Python", "FastAPI", "PostgreSQL", "Redis"],
            interview_type=InterviewType.BACKEND_DEBUGGING,
            difficulty=Difficulty.HARD,
            duration_minutes=75,
            ai_mode=AIMode.DEBUGGING_ASSISTANT,
        )
        db.add(interview)
        db.flush()
    else:
        interview.created_by = interviewer
        interview.role_title = "Senior Backend Engineer"
        interview.seniority = Seniority.SENIOR
        interview.stack = ["Python", "FastAPI", "PostgreSQL", "Redis"]
        interview.interview_type = InterviewType.BACKEND_DEBUGGING
        interview.difficulty = Difficulty.HARD
        interview.duration_minutes = 75
        interview.ai_mode = AIMode.DEBUGGING_ASSISTANT

    scenario = interview.scenarios[0] if interview.scenarios else None
    scenario_payload = {
        "title": "Duplicate payment creation during retries",
        "business_context": (
            "A payment service intermittently creates duplicate transactions when an upstream processor times out. "
            "The issue appears during retry handling and only under partial failure conditions."
        ),
        "candidate_instructions": (
            "Review the retry flow, identify the root cause, explain the failure mode, and propose a safe fix. "
            "You may use AI assistance, but your final answer must include validation steps and tradeoffs."
        ),
        "technical_requirements": (
            "Preserve idempotency across retries, avoid duplicate transaction records, and describe the database or API "
            "constraints needed to prevent recurrence."
        ),
        "evaluation_rubric": (
            "Strong answers isolate idempotency key generation, validate behavior with tests, explain concurrency risks, "
            "and describe operational safeguards."
        ),
    }
    if scenario is None:
        db.add(Scenario(interview=interview, created_by=interviewer, **scenario_payload))
    else:
        scenario.created_by = interviewer
        for field_name, value in scenario_payload.items():
            setattr(scenario, field_name, value)

    session = db.execute(
        select(InterviewSession).where(
            InterviewSession.interview_id == interview.id,
            InterviewSession.candidate_user_id == candidate.id,
        )
    ).scalar_one_or_none()
    if session is None:
        db.add(
            InterviewSession(
                interview=interview,
                candidate=candidate,
                status=InterviewSessionStatus.INVITED,
            )
        )


def seed() -> None:
    db = SessionLocal()
    try:
        organization = _get_or_create_organization(db)
        _upsert_user(
            db,
            email="admin@nexterview.dev",
            full_name="Demo Admin",
            role=UserRole.ADMIN,
            organization=organization,
        )
        interviewer = _upsert_user(
            db,
            email="interviewer@nexterview.dev",
            full_name="Demo Interviewer",
            role=UserRole.INTERVIEWER,
            organization=organization,
        )
        candidate = _upsert_user(
            db,
            email="candidate@nexterview.dev",
            full_name="Demo Candidate",
            role=UserRole.CANDIDATE,
            organization=organization,
        )
        _upsert_demo_interview(db, organization=organization, interviewer=interviewer, candidate=candidate)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo organization and users.")

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.interview import Interview, Scenario, ScenarioStatus
from app.models.organization import Organization, OrganizationMember
from app.models.user import User, UserRole
from app.services.scenario_projects import upsert_scenario_project
from app.services.scenario_generator import build_fallback_scenario

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


def _upsert_sample_interview(db: Session, *, organization: Organization, interviewer: User) -> None:
    interview = db.execute(
        select(Interview).where(
            Interview.organization_id == organization.id,
            Interview.role_title == "Backend Platform Engineer",
            Interview.interview_type == "Backend debugging",
        )
    ).scalar_one_or_none()

    if interview is None:
        interview = Interview(
            organization_id=organization.id,
            created_by_id=interviewer.id,
            role_title="Backend Platform Engineer",
            seniority="Senior",
            stack=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            difficulty="Intermediate",
            interview_type="Backend debugging",
            duration_minutes=75,
            allowed_ai_mode="Pair Programmer Mode",
            evaluation_criteria=[
                "Correctness and edge-case handling",
                "Debugging process and verification discipline",
                "Code quality, maintainability, and error handling",
                "AI collaboration quality and ability to validate suggestions",
            ],
            status="READY",
        )
        db.add(interview)
        db.flush()
    else:
        interview.created_by_id = interviewer.id
        interview.stack = ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"]
        interview.difficulty = "Intermediate"
        interview.duration_minutes = 75
        interview.allowed_ai_mode = "Pair Programmer Mode"
        interview.status = "READY"

    generated = build_fallback_scenario(interview)
    scenario = db.execute(select(Scenario).where(Scenario.interview_id == interview.id)).scalar_one_or_none()
    if scenario is None:
        scenario = Scenario(interview_id=interview.id)
        db.add(scenario)

    scenario.title = generated.title
    scenario.role_title = generated.role_title
    scenario.seniority = generated.seniority
    scenario.interview_type = generated.interview_type
    scenario.difficulty = generated.difficulty
    scenario.stack = generated.stack
    scenario.language = generated.language
    scenario.framework = generated.framework
    scenario.ai_mode = generated.ai_mode
    scenario.business_context = generated.business_context
    scenario.technical_requirements = generated.technical_requirements
    scenario.visible_requirements = generated.visible_requirements
    scenario.starter_code = generated.starter_code
    scenario.starter_files_json = [file_payload.model_dump() for file_payload in generated.starter_files_json]
    scenario.test_files_json = [file_payload.model_dump() for file_payload in generated.test_files_json]
    scenario.expected_solution_files_json = [
        file_payload.model_dump() for file_payload in generated.expected_solution_files_json
    ]
    scenario.expected_behavior = generated.expected_behavior
    scenario.logs_or_bug_report = generated.logs_or_bug_report
    scenario.bug_description = generated.bug_description
    scenario.bug_description_internal = generated.bug_description_internal
    scenario.feature_request = generated.feature_request
    scenario.validation_instructions = generated.validation_instructions
    scenario.validation_command = generated.validation_command
    scenario.constraints = generated.constraints
    scenario.candidate_task_summary = generated.candidate_task_summary
    scenario.expected_solution_summary = generated.expected_solution_summary
    scenario.scenario_fit = generated.scenario_fit
    scenario.hidden_evaluation_points = generated.hidden_evaluation_points
    scenario.hidden_rubric = generated.hidden_rubric
    scenario.candidate_instructions = generated.candidate_instructions
    scenario.interviewer_rubric = generated.interviewer_rubric
    scenario.generation_source = "fallback"
    scenario.ai_model = None
    scenario.status = ScenarioStatus.APPROVED.value
    db.flush()
    upsert_scenario_project(db, scenario=scenario, project_payload=generated.project)


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
        _upsert_user(
            db,
            email="candidate@nexterview.dev",
            full_name="Demo Candidate",
            role=UserRole.CANDIDATE,
            organization=organization,
        )
        _upsert_sample_interview(db, organization=organization, interviewer=interviewer)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo organization, users, and sample interview.")

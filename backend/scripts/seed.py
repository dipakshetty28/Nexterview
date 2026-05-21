from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
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


def seed() -> None:
    db = SessionLocal()
    try:
        organization = _get_or_create_organization(db)
        _upsert_user(
            db,
            email="admin@nexterview.local",
            full_name="Demo Admin",
            role=UserRole.ADMIN,
            organization=organization,
        )
        _upsert_user(
            db,
            email="interviewer@nexterview.local",
            full_name="Demo Interviewer",
            role=UserRole.INTERVIEWER,
            organization=organization,
        )
        _upsert_user(
            db,
            email="candidate@nexterview.local",
            full_name="Demo Candidate",
            role=UserRole.CANDIDATE,
            organization=organization,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seeded demo organization and users.")

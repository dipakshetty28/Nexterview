from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.organization import OrganizationMember
from app.models.user import User, UserRole
from app.schemas.auth import UserRead
from app.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/api", tags=["dashboard"])


def _serialize_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        organizations=list(user.memberships),
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    current_user: Annotated[
        User,
        Depends(require_roles(UserRole.ADMIN, UserRole.INTERVIEWER, UserRole.CANDIDATE)),
    ],
) -> DashboardResponse:
    serialized_user = _serialize_user(current_user)
    return DashboardResponse(user=serialized_user, organizations=serialized_user.organizations)


@router.get("/admin/users", response_model=list[UserRead])
def admin_users(
    current_user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserRead]:
    _ = current_user
    users = db.execute(
        select(User).options(selectinload(User.memberships).selectinload(OrganizationMember.organization)).order_by(User.email)
    ).scalars()
    return [_serialize_user(user) for user in users]

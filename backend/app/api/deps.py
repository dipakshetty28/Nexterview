from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.organization import OrganizationMember
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _auth_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided or are invalid.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _auth_error()

    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError:
        raise _auth_error() from None

    user = db.execute(
        select(User)
        .options(selectinload(User.memberships).selectinload(OrganizationMember.organization))
        .where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise _auth_error()
    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return dependency

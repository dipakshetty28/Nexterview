from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.organization import Organization, OrganizationMember
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "organization"


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


def _build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=_serialize_user(user))


def _unique_organization_slug(db: Session, organization_name: str) -> str:
    base_slug = _slugify(organization_name)
    slug = base_slug
    suffix = 2
    while db.execute(select(Organization.id).where(Organization.slug == slug)).scalar_one_or_none() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = _normalize_email(payload.email)
    existing_user = db.execute(select(User.id).where(User.email == email)).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists.")

    try:
        user = User(
            email=email,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            role=UserRole.ADMIN,
        )
        organization = Organization(
            name=payload.organization_name.strip(),
            slug=_unique_organization_slug(db, payload.organization_name),
        )
        membership = OrganizationMember(user=user, organization=organization, role=UserRole.ADMIN)
        db.add_all([user, organization, membership])
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Registration conflicts with existing data.")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    db.refresh(user)
    user = db.execute(
        select(User)
        .options(selectinload(User.memberships).selectinload(OrganizationMember.organization))
        .where(User.id == user.id)
    ).scalar_one()
    return _build_auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = _normalize_email(payload.email)
    user = db.execute(
        select(User)
        .options(selectinload(User.memberships).selectinload(OrganizationMember.organization))
        .where(User.email == email)
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return _build_auth_response(user)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return _serialize_user(current_user)

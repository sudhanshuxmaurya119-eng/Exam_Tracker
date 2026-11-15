"""Administrator authentication and account management routes."""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, require_super_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit_dependency
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import AdminUser
from app.schemas.schemas import (
    AdminUserCreate,
    AdminUserResponse,
    LoginRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

login_rate_limiter = rate_limit_dependency(
    bucket="auth_login",
    max_requests=settings.RATE_LIMIT_AUTH_PER_MINUTE,
    window_seconds=60,
)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(login_rate_limiter)],
    summary="Authenticate administrator and issue JWT access token",
)
def login_admin(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    identifier = payload.username.strip()
    stmt = select(AdminUser).where(
        or_(
            func.lower(AdminUser.username) == identifier.lower(),
            func.lower(AdminUser.email) == identifier.lower(),
        )
    )
    admin = db.scalar(stmt)
    if admin is None or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is disabled.",
        )

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)

    token_data = create_access_token(
        subject=admin.id,
        role=admin.role,
        username=admin.username,
    )
    return TokenResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        expires_in=token_data["expires_in"],
        expires_at=token_data["expires_at"],
        user=AdminUserResponse.model_validate(admin),
    )


@router.get(
    "/me",
    response_model=AdminUserResponse,
    summary="Get current authenticated administrator profile",
)
def get_me(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUserResponse:
    return AdminUserResponse.model_validate(current_admin)


@router.get(
    "/admins",
    response_model=List[AdminUserResponse],
    summary="List administrator accounts",
)
def list_admins(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> List[AdminUserResponse]:
    admins = db.scalars(select(AdminUser).order_by(AdminUser.id.asc())).all()
    return [AdminUserResponse.model_validate(a) for a in admins]


@router.post(
    "/admins",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new administrator account (Super Admin only)",
)
def create_admin_account(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_super_admin),
) -> AdminUserResponse:
    existing = db.scalar(
        select(AdminUser).where(
            or_(
                func.lower(AdminUser.username) == payload.username.lower(),
                func.lower(AdminUser.email) == payload.email.lower(),
            )
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An administrator with that username or email already exists.",
        )

    new_admin = AdminUser(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return AdminUserResponse.model_validate(new_admin)

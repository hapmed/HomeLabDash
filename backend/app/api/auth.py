"""Autenticación: login por usuario/contraseña y emisión de JWT."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    verify_dummy_password,
    verify_password,
)
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

logger = logging.getLogger(__name__)

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None


def _audit(db: Session, request: Request, actor: str, success: bool) -> None:
    db.add(
        AuditLog(
            actor=actor,
            action="auth.login",
            success=success,
            ip=_client_ip(request),
            detail=None,
        )
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit("auth")),
) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username))

    if user is None:
        verify_dummy_password(payload.password)
        _audit(db, request, payload.username, False)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="usuario o contraseña incorrectos",
        )

    if not user.is_active or not verify_password(payload.password, user.password_hash):
        _audit(db, request, payload.username, False)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="usuario o contraseña incorrectos",
        )

    token, expires_in = create_access_token(str(user.id))
    user.last_login_at = datetime.now(UTC)
    _audit(db, request, payload.username, True)
    db.commit()
    logger.info("login correcto: %s", user.username)

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)

"""Hashing de contraseñas y emisión/validación de JWT."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

# Hash de relleno para comparar también cuando el usuario no existe y evitar
# diferencias de tiempo que permitan enumerar cuentas.
_DUMMY_HASH = bcrypt.hashpw(b"homelabdash-dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("la contraseña no puede estar vacía")
    # bcrypt solo usa los primeros 72 bytes.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not password or not stored_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], stored_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_dummy_password(password: str) -> None:
    """Consume tiempo similar a una verificación real (anti-enumeración)."""
    verify_password(password, _DUMMY_HASH)


def create_access_token(subject: str) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.jwt_ttl_minutes)
    payload: dict[str, Any] = {"sub": subject, "iat": int(now.timestamp()), "exp": int(expires.timestamp())}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_ttl_minutes * 60


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None

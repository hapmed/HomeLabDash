"""Arranque: creación del administrador inicial si no existe."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def bootstrap_admin(session: Session) -> None:
    settings = get_settings()
    if not settings.admin_password:
        logger.warning("ADMIN_PASSWORD vacío: no se crea el administrador inicial")
        return

    existing = session.scalar(select(User).where(User.username == settings.admin_user))
    if existing is not None:
        return

    session.add(
        User(
            username=settings.admin_user,
            password_hash=hash_password(settings.admin_password),
            is_active=True,
            is_admin=True,
        )
    )
    session.commit()
    logger.info("administrador inicial creado: %s", settings.admin_user)

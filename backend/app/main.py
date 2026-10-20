"""Bootstrap de la aplicación FastAPI."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, health, modules
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.bootstrap import bootstrap_admin
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        with get_session_factory()() as session:
            bootstrap_admin(session)
    except Exception:  # noqa: BLE001 - el arranque no debe caer si la BD tarda
        logger.exception("no se pudo inicializar el administrador (¿migraciones pendientes?)")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(modules.router, prefix="/api/v1/modules", tags=["modules"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
    return app


app = create_app()

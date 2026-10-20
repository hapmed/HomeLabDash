"""Configuración centralizada del backend (variables de entorno)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "HomeLabDash API"
    version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "prod"] = "local"
    debug: bool = False

    # Base de datos: instancia PostgreSQL existente.
    database_url: str = (
        "postgresql+psycopg://homelabdash_app:change-me@postgres:5432/homelabdash"
    )

    # Sesión de usuario (JWT).
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 720
    cookie_name: str = "hld_session"
    cookie_secure: bool = True

    # Administrador inicial.
    admin_user: str = "admin"
    admin_password: str = ""

    # Agente de métricas.
    agent_url: str = "http://agent:8001"
    agent_token: str = ""
    agent_timeout_seconds: float = 8.0

    # Rate limiting.
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 10

    # Umbrales de estado.
    cpu_warn: float = 75.0
    cpu_critical: float = 90.0
    memory_warn: float = 80.0
    memory_critical: float = 92.0
    disk_warn: float = 85.0
    disk_critical: float = 95.0
    load_per_core_warn: float = 1.0
    load_per_core_critical: float = 2.0

    # CORS (vacío = no se habilita).
    cors_origins: list[str] = Field(default_factory=list)

    # Snapshots genéricos de todos los módulos (gráficas 24 h / 7 d / 30 d).
    snapshot_monitor_enabled: bool = True
    snapshot_interval_seconds: int = 300
    snapshot_history_days: int = 30
    snapshot_max_points: int = 600
    database_connection_warn_percent: float = 80.0
    database_connection_critical_percent: float = 95.0
    database_cache_warn_percent: float = 90.0
    database_dead_tuple_warn_percent: float = 20.0
    database_long_query_warn_seconds: float = 30.0

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()

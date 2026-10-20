"""Configuración del agente de métricas."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    agent_token: str = ""
    host_root: str = "/host"
    host_proc: str = "/host/proc"
    host_sys: str = "/host/sys"

    cpu_warn: float = 75.0
    cpu_critical: float = 90.0
    memory_warn: float = 80.0
    memory_critical: float = 92.0
    disk_warn: float = 85.0
    disk_critical: float = 95.0
    load_per_core_warn: float = 1.0
    load_per_core_critical: float = 2.0

    @property
    def procfs(self) -> str:
        return self.host_proc if Path(self.host_proc).is_dir() else "/proc"

    @property
    def rootfs(self) -> str:
        return self.host_root if Path(self.host_root).is_dir() else "/"

    @property
    def sysfs(self) -> str:
        return self.host_sys if Path(self.host_sys).is_dir() else "/sys"


@lru_cache
def get_settings() -> Settings:
    return Settings()

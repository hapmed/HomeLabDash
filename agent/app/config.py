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

    # Monitor de Internet (IP pública, latencia y velocidad).
    internet_monitor_enabled: bool = True
    internet_check_seconds: int = 60
    internet_speedtest_minutes: int = 60
    internet_ip_refresh_minutes: int = 15
    internet_download_bytes: int = 10_000_000
    internet_upload_bytes: int = 2_000_000
    internet_history_size: int = 168
    internet_history_path: str = "/data/internet-history.json"
    internet_latency_warn_ms: float = 150.0
    internet_latency_critical_ms: float = 400.0
    internet_speedtest_url: str = "https://speed.cloudflare.com"
    internet_trace_url: str = "https://www.cloudflare.com/cdn-cgi/trace"
    internet_ipinfo_url: str = "https://ipinfo.io"
    internet_ipinfo_enabled: bool = True

    # Monitor de dispositivos de la red local.
    network_monitor_enabled: bool = True
    network_cidr: str = "192.168.0.0/24"
    network_scan_seconds: int = 60
    network_probe_wait_seconds: float = 2.5
    network_history_path: str = "/data/network-devices.json"
    network_name: str = ""
    network_arp_path: str = "/host/proc/1/net/arp"
    network_gateway_ip: str = "192.168.0.1"
    network_gateway_name: str = "Mercusys AC12"
    network_server_ip: str = "192.168.0.14"
    network_server_name: str = "HomeLab (servidor)"
    network_host_sys: str = "/host/sys"

    # Interfaces de red del host (RX/TX, errores y estado).
    host_network_enabled: bool = True
    host_network_poll_seconds: int = 5

    # Sensores de temperatura y ventiladores del host.
    temperature_enabled: bool = True
    temperature_warn_c: float = 75.0
    temperature_critical_c: float = 85.0

    # Hardware: batería, discos, inodos y salud disponible.
    hardware_enabled: bool = True
    hardware_inodes_warn_percent: float = 90.0
    hardware_inodes_critical_percent: float = 95.0

    # Router Mercusys (solo lectura; opcional, mejora nombres/SSID/consumo).
    router_enabled: bool = False
    router_url: str = "http://192.168.0.1"
    router_username: str = "admin"
    router_password: str = ""
    router_info_refresh_seconds: int = 300
    router_retry_seconds: int = 300

    # Docker (solo lectura; socket montado en ro).
    docker_monitor_enabled: bool = True
    docker_socket: str = "unix:///var/run/docker.sock"
    docker_poll_seconds: int = 30
    docker_df_seconds: int = 120
    docker_stats_timeout: float = 8.0

    # Ciclo de facturación mensual (corte el día indicado, hora local).
    billing_cycle_day: int = 10
    billing_timezone: str = "America/Monterrey"
    billing_history_months: int = 24
    billing_daily_history_days: int = 62

    # Clima (Open-Meteo, sin API key).
    weather_enabled: bool = True
    weather_latitude: float = 25.6866
    weather_longitude: float = -100.3161
    weather_timezone: str = "America/Monterrey"
    weather_location: str = "Monterrey"
    weather_poll_seconds: int = 900
    weather_history_path: str = "/data/weather-history.json"
    weather_history_days: int = 730
    weather_payload_history_days: int = 90
    weather_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_air_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"

    # Módulo dedicado de OpenCode (usa el socket Docker).
    opencode_enabled: bool = True
    opencode_container: str = "opencode"
    opencode_api_url: str = "http://opencode:4096"
    opencode_api_username: str = "opencode"
    opencode_api_password: str = ""
    opencode_app_poll_seconds: int = 60
    opencode_session_limit: int = 100

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

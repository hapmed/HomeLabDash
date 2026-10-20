"""Monitor de Docker en solo lectura.

Se conecta al socket de Docker (montado en ro) y muestrea contenedores,
consumo de CPU/RAM, red, bloques y uso de disco. Nunca ejecuta acciones.
"""

import copy
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any, cast

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

from app.config import Settings

logger = logging.getLogger(__name__)


class DockerLogsError(RuntimeError):
    """No se pudieron leer los logs del contenedor."""


class DockerNotFoundError(DockerLogsError):
    """El contenedor no existe."""


_DOCKER_TIME = re.compile(r"(\.\d{6})\d*")


def human_bytes(value: float | int | None) -> str:
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def parse_docker_time(value: str | None) -> datetime | None:
    if not value or value.startswith("0001-"):
        return None
    cleaned = _DOCKER_TIME.sub(r"\1", value.replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def calculate_cpu_percent(stats: dict[str, Any] | None) -> float:
    if not stats:
        return 0.0
    cpu = stats.get("cpu_stats") or {}
    previous = stats.get("precpu_stats") or {}
    cpu_total = (cpu.get("cpu_usage") or {}).get("total_usage", 0) or 0
    previous_total = (previous.get("cpu_usage") or {}).get("total_usage", 0) or 0
    system_total = cpu.get("system_cpu_usage", 0) or 0
    previous_system = previous.get("system_cpu_usage", 0) or 0
    online = cpu.get("online_cpus") or len(
        (cpu.get("cpu_usage") or {}).get("percpu_usage") or []
    )
    cpu_delta = cpu_total - previous_total
    system_delta = system_total - previous_system
    if cpu_delta > 0 and system_delta > 0 and online:
        return round((cpu_delta / system_delta) * online * 100, 1)
    return 0.0


def calculate_memory(stats: dict[str, Any] | None) -> tuple[int, int, float]:
    if not stats:
        return 0, 0, 0.0
    memory = stats.get("memory_stats") or {}
    usage = int(memory.get("usage", 0) or 0)
    limit = int(memory.get("limit", 0) or 0)
    detail = memory.get("stats") or {}
    cache = int(detail.get("inactive_file") or detail.get("total_inactive_file") or 0)
    used = max(0, usage - cache)
    percent = round(used / limit * 100, 1) if limit else 0.0
    return used, limit, percent


def calculate_network(stats: dict[str, Any] | None) -> tuple[int, int]:
    if not stats:
        return 0, 0
    networks = stats.get("networks") or {}
    rx = sum(int(item.get("rx_bytes", 0) or 0) for item in networks.values())
    tx = sum(int(item.get("tx_bytes", 0) or 0) for item in networks.values())
    return rx, tx


def calculate_block_io(stats: dict[str, Any] | None) -> tuple[int, int]:
    if not stats:
        return 0, 0
    entries = (stats.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []
    read = sum(int(item.get("value", 0) or 0) for item in entries if item.get("op") == "read")
    write = sum(int(item.get("value", 0) or 0) for item in entries if item.get("op") == "write")
    return read, write


class DockerMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._client: docker.DockerClient | None = None
        self._df_cache: dict[str, Any] = {}
        self._df_at = 0.0
        self._state: dict[str, Any] = {
            "enabled": settings.docker_monitor_enabled,
            "containers": [],
            "system": {},
            "totals": {},
            "top_cpu": None,
            "top_memory": None,
            "sampled_at": None,
            "error": None,
            "poll_seconds": settings.docker_poll_seconds,
        }

    # --- ciclo de vida ---------------------------------------------------
    def start(self) -> None:
        if not self.settings.docker_monitor_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="docker-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            if self._stop.wait(max(10, self.settings.docker_poll_seconds)):
                break

    # --- muestreo --------------------------------------------------------
    def _ensure_client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.DockerClient(
                base_url=self.settings.docker_socket,
                timeout=int(self.settings.docker_stats_timeout),
                version="auto",
            )
        return self._client

    def _safe_stats(self, container: Container) -> dict[str, Any] | None:
        try:
            return cast(dict[str, Any], container.stats(stream=False))
        except DockerException:
            return None

    def _sample(self) -> None:
        try:
            client = self._ensure_client()
            client.ping()
            containers = client.containers.list(all=True)
            running = [container for container in containers if container.status == "running"]
            stats_by_id: dict[str, dict[str, Any]] = {}
            if running:
                workers = min(8, max(1, len(running)))
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {pool.submit(self._safe_stats, container): container for container in running}
                    for future in as_completed(futures):
                        container = futures[future]
                        try:
                            result = future.result()
                        except Exception:  # noqa: BLE001 - un contenedor no debe tumbar el muestreo
                            result = None
                        if result is not None:
                            stats_by_id[container.id or ""] = result

            records = [
                self._container_data(container, stats_by_id.get(container.id or ""))
                for container in containers
            ]
            records.sort(
                key=lambda item: (
                    item["state"] != "running",
                    -float(item.get("cpu_percent", 0)),
                    str(item.get("name", "")).lower(),
                )
            )
            system = self._system_data(client, containers)
            totals = {
                "cpu_percent": round(sum(float(item.get("cpu_percent", 0)) for item in records), 1),
                "memory_used": sum(int(item.get("memory_used", 0)) for item in records),
                "net_rx": sum(int(item.get("net_rx", 0)) for item in records),
                "net_tx": sum(int(item.get("net_tx", 0)) for item in records),
                "blk_read": sum(int(item.get("blk_read", 0)) for item in records),
                "blk_write": sum(int(item.get("blk_write", 0)) for item in records),
            }
            top_cpu = max(
                (item for item in records if item["state"] == "running"),
                key=lambda item: float(item.get("cpu_percent", 0)),
                default=None,
            )
            top_memory = max(
                (item for item in records if item["state"] == "running"),
                key=lambda item: int(item.get("memory_used", 0)),
                default=None,
            )
        except (DockerException, OSError, PermissionError) as exc:
            message = f"docker no disponible ({type(exc).__name__})"
            with self._lock:
                self._state["error"] = message
                self._state["sampled_at"] = datetime.now(UTC).isoformat()
            logger.warning("%s", message)
            return

        with self._lock:
            self._state.update(
                {
                    "containers": records,
                    "system": system,
                    "totals": totals,
                    "top_cpu": self._brief(top_cpu),
                    "top_memory": self._brief(top_memory),
                    "sampled_at": datetime.now(UTC).isoformat(),
                    "error": None,
                }
            )

    def _container_data(
        self, container: Container, stats: dict[str, Any] | None
    ) -> dict[str, Any]:
        attrs = container.attrs or {}
        state = attrs.get("State") or {}
        labels = (attrs.get("Config") or {}).get("Labels") or {}
        started = parse_docker_time(state.get("StartedAt"))
        now = datetime.now(UTC)
        uptime = (
            max(0.0, (now - started).total_seconds())
            if started and container.status == "running"
            else 0.0
        )
        memory_used, memory_limit, memory_percent = calculate_memory(stats)
        net_rx, net_tx = calculate_network(stats)
        blk_read, blk_write = calculate_block_io(stats)
        ports: list[str] = []
        for container_port, bindings in (
            (attrs.get("NetworkSettings") or {}).get("Ports") or {}
        ).items():
            if not bindings:
                ports.append(container_port)
                continue
            for binding in bindings:
                host = binding.get("HostIp") or "0.0.0.0"
                ports.append(f"{host}:{binding.get('HostPort')}->{container_port}")

        return {
            "id": (container.id or "")[:12],
            "name": container.name,
            "image": (attrs.get("Config") or {}).get("Image", ""),
            "state": container.status,
            "status": state.get("Status", container.status),
            "health": (state.get("Health") or {}).get("Status"),
            "created": attrs.get("Created"),
            "started_at": state.get("StartedAt"),
            "uptime_seconds": round(uptime),
            "restart_count": int(attrs.get("RestartCount", 0) or 0),
            "cpu_percent": calculate_cpu_percent(stats),
            "memory_used": memory_used,
            "memory_limit": memory_limit,
            "memory_percent": memory_percent,
            "net_rx": net_rx,
            "net_tx": net_tx,
            "blk_read": blk_read,
            "blk_write": blk_write,
            "pids": int((stats or {}).get("pids_stats", {}).get("current", 0) or 0),
            "ports": ports,
            "networks": list(((attrs.get("NetworkSettings") or {}).get("Networks") or {}).keys()),
            "compose_project": labels.get("com.docker.compose.project"),
            "compose_service": labels.get("com.docker.compose.service"),
            "stats": stats is not None,
        }

    def _system_data(
        self, client: docker.DockerClient, containers: list[Container]
    ) -> dict[str, Any]:
        version = client.version()
        info = client.info()
        now = time.monotonic()
        if now - self._df_at >= self.settings.docker_df_seconds:
            try:
                self._df_cache = client.df() or {}
                self._df_at = now
            except DockerException:
                pass

        df = self._df_cache
        images = df.get("Images") or []
        volumes = df.get("Volumes") or []
        containers_df = df.get("Containers") or []
        build_cache = df.get("BuildCache") or []
        volumes_size = 0
        for volume in volumes:
            usage = volume.get("UsageData") or {}
            volumes_size += int(usage.get("Size", 0) or 0)
        counts = {
            "total": len(containers),
            "running": sum(1 for item in containers if item.status == "running"),
            "paused": sum(1 for item in containers if item.status == "paused"),
            "stopped": sum(
                1 for item in containers if item.status in {"exited", "created", "dead"}
            ),
        }
        try:
            networks_count = len(client.networks.list())
        except DockerException:
            networks_count = int(info.get("Networks", 0) or 0)
        return {
            "version": version.get("Version"),
            "api_version": version.get("ApiVersion"),
            "os": version.get("Os"),
            "arch": version.get("Arch"),
            "kernel": version.get("KernelVersion"),
            "hostname": info.get("Name"),
            "cpus": info.get("NCPU"),
            "memory_total": info.get("MemTotal"),
            "images": len(images) if images else int(info.get("Images", 0) or 0),
            "volumes": len(volumes) if df else None,
            "networks": networks_count,
            "containers": counts,
            "disk": {
                "images": int(df.get("LayersSize", 0) or 0),
                "containers": sum(int(item.get("SizeRw", 0) or 0) for item in containers_df),
                "volumes": volumes_size,
                "build_cache": sum(int(item.get("Size", 0) or 0) for item in build_cache),
                "total": int(df.get("LayersSize", 0) or 0)
                + sum(int(item.get("SizeRw", 0) or 0) for item in containers_df)
                + volumes_size
                + sum(int(item.get("Size", 0) or 0) for item in build_cache),
            },
        }

    @staticmethod
    def _brief(item: dict[str, Any] | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "image": item.get("image"),
            "cpu_percent": item.get("cpu_percent"),
            "memory_used": item.get("memory_used"),
        }

    # --- API -------------------------------------------------------------
    def logs(self, container_id: str, tail: int = 100) -> dict[str, Any]:
        client = self._ensure_client()
        try:
            container = client.containers.get(container_id)
            raw = container.logs(tail=tail, timestamps=True)
        except NotFound as exc:
            raise DockerNotFoundError("contenedor no encontrado") from exc
        except (DockerException, OSError) as exc:
            raise DockerLogsError("no se pudieron leer los logs") from exc
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        lines = text.splitlines()[-tail:]
        return {
            "container": container.name,
            "id": (container.id or "")[:12],
            "lines": lines,
            "tail": tail,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Contenedores",
                    "value": "—",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }

        counts = (snap.get("system") or {}).get("containers") or {}
        running = counts.get("running", 0)
        total = counts.get("total", 0)
        unhealthy = sum(
            1
            for item in snap["containers"]
            if item.get("health") == "unhealthy" or item.get("state") in {"restarting", "dead"}
        )
        if snap["error"]:
            status = "critical" if not snap["containers"] else "warn"
        elif unhealthy:
            status = "warn"
        elif total == 0:
            status = "warn"
        else:
            status = "ok"

        totals = snap.get("totals") or {}
        summary_value = f"{running}/{total}" if total else "—"
        if snap["error"]:
            detail = snap["error"]
        elif total:
            detail = (
                f"{unhealthy} con problemas · CPU {totals.get('cpu_percent', 0):.1f}% · "
                f"RAM {human_bytes(totals.get('memory_used', 0))}"
            )
        else:
            detail = "Recopilando métricas…"

        return {
            "status": status,
            "summary": {"label": "Contenedores", "value": summary_value, "detail": detail},
            "detail": snap,
        }

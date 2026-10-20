"""Métricas del host en solo lectura.

Fuentes: `/proc`, `/sys` y el sistema de archivos del host montados en `/host`
(cuando corre en contenedor). Sin esos montajes usa los del propio proceso, lo
que permite ejecutar el agente en local para desarrollo.
"""

import os
import re
import shutil
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from app.config import Settings

STATUS_RANK = {"ok": 0, "warn": 1, "critical": 2, "unknown": 3}
DISK_FILESYSTEMS = {
    "ext2",
    "ext3",
    "ext4",
    "xfs",
    "btrfs",
    "f2fs",
    "vfat",
    "fat",
    "fat32",
    "zfs",
    "ntfs",
    "ntfs3",
}
SKIP_MOUNT_PREFIXES = (
    "/snap",
    "/var/lib/docker",
    "/var/lib/containers",
    "/run",
    "/sys",
    "/proc",
    "/dev",
)
_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")


def worst(statuses: list[str]) -> str:
    if not statuses:
        return "unknown"
    return max(statuses, key=lambda status: STATUS_RANK.get(status, 3))


def status_for(value: float, warn: float, critical: float) -> str:
    if value >= critical:
        return "critical"
    if value >= warn:
        return "warn"
    return "ok"


def format_uptime(seconds: float) -> str:
    total = int(seconds)
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _decode_mount(value: str) -> str:
    return _OCTAL_ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), value)


class HostMetrics:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # psutil lee `/proc` desde esta ruta (procfs del host si está montado).
        psutil.PROCFS_PATH = settings.procfs

    # --- utilidades -----------------------------------------------------
    def _read(self, path: str, default: str = "") -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return default

    def _root_path(self, mountpoint: str) -> str:
        root = self.settings.rootfs.rstrip("/")
        if mountpoint == "/":
            return root or "/"
        return f"{root}{mountpoint}"

    def _loadavg(self) -> tuple[float, float, float]:
        try:
            one, five, fifteen = psutil.getloadavg()
        except OSError:
            return (0.0, 0.0, 0.0)
        return (round(one, 2), round(five, 2), round(fifteen, 2))

    def _uptime(self) -> float:
        raw = self._read(f"{self.settings.procfs}/uptime")
        if raw:
            try:
                return float(raw.split()[0])
            except (ValueError, IndexError):
                pass
        return max(0.0, time.time() - psutil.boot_time())

    def _hostname(self) -> str:
        # `/proc/sys/kernel/hostname` refleja el UTS namespace de quien lee
        # (el contenedor); el host real está en el `/etc/hostname` montado.
        raw = self._read(f"{self.settings.rootfs}/etc/hostname").strip()
        if raw:
            return raw
        raw = self._read(f"{self.settings.procfs}/sys/kernel/hostname").strip()
        return raw or socket.gethostname()

    def _os_release(self) -> tuple[str, str]:
        raw = self._read(f"{self.settings.rootfs}/etc/os-release")
        data: dict[str, str] = {}
        for line in raw.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"')
        return data.get("PRETTY_NAME", "Linux"), data.get("VERSION_ID", "")

    def _kernel(self) -> str:
        raw = self._read(f"{self.settings.procfs}/sys/kernel/osrelease").strip()
        if raw:
            return raw
        try:
            return os.uname().release
        except AttributeError:  # pragma: no cover - solo no-Linux
            return ""

    def _cpu_model(self) -> str:
        raw = self._read(f"{self.settings.procfs}/cpuinfo")
        for line in raw.splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
        return "CPU"

    def _memory_pressure(self) -> dict[str, float] | None:
        raw = self._read(f"{self.settings.procfs}/pressure/memory")
        if not raw:
            return None
        pressure: dict[str, float] = {}
        for line in raw.splitlines():
            parts = line.split()
            if not parts:
                continue
            kind = parts[0]
            for part in parts[1:]:
                if part.startswith("avg10="):
                    try:
                        pressure[kind] = float(part.split("=", 1)[1])
                    except ValueError:
                        pass
        return pressure or None

    def _mounts(self) -> list[dict[str, Any]]:
        # `/proc/mounts` depende del namespace de montaje de quien lee. Con el
        # `/proc` del host montado, `/proc/1/mounts` muestra los del host.
        host_init_mounts = f"{self.settings.procfs}/1/mounts"
        if Path(host_init_mounts).exists():
            raw = self._read(host_init_mounts)
        else:
            raw = self._read(f"{self.settings.procfs}/mounts")
        mounts: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line in raw.splitlines():
            fields = line.split()
            if len(fields) < 3:
                continue
            device, mountpoint, fstype = fields[0], _decode_mount(fields[1]), fields[2]
            if fstype not in DISK_FILESYSTEMS:
                continue
            if not device.startswith("/dev/"):
                continue
            if mountpoint.startswith(SKIP_MOUNT_PREFIXES):
                continue
            if mountpoint in seen:
                continue
            seen.add(mountpoint)
            try:
                usage = shutil.disk_usage(self._root_path(mountpoint))
            except OSError:
                continue
            mounts.append(
                {
                    "device": device,
                    "mountpoint": mountpoint,
                    "fstype": fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0.0,
                }
            )
        mounts.sort(key=lambda item: (item["mountpoint"] != "/", item["mountpoint"]))
        return mounts

    # --- módulos --------------------------------------------------------
    def cpu(self) -> dict[str, Any]:
        per_core = [round(value, 1) for value in psutil.cpu_percent(interval=0.15, percpu=True)]
        overall = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
        load = self._loadavg()
        logical = psutil.cpu_count(logical=True) or len(per_core) or 1
        physical = psutil.cpu_count(logical=False) or logical
        freq = psutil.cpu_freq()
        load_per_core = load[0] / logical if logical else 0.0

        status = worst(
            [
                status_for(overall, self.settings.cpu_warn, self.settings.cpu_critical),
                status_for(
                    load_per_core,
                    self.settings.load_per_core_warn,
                    self.settings.load_per_core_critical,
                ),
            ]
        )
        return {
            "status": status,
            "summary": {
                "label": "uso",
                "value": overall,
                "unit": "%",
                "detail": f"carga 1m {load[0]:.2f} · {logical} núcleos",
            },
            "detail": {
                "percent": overall,
                "cores": [
                    {"index": index, "percent": value} for index, value in enumerate(per_core)
                ],
                "logical_cores": logical,
                "physical_cores": physical,
                "frequency_mhz": round(freq.current, 0) if freq else None,
                "frequency_max_mhz": round(freq.max, 0) if freq and freq.max else None,
                "model": self._cpu_model(),
                "load": {"1m": load[0], "5m": load[1], "15m": load[2]},
                "load_per_core": round(load_per_core, 2),
            },
        }

    def memory(self) -> dict[str, Any]:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        used_gb = memory.used / 1024**3
        total_gb = memory.total / 1024**3
        status = status_for(memory.percent, self.settings.memory_warn, self.settings.memory_critical)
        return {
            "status": status,
            "summary": {
                "label": "RAM usada",
                "value": round(memory.percent, 1),
                "unit": "%",
                "detail": f"{used_gb:.1f} GB de {total_gb:.1f} GB",
            },
            "detail": {
                "percent": round(memory.percent, 1),
                "total_bytes": memory.total,
                "used_bytes": memory.used,
                "available_bytes": memory.available,
                "free_bytes": memory.free,
                "cached_bytes": getattr(memory, "cached", 0),
                "buffers_bytes": getattr(memory, "buffers", 0),
                "swap": {
                    "total_bytes": swap.total,
                    "used_bytes": swap.used,
                    "free_bytes": swap.free,
                    "percent": round(swap.percent, 1),
                },
                "pressure": self._memory_pressure(),
            },
        }

    def storage(self) -> dict[str, Any]:
        mounts = self._mounts()
        root = next((item for item in mounts if item["mountpoint"] == "/"), None)
        if root is None:
            try:
                usage = shutil.disk_usage(self.settings.rootfs)
            except OSError:
                usage = None
            if usage is not None:
                root = {
                    "device": "root",
                    "mountpoint": "/",
                    "fstype": "unknown",
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0.0,
                }
        percent = float(root["percent"]) if root else 0.0
        status = status_for(percent, self.settings.disk_warn, self.settings.disk_critical)
        detail_text = "sin datos"
        if root:
            detail_text = (
                f"{root['free_bytes'] / 1024**3:.0f} GB libres de "
                f"{root['total_bytes'] / 1024**3:.0f} GB"
            )
        return {
            "status": status,
            "summary": {
                "label": "Disco raíz",
                "value": percent,
                "unit": "%",
                "detail": detail_text,
            },
            "detail": {
                "percent": percent,
                "mounts": mounts,
                "io": self._disk_io(),
            },
        }

    def _disk_io(self) -> dict[str, int] | None:
        try:
            counters = psutil.disk_io_counters()
        except (OSError, RuntimeError):
            return None
        if counters is None:
            return None
        return {
            "read_bytes": counters.read_bytes,
            "write_bytes": counters.write_bytes,
            "read_count": counters.read_count,
            "write_count": counters.write_count,
        }

    def overview(
        self,
        cpu: dict[str, Any] | None = None,
        memory: dict[str, Any] | None = None,
        storage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cpu = cpu or self.cpu()
        memory = memory or self.memory()
        storage = storage or self.storage()
        load = cpu["detail"]["load"]
        uptime = self._uptime()
        os_name, os_version = self._os_release()
        hostname = self._hostname()

        alerts: list[dict[str, str]] = []
        for module_id, module in (
            ("cpu", cpu),
            ("memory", memory),
            ("storage", storage),
        ):
            if module["status"] in {"warn", "critical"}:
                alerts.append(
                    {
                        "module": module_id,
                        "severity": module["status"],
                        "message": f"{module['summary']['label']} al "
                        f"{module['summary']['value']}{module['summary'].get('unit') or ''}",
                    }
                )

        status = worst([cpu["status"], memory["status"], storage["status"]])
        return {
            "status": status,
            "summary": {
                "label": "Carga 1m",
                "value": load["1m"],
                "detail": (
                    f"CPU {cpu['summary']['value']}% · RAM {memory['summary']['value']}% · "
                    f"up {format_uptime(uptime)}"
                ),
            },
            "detail": {
                "hostname": hostname,
                "os": os_name,
                "os_version": os_version,
                "kernel": self._kernel(),
                "uptime_seconds": round(uptime),
                "uptime_human": format_uptime(uptime),
                "boot_time": datetime.fromtimestamp(time.time() - uptime, tz=UTC).isoformat(),
                "cpu_percent": cpu["summary"]["value"],
                "memory_percent": memory["summary"]["value"],
                "disk_percent": storage["summary"]["value"],
                "load": load,
                "alerts": alerts,
            },
        }

    # --- API interna ----------------------------------------------------
    def summary(self) -> dict[str, Any]:
        cpu = self.cpu()
        memory = self.memory()
        storage = self.storage()
        overview = self.overview(cpu, memory, storage)
        hostname = str(overview["detail"]["hostname"])
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "host": {"hostname": hostname},
            "modules": {
                "overview": overview,
                "cpu": cpu,
                "memory": memory,
                "storage": storage,
            },
        }

    def module(self, module_id: str) -> dict[str, Any]:
        builders = {
            "overview": self.overview,
            "cpu": self.cpu,
            "memory": self.memory,
            "storage": self.storage,
        }
        builder = builders.get(module_id)
        if builder is None:
            raise KeyError(module_id)
        payload = builder()
        return {
            "id": module_id,
            "generated_at": datetime.now(UTC).isoformat(),
            **payload,
        }

"""Hardware del host: discos, inodos, batería/UPS y actualizaciones.

Todo es de solo lectura. SMART no se inventa: si `smartctl` no está
disponible o el contenedor no tiene permisos sobre `/dev/nvme*`, se muestra
como no disponible.
"""

import json
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.metrics import HostMetrics, status_for, worst

SKIP_BLOCK = re.compile(r"^(loop|ram|fd|sr|dm-|md|zram)")


def _read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return default


def _int(path: Path) -> int | None:
    raw = _read(path)
    try:
        return int(raw)
    except ValueError:
        return None


def _version_order(char: str) -> int:
    if char == "~":
        return -1
    if not char or char.isdigit():
        return 0
    if char.isalpha():
        return ord(char)
    return ord(char) + 256


def _compare_part(left: str, right: str) -> int:
    while left or right:
        while (left and not left[0].isdigit()) or (right and not right[0].isdigit()):
            left_char = _version_order(left[0]) if left else 0
            right_char = _version_order(right[0]) if right else 0
            if left_char != right_char:
                return left_char - right_char
            left = left[1:]
            right = right[1:]
        while left.startswith("0"):
            left = left[1:]
        while right.startswith("0"):
            right = right[1:]
        left_digits = len(left) - len(left.lstrip("0123456789"))
        right_digits = len(right) - len(right.lstrip("0123456789"))
        if left_digits != right_digits:
            return left_digits - right_digits
        left_number = left[:left_digits]
        right_number = right[:right_digits]
        if left_number != right_number:
            return 1 if left_number > right_number else -1
        left = left[left_digits:]
        right = right[right_digits:]
    return 0


def compare_versions(left: str, right: str) -> int:
    """Comparación de versiones Debian (epoch:upstream-revision)."""
    if ":" in left:
        left_epoch, left = left.split(":", 1)
    else:
        left_epoch = "0"
    if ":" in right:
        right_epoch, right = right.split(":", 1)
    else:
        right_epoch = "0"
    epoch_diff = int(left_epoch) - int(right_epoch)
    if epoch_diff:
        return 1 if epoch_diff > 0 else -1
    left_upstream, _, left_revision = left.rpartition("-")
    right_upstream, _, right_revision = right.rpartition("-")
    if not left_upstream:
        left_upstream, left_revision = left, ""
    if not right_upstream:
        right_upstream, right_revision = right, ""
    upstream = _compare_part(left_upstream, right_upstream)
    if upstream:
        return 1 if upstream > 0 else -1
    revision = _compare_part(left_revision, right_revision)
    return 1 if revision > 0 else -1 if revision < 0 else 0


def _paragraphs(path: Path) -> Iterator[list[str]]:
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    if lines:
                        yield lines
                        lines = []
                    continue
                lines.append(line.rstrip("\n"))
    except OSError:
        return
    if lines:
        yield lines


def _fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _get_any(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


class HardwareMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._updates_cache: dict[str, Any] | None = None
        self._updates_at = 0.0
        self._smart_cache: dict[str, Any] | None = None
        self._smart_at = 0.0

    # --- utilidades -----------------------------------------------------
    def _dmi(self) -> dict[str, Any]:
        base = Path(self.settings.sysfs) / "devices" / "virtual" / "dmi" / "id"
        return {
            "vendor": _read(base / "sys_vendor") or None,
            "model": _read(base / "product_name") or None,
            "board": _read(base / "board_name") or None,
            "bios": _read(base / "bios_version") or None,
            "serial": _read(base / "product_serial") or None,
        }

    def _nvme_temperature(self) -> float | None:
        base = Path(self.settings.sysfs) / "class" / "hwmon"
        if not base.is_dir():
            return None
        best: float | None = None
        for folder in base.iterdir():
            if not folder.is_dir() or _read(folder / "name") != "nvme":
                continue
            for path in folder.glob("temp*_input"):
                raw = _int(path)
                if raw is None or raw <= 0:
                    continue
                value = round(raw / 1000, 1)
                best = value if best is None else max(best, value)
        return best

    def _mounts(self) -> list[dict[str, Any]]:
        try:
            return HostMetrics(self.settings).mounts()
        except Exception:  # noqa: BLE001 - hardware no debe tumbar el agente
            return []

    def _smart_file(self) -> dict[str, Any]:
        """Lee el JSON que deja el colector de SMART del host."""
        if self._smart_cache is not None and time.monotonic() - self._smart_at < 300:
            return self._smart_cache
        candidates = [
            Path(self.settings.rootfs) / "opt" / "apps" / "HomeLabDash" / "data" / "smart.json",
            Path("/data/smart.json"),
        ]
        data: dict[str, Any] = {}
        for path in candidates:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(raw, dict) and isinstance(raw.get("devices"), dict):
                data = raw["devices"]
                break
        self._smart_cache = data
        self._smart_at = time.monotonic()
        return data

    def _smart(self, name: str) -> dict[str, Any]:
        data = self._smart_file().get(name)
        if not isinstance(data, dict):
            return {
                "available": False,
                "status": "unknown",
                "reason": "sin datos de smartctl (colector no instalado o sin permisos)",
            }
        status = _get_any(data, "smart_status", "passed")
        nvme = data.get("nvme_smart_health_information_log")
        nvme = nvme if isinstance(nvme, dict) else {}
        temperature = _get_any(data, "temperature", "current")
        if temperature is None:
            temperature = nvme.get("temperature")
        result: dict[str, Any] = {
            "available": True,
            "status": "passed" if status is True else "failed" if status is False else "unknown",
            "temperature_c": temperature,
            "power_on_hours": _get_any(data, "power_on_time", "hours"),
            "power_cycles": _get_any(data, "power_cycle_count"),
            "percentage_used": nvme.get("percentage_used"),
            "media_errors": nvme.get("media_errors"),
            "unsafe_shutdowns": nvme.get("unsafe_shutdowns"),
            "available_spare": nvme.get("available_spare"),
            "critical_warning": nvme.get("critical_warning"),
        }
        return result

    def _disks(self, mounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        base = Path(self.settings.sysfs) / "block"
        disks: list[dict[str, Any]] = []
        if not base.is_dir():
            return disks
        nvme_temp = self._nvme_temperature()
        for folder in sorted(base.iterdir(), key=lambda item: item.name):
            name = folder.name
            if not folder.is_dir() or SKIP_BLOCK.match(name):
                continue
            size_sectors = _int(folder / "size") or 0
            rotational = _int(folder / "queue" / "rotational")
            disk_mounts = [
                mount
                for mount in mounts
                if str(mount.get("device", "")).startswith(f"/dev/{name}")
            ]
            usage = max((float(mount.get("percent", 0) or 0) for mount in disk_mounts), default=None)
            inodes = max(
                (float(mount.get("inodes_percent", 0) or 0) for mount in disk_mounts),
                default=None,
            )
            smart = self._smart(name)
            temperature = smart.get("temperature_c") if smart.get("available") else None
            if temperature is None and name.startswith("nvme"):
                temperature = nvme_temp
            disks.append(
                {
                    "name": name,
                    "model": _read(folder / "device" / "model") or None,
                    "vendor": _read(folder / "device" / "vendor") or None,
                    "serial": _read(folder / "device" / "serial") or None,
                    "firmware": _read(folder / "device" / "firmware_rev") or None,
                    "size_bytes": size_sectors * 512,
                    "rotational": bool(rotational) if rotational is not None else None,
                    "removable": bool(_int(folder / "removable") or 0),
                    "temperature_c": temperature,
                    "mountpoints": [
                        {
                            "mountpoint": mount.get("mountpoint"),
                            "fstype": mount.get("fstype"),
                            "used_bytes": mount.get("used_bytes"),
                            "total_bytes": mount.get("total_bytes"),
                            "percent": mount.get("percent"),
                            "inodes_percent": mount.get("inodes_percent"),
                        }
                        for mount in disk_mounts
                    ],
                    "usage_percent": usage,
                    "inodes_percent": inodes,
                    "smart": smart,
                }
            )
        return disks

    def _power(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
        base = Path(self.settings.sysfs) / "class" / "power_supply"
        battery: dict[str, Any] | None = None
        ac: dict[str, Any] | None = None
        ups: list[dict[str, Any]] = []
        if not base.is_dir():
            return battery, ac, ups
        for folder in sorted(base.iterdir(), key=lambda item: item.name):
            if not folder.is_dir():
                continue
            kind = _read(folder / "type").lower()
            if kind == "battery" and battery is None:
                energy_now = _int(folder / "energy_now")
                energy_full = _int(folder / "energy_full")
                energy_design = _int(folder / "energy_full_design")
                power_now = _int(folder / "power_now")
                capacity = _int(folder / "capacity")
                voltage = _int(folder / "voltage_now")
                status = _read(folder / "status")
                health = None
                if energy_full and energy_design:
                    health = round(energy_full / energy_design * 100, 1)
                runtime = None
                if energy_now and power_now and power_now > 0:
                    runtime = round(energy_now / power_now * 60, 0)
                battery = {
                    "name": folder.name,
                    "percent": capacity,
                    "status": status or None,
                    "manufacturer": _read(folder / "manufacturer") or None,
                    "model": _read(folder / "model_name") or None,
                    "serial": _read(folder / "serial_number") or None,
                    "voltage_v": round(voltage / 1_000_000, 3) if voltage else None,
                    "power_w": round(power_now / 1_000_000, 2) if power_now else None,
                    "energy_wh": round(energy_now / 1_000_000, 1) if energy_now else None,
                    "energy_full_wh": round(energy_full / 1_000_000, 1) if energy_full else None,
                    "health_percent": health,
                    "cycle_count": _int(folder / "cycle_count"),
                    "runtime_minutes": runtime,
                }
            elif kind in {"mains", "usb"} and ac is None:
                ac = {
                    "name": folder.name,
                    "online": (_int(folder / "online") or 0) == 1,
                }
            elif kind == "ups":
                ups.append(
                    {
                        "name": folder.name,
                        "status": _read(folder / "status") or None,
                        "capacity": _int(folder / "capacity"),
                    }
                )
        return battery, ac, ups

    def _updates(self) -> dict[str, Any]:
        if self._updates_cache is not None and time.monotonic() - self._updates_at < 3600:
            return self._updates_cache
        root = Path(self.settings.rootfs)
        reboot = (root / "run" / "reboot-required").exists() or (
            root / "var" / "run" / "reboot-required"
        ).exists()
        lists = root / "var" / "lib" / "apt" / "lists"
        last_update = None
        if lists.is_dir():
            stamps = [
                path.stat().st_mtime
                for path in lists.glob("*_InRelease")
                if path.is_file()
            ]
            if stamps:
                last_update = datetime.fromtimestamp(max(stamps), tz=UTC).isoformat()

        installed: dict[tuple[str, str], str] = {}
        status_path = root / "var" / "lib" / "dpkg" / "status"
        for lines in _paragraphs(status_path):
            fields = _fields(lines)
            name = fields.get("Package")
            version = fields.get("Version")
            status = fields.get("Status", "")
            if name and version and "installed" in status:
                installed[(name, fields.get("Architecture", "amd64"))] = version

        candidates: dict[tuple[str, str], str] = {}
        if lists.is_dir():
            for path in lists.glob("*_binary-*_Packages"):
                for lines in _paragraphs(path):
                    fields = _fields(lines)
                    name = fields.get("Package")
                    version = fields.get("Version")
                    arch = fields.get("Architecture")
                    if not name or not version or not arch:
                        continue
                    key = (name, arch)
                    current = candidates.get(key)
                    if current is None or compare_versions(version, current) > 0:
                        candidates[key] = version

        available: int | None = None
        if installed and candidates:
            available = 0
            for (name, arch), version in installed.items():
                candidate = candidates.get((name, arch))
                if candidate is None:
                    candidate = candidates.get((name, "all"))
                if candidate is not None and compare_versions(candidate, version) > 0:
                    available += 1

        result = {
            "reboot_required": reboot,
            "last_apt_update": last_update,
            "available": available,
            "installed": len(installed),
            "reason": None
            if available is not None
            else "recuento de actualizaciones no disponible (sin listas de apt legibles)",
        }
        self._updates_cache = result
        self._updates_at = time.monotonic()
        return result

    # --- API -------------------------------------------------------------
    def payload(self) -> dict[str, Any]:
        if not self.settings.hardware_enabled:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Hardware",
                    "value": "—",
                    "detail": "Monitor deshabilitado",
                },
                "detail": {"enabled": False, "error": "deshabilitado"},
            }

        mounts = self._mounts()
        disks = self._disks(mounts)
        battery, ac, ups = self._power()
        root = next((mount for mount in mounts if mount.get("mountpoint") == "/"), None)
        root_inodes = root.get("inodes_percent") if root else None
        status = "ok"
        if root_inodes is not None:
            status = status_for(
                float(root_inodes),
                self.settings.hardware_inodes_warn_percent,
                self.settings.hardware_inodes_critical_percent,
            )
        if battery and battery.get("percent") is not None and battery.get("status") == "Discharging":
            status = worst(
                [
                    status,
                    "critical" if float(battery["percent"]) <= 10 else "warn"
                    if float(battery["percent"]) <= 25
                    else "ok",
                ]
            )
        for disk in disks:
            smart_raw = disk.get("smart")
            smart: dict[str, Any] = smart_raw if isinstance(smart_raw, dict) else {}
            if not smart.get("available"):
                continue
            if smart.get("status") == "failed":
                status = "critical"
            used = smart.get("percentage_used")
            if isinstance(used, (int, float)):
                if used >= 95:
                    status = "critical"
                elif used >= 85:
                    status = worst([status, "warn"])
            if isinstance(smart.get("media_errors"), (int, float)) and smart["media_errors"] > 0:
                status = worst([status, "warn"])

        if battery:
            bits = [str(battery.get("status") or "—")]
            if battery.get("voltage_v"):
                bits.append(f"{battery['voltage_v']:.2f} V")
            if battery.get("cycle_count") is not None:
                bits.append(f"{battery['cycle_count']} ciclos")
            summary = {
                "label": "Batería",
                "value": battery.get("percent") if battery.get("percent") is not None else "—",
                "unit": "%",
                "detail": " · ".join(bits),
            }
        else:
            summary = {
                "label": "Discos",
                "value": len(disks),
                "unit": "uds",
                "detail": f"{len(disks)} discos · inodos {root_inodes or '—'}%",
            }

        detail = {
            "enabled": True,
            "host": self._dmi(),
            "disks": disks,
            "disk_count": len(disks),
            "battery": battery,
            "ac": ac,
            "ups": {"detected": bool(ups), "devices": ups},
            "mounts": mounts,
            "root_inodes_percent": root_inodes,
            "updates": self._updates(),
            "smart_available": any(bool(disk["smart"].get("available")) for disk in disks),
            "sampled_at": datetime.now(UTC).isoformat(),
            "error": None,
        }
        return {"status": status, "summary": summary, "detail": detail}

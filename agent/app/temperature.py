"""Sensores de temperatura y ventiladores del host (solo lectura)."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.metrics import status_for


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


class TemperatureMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _hwmon(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        sensors: list[dict[str, Any]] = []
        fans: list[dict[str, Any]] = []
        base = Path(self.settings.sysfs) / "class" / "hwmon"
        if not base.is_dir():
            return sensors, fans
        for folder in sorted(base.iterdir(), key=lambda item: item.name):
            if not folder.is_dir():
                continue
            chip = _read(folder / "name") or folder.name
            for path in sorted(folder.glob("temp*_input")):
                raw = _int(path)
                if raw is None or raw <= 0:
                    continue
                stem = path.name.removesuffix("_input")
                label = _read(folder / f"{stem}_label") or chip
                maximum = _int(folder / f"{stem}_max")
                critical = _int(folder / f"{stem}_crit")
                sensors.append(
                    {
                        "id": f"{folder.name}:{stem}",
                        "chip": chip,
                        "label": label,
                        "temp_c": round(raw / 1000, 1),
                        "max_c": round(maximum / 1000, 1) if maximum and maximum > 0 else None,
                        "crit_c": round(critical / 1000, 1) if critical and critical > 0 else None,
                        "source": "hwmon",
                    }
                )
            for path in sorted(folder.glob("fan*_input")):
                raw = _int(path)
                if raw is None:
                    continue
                stem = path.name.removesuffix("_input")
                label = _read(folder / f"{stem}_label") or chip
                fans.append({"id": f"{folder.name}:{stem}", "chip": chip, "label": label, "rpm": raw})
        return sensors, fans

    def _thermal_zones(self) -> list[dict[str, Any]]:
        sensors: list[dict[str, Any]] = []
        base = Path(self.settings.sysfs) / "class" / "thermal"
        if not base.is_dir():
            return sensors
        for folder in sorted(base.glob("thermal_zone*")):
            raw = _int(folder / "temp")
            if raw is None or raw <= 0:
                continue
            label = _read(folder / "type") or folder.name
            sensors.append(
                {
                    "id": folder.name,
                    "chip": "thermal",
                    "label": label,
                    "temp_c": round(raw / 1000, 1),
                    "max_c": None,
                    "crit_c": None,
                    "source": "thermal",
                }
            )
        return sensors

    def snapshot(self) -> dict[str, Any]:
        if not self.settings.temperature_enabled:
            return {
                "enabled": False,
                "sensors": [],
                "fans": [],
                "max_c": None,
                "sensor_count": 0,
                "fan_count": 0,
                "error": "Monitor deshabilitado",
                "sampled_at": datetime.now(UTC).isoformat(),
            }
        sensors, fans = self._hwmon()
        if not sensors:
            sensors = self._thermal_zones()
        sensors.sort(key=lambda item: float(item["temp_c"]), reverse=True)
        max_c = float(sensors[0]["temp_c"]) if sensors else None
        status = "unknown"
        if max_c is not None:
            status = status_for(
                max_c,
                self.settings.temperature_warn_c,
                self.settings.temperature_critical_c,
            )
        return {
            "enabled": True,
            "sensors": sensors,
            "fans": fans,
            "max_c": max_c,
            "status": status,
            "sensor_count": len(sensors),
            "fan_count": len(fans),
            "warn_c": self.settings.temperature_warn_c,
            "critical_c": self.settings.temperature_critical_c,
            "error": None if sensors else "sin sensores de temperatura",
            "sampled_at": datetime.now(UTC).isoformat(),
        }

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Temperatura",
                    "value": "—",
                    "unit": "°C",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }
        if snap["max_c"] is None:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Temperatura",
                    "value": "—",
                    "unit": "°C",
                    "detail": snap["error"] or "Sin sensores",
                },
                "detail": snap,
            }
        max_c = float(snap["max_c"])
        detail = (
            f"{snap['sensor_count']} sensores · {snap['fan_count']} ventiladores"
            if snap["fan_count"]
            else f"{snap['sensor_count']} sensores"
        )
        return {
            "status": snap["status"],
            "summary": {
                "label": "Máxima",
                "value": max_c,
                "unit": "°C",
                "detail": detail,
            },
            "detail": snap,
        }

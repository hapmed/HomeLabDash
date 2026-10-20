"""Inventario de dispositivos de la red local.

Fuente actual: tabla ARP del host (montada en `/host/proc/1/net/arp`). Se
sondean las IPs de la red con datagramas UDP baratos para forzar la resolución
ARP y se registra presencia, primera/última vez visto y tiempo acumulado.

El router Mercusys AC12 no expone consumo acumulado por dispositivo. La
integración con el router (credenciales) añadirá nombres reales, SSID y una
estimación de consumo por muestreo de sus velocidades.
"""

import copy
import ipaddress
import json
import logging
import socket
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from netaddr import EUI
from netaddr.core import NotRegisteredError

from app.config import Settings
from app.router import MercusysRouter, RouterError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArpEntry:
    ip: str
    mac: str
    device: str
    flags: int


def _iso(moment: datetime | None = None) -> str:
    return (moment or datetime.now(UTC)).isoformat()


def parse_arp(text: str) -> list[ArpEntry]:
    entries: list[ArpEntry] = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        ip, hw_type, flags, mac, _mask, device = parts[:6]
        if hw_type != "0x1":
            continue
        try:
            flags_value = int(flags, 16)
        except ValueError:
            continue
        # 0x2 = entrada completa; descarta INCOMPLETE/FAILED.
        if not flags_value & 0x2:
            continue
        normalized = mac.lower()
        if normalized in {"00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"}:
            continue
        entries.append(ArpEntry(ip=ip, mac=normalized, device=device, flags=flags_value))
    return entries


def is_random_mac(mac: str) -> bool:
    try:
        first = int(mac.split(":")[0], 16)
    except (ValueError, IndexError):
        return False
    return bool(first & 0x02)


def vendor_for(mac: str, cache: dict[str, str]) -> str:
    if mac in cache:
        return cache[mac]
    if is_random_mac(mac):
        vendor = "MAC aleatoria"
    else:
        try:
            registration = EUI(mac).oui.registration()
            vendor = str(getattr(registration, "org", "")).split(",")[0].strip()
            if not vendor:
                vendor = "Desconocido"
            if len(vendor) > 48:
                vendor = vendor[:48].rstrip() + "…"
        except (NotRegisteredError, ValueError):
            vendor = "Desconocido"
    cache[mac] = vendor
    return vendor


def _device_name(vendor: str, ip: str) -> str:
    if vendor not in {"Desconocido", "MAC aleatoria"}:
        return vendor
    return f"Dispositivo {ip.split('.')[-1]}"


def update_registry(
    registry: dict[str, dict[str, Any]],
    observed: dict[str, dict[str, Any]],
    now: datetime,
    interval_seconds: int,
) -> dict[str, dict[str, Any]]:
    """Actualiza presencia y tiempos. `observed` está indexado por MAC."""
    now_iso = now.isoformat()
    max_delta = max(1, interval_seconds) * 2

    for mac, data in observed.items():
        is_online = bool(data.get("online", True))
        entry = registry.get(mac)
        if entry is None:
            registry[mac] = {
                "mac": mac,
                "ip": data["ip"],
                "name": data["name"],
                "vendor": data["vendor"],
                "type": data.get("type", "device"),
                "online": is_online,
                "first_seen": now_iso,
                "last_seen": now_iso if is_online else None,
                "connected_since": now_iso if is_online else None,
                "online_seconds": 0.0,
                "sessions": 1 if is_online else 0,
                "bytes": float(data.get("bytes", 0)),
                "rate_up_bps": int(data.get("rate_up_bps", 0)),
                "rate_down_bps": int(data.get("rate_down_bps", 0)),
                "connection": data.get("connection"),
                "blocked": bool(data.get("blocked", False)),
                "last_router_sample_at": data.get("last_router_sample_at"),
            }
            continue

        delta = 0.0
        previous_raw = entry.get("last_seen")
        if previous_raw:
            try:
                previous = datetime.fromisoformat(previous_raw)
                delta = max(0.0, (now - previous).total_seconds())
            except ValueError:
                delta = 0.0

        if is_online:
            if not entry.get("online"):
                entry["connected_since"] = now_iso
                entry["sessions"] = int(entry.get("sessions", 0)) + 1
            else:
                entry["online_seconds"] = float(entry.get("online_seconds", 0.0)) + min(
                    delta, max_delta
                )
            entry["last_seen"] = now_iso
        elif entry.get("online"):
            entry["online_seconds"] = float(entry.get("online_seconds", 0.0)) + min(
                delta, max_delta
            )
            entry["rate_up_bps"] = 0
            entry["rate_down_bps"] = 0

        entry.update(
            {
                "ip": data["ip"],
                "name": data["name"],
                "vendor": data["vendor"],
                "type": data.get("type", entry.get("type", "device")),
                "online": is_online,
            }
        )
        for key in (
            "bytes",
            "rate_up_bps",
            "rate_down_bps",
            "connection",
            "blocked",
            "last_router_sample_at",
        ):
            if key in data:
                entry[key] = data[key]

    for mac, entry in registry.items():
        if mac in observed or not entry.get("online"):
            continue
        delta = 0.0
        previous_raw = entry.get("last_seen")
        if previous_raw:
            try:
                previous = datetime.fromisoformat(previous_raw)
                delta = max(0.0, (now - previous).total_seconds())
            except ValueError:
                pass
        entry["online_seconds"] = float(entry.get("online_seconds", 0.0)) + min(delta, max_delta)
        entry["online"] = False
        entry["rate_up_bps"] = 0
        entry["rate_down_bps"] = 0

    return registry


class NetworkMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._vendor_cache: dict[str, str] = {}
        self._registry: dict[str, dict[str, Any]] = {}
        self._network = ipaddress.ip_network(settings.network_cidr, strict=False)
        self._state: dict[str, Any] = {
            "enabled": settings.network_monitor_enabled,
            "network_name": settings.network_name
            or f"Red local {settings.network_cidr}",
            "cidr": settings.network_cidr,
            "gateway": settings.network_gateway_ip,
            "interface": None,
            "last_scan_at": None,
            "scan_error": None,
            "source": "arp",
            "consumption_available": False,
            "router": {"enabled": False, "ssid": None, "model": None, "error": None},
        }
        self._router: MercusysRouter | None = None
        if settings.router_enabled and settings.router_password:
            self._router = MercusysRouter(
                settings.router_url,
                settings.router_password,
                info_refresh_seconds=settings.router_info_refresh_seconds,
            )
            self._state["router"]["enabled"] = True
        self._router_next_attempt = 0.0
        self._router_error: str | None = None
        self._ssid: str | None = None
        self._router_model: str | None = None
        self._load_registry()
        self._warning_logged = False

    # --- ciclo de vida ---------------------------------------------------
    def start(self) -> None:
        if not self.settings.network_monitor_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="network-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            self._scan()
            if self._stop.wait(max(10, self.settings.network_scan_seconds)):
                break

    # --- sondeo ----------------------------------------------------------
    def _probe(self) -> None:
        addresses = [str(ip) for ip in self._network.hosts()]
        gateway = self.settings.network_gateway_ip
        if gateway not in addresses:
            addresses.append(gateway)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            for address in addresses:
                try:
                    sock.sendto(b"", (address, 9))
                except OSError:
                    continue
        finally:
            sock.close()

    def _read_arp(self) -> str:
        candidates = [self.settings.network_arp_path, "/host/proc/net/arp", "/proc/net/arp"]
        for candidate in candidates:
            try:
                return Path(candidate).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        raise OSError("no se puede leer la tabla ARP del host")

    def _scan(self) -> None:
        try:
            self._probe()
            time.sleep(max(0.0, self.settings.network_probe_wait_seconds))
            entries = parse_arp(self._read_arp())
        except (OSError, ValueError) as exc:
            with self._lock:
                self._state["scan_error"] = f"no se pudo escanear la red ({type(exc).__name__})"
                self._state["last_scan_at"] = _iso()
            return

        observed: dict[str, dict[str, Any]] = {}
        interface = None
        for entry in entries:
            try:
                address = ipaddress.ip_address(entry.ip)
            except ValueError:
                continue
            if address not in self._network:
                continue
            if interface is None and entry.device:
                interface = entry.device
            if entry.ip == self.settings.network_gateway_ip:
                continue  # se añade como router con nombre propio
            vendor = vendor_for(entry.mac, self._vendor_cache)
            observed[entry.mac] = {
                "ip": entry.ip,
                "name": _device_name(vendor, entry.ip),
                "vendor": vendor,
                "type": "device",
            }

        now = datetime.now(UTC)
        router_ok = False
        if self._router is not None and time.monotonic() >= self._router_next_attempt:
            try:
                router_snapshot = self._router.fetch()
                router_ok = True
                self._router_error = None
                self._router_next_attempt = 0.0
                self._ssid = router_snapshot.ssid or self._ssid
                self._router_model = router_snapshot.model
                for device in router_snapshot.devices:
                    existing = self._registry.get(device.mac, {})
                    previous_sample = existing.get("last_router_sample_at")
                    elapsed = 0.0
                    if previous_sample:
                        try:
                            elapsed = max(
                                0.0, (now - datetime.fromisoformat(previous_sample)).total_seconds()
                            )
                        except ValueError:
                            elapsed = 0.0
                    elapsed = min(elapsed, max(1, self.settings.network_scan_seconds) * 2)
                    total_bytes = float(existing.get("bytes", 0.0))
                    if device.online:
                        total_bytes += (device.up_bps + device.down_bps) * elapsed
                    vendor = existing.get("vendor") or vendor_for(device.mac, self._vendor_cache)
                    is_server = device.ip == self.settings.network_server_ip
                    fallback_name = (
                        self.settings.network_server_name
                        if is_server
                        else _device_name(vendor, device.ip)
                    )
                    observed[device.mac] = {
                        "ip": device.ip,
                        "name": device.name or fallback_name,
                        "vendor": "Servidor" if is_server else vendor,
                        "type": "server" if is_server else "device",
                        "connection": device.connection,
                        "online": device.online,
                        "blocked": device.blocked,
                        "rate_up_bps": device.up_bps if device.online else 0,
                        "rate_down_bps": device.down_bps if device.online else 0,
                        "bytes": round(total_bytes, 1),
                        "last_router_sample_at": now.isoformat(),
                    }
            except RouterError as exc:
                self._router_error = str(exc)
                self._router_next_attempt = (
                    time.monotonic() + max(60, self.settings.router_retry_seconds)
                )
                logger.warning("no se pudo leer el router: %s", exc)

        gateway_vendor = "Router"
        gateway_entry = next(
            (entry for entry in entries if entry.ip == self.settings.network_gateway_ip), None
        )
        if gateway_entry is not None:
            gateway_vendor = vendor_for(gateway_entry.mac, self._vendor_cache)
            previous_entry = self._registry.get(gateway_entry.mac, {})
            observed[gateway_entry.mac] = {
                "ip": gateway_entry.ip,
                "name": self.settings.network_gateway_name,
                "vendor": gateway_vendor,
                "type": "router",
                "connection": "Router",
                "bytes": float(previous_entry.get("bytes", 0.0)),
            }
            interface = interface or gateway_entry.device

        server_mac = self._server_mac(interface)
        if server_mac and server_mac not in observed:
            previous_entry = self._registry.get(server_mac, {})
            observed[server_mac] = {
                "ip": self.settings.network_server_ip,
                "name": self.settings.network_server_name,
                "vendor": "Servidor",
                "type": "server",
                "connection": "Cable",
                "bytes": float(previous_entry.get("bytes", 0.0)),
            }

        with self._lock:
            self._registry = update_registry(
                self._registry, observed, now, self.settings.network_scan_seconds
            )
            self._state["interface"] = interface
            self._state["last_scan_at"] = now.isoformat()
            self._state["scan_error"] = None
            self._state["source"] = "router" if router_ok else "arp"
            self._state["consumption_available"] = router_ok
            self._state["network_name"] = (
                self._ssid
                or self.settings.network_name
                or f"Red local {self.settings.network_cidr}"
            )
            self._state["router"] = {
                "enabled": self._router is not None,
                "ssid": self._ssid,
                "model": self._router_model,
                "error": self._router_error,
            }
            registry_snapshot = copy.deepcopy(self._registry)
        self._save_registry(registry_snapshot)

    def _server_mac(self, interface: str | None) -> str | None:
        if not interface:
            return None
        try:
            raw = Path(
                f"{self.settings.network_host_sys}/class/net/{interface}/address"
            ).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not raw or raw == "00:00:00:00:00:00":
            return None
        return raw.lower()

    # --- persistencia ----------------------------------------------------
    def _load_registry(self) -> None:
        path = Path(self.settings.network_history_path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        devices = payload.get("devices") if isinstance(payload, dict) else None
        if isinstance(devices, dict):
            self._registry = {
                str(mac): entry
                for mac, entry in devices.items()
                if isinstance(entry, dict) and entry.get("mac")
            }

    def _save_registry(self, registry: dict[str, dict[str, Any]]) -> None:
        path = Path(self.settings.network_history_path)
        payload = {
            "version": 1,
            "updated_at": _iso(),
            "network": self._state["network_name"],
            "devices": registry,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(path)
        except OSError:
            if not self._warning_logged:
                self._warning_logged = True
                logger.warning("no se puede guardar el inventario de red en %s", path)

    # --- API -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            devices = copy.deepcopy(self._registry)
            state = copy.deepcopy(self._state)

        items = sorted(
            devices.values(),
            key=lambda device: (
                not bool(device.get("online")),
                -float(device.get("bytes", 0) or 0),
                str(device.get("name", "")).lower(),
            ),
        )
        online = sum(1 for device in items if device.get("online"))
        with_bytes = [device for device in items if float(device.get("bytes", 0) or 0) > 0]
        top = max(with_bytes, key=lambda device: float(device.get("bytes", 0)), default=None)
        top_consumer = (
            {
                "name": top.get("name") or "Dispositivo",
                "mac": top.get("mac"),
                "ip": top.get("ip"),
                "bytes": round(float(top.get("bytes", 0)), 1),
            }
            if top
            else None
        )
        router = state.get("router") or {}
        if state.get("consumption_available"):
            warning = ""
        elif router.get("enabled"):
            warning = (
                "No se pudo leer el router"
                + (f": {router.get('error')}" if router.get("error") else "")
                + ". Se muestra solo la presencia detectada por ARP."
            )
        else:
            warning = (
                "El router no expone consumo acumulado por dispositivo. "
                "Para estimarlo hace falta configurar el acceso al router."
            )

        return {
            **state,
            "counts": {"online": online, "total": len(items)},
            "devices": items,
            "top_consumer": top_consumer,
            "consumption_note": (
                f"Consumo estimado acumulado desde que se activó el monitor, "
                f"muestreando las tasas del router cada {self.settings.network_scan_seconds} s."
                if state.get("consumption_available")
                else ""
            ),
            "scan_interval_seconds": self.settings.network_scan_seconds,
            "warning": warning,
        }

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Dispositivos",
                    "value": "—",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }

        if snap["scan_error"]:
            status = "warn"
        elif snap["router"].get("enabled") and snap["router"].get("error"):
            status = "warn"
        elif snap["counts"]["online"] == 0:
            status = "warn"
        else:
            status = "ok"

        return {
            "status": status,
            "summary": {
                "label": "En línea",
                "value": snap["counts"]["online"],
                "detail": (
                    f"{snap['counts']['total']} conocidos · {snap['network_name']}"
                    if snap["counts"]["total"]
                    else "Sin dispositivos detectados"
                ),
            },
            "detail": snap,
        }

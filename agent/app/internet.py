"""Monitor de Internet: IP pública, latencia, velocidad e histórico.

- Comprobación de conectividad y latencia cada minuto (TCP a 1.1.1.1).
- Test de velocidad completo cada hora contra Cloudflare (descarga y subida).
- Historial persistente en `/data/internet-history.json` (volumen Docker).
"""

import copy
import json
import logging
import socket
import statistics
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

LATENCY_TARGETS: tuple[tuple[str, int], ...] = (("1.1.1.1", 443), ("8.8.8.8", 53))
STATUS_RANK = {"ok": 0, "warn": 1, "critical": 2, "unknown": 3}


def parse_trace(text: str) -> dict[str, str]:
    """Convierte `clave=valor` de cdn-cgi/trace en un diccionario."""
    data: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def mbps(num_bytes: int, seconds: float) -> float:
    if num_bytes <= 0 or seconds <= 0:
        return 0.0
    return round(num_bytes * 8 / seconds / 1_000_000, 1)


def adaptive_bytes(
    configured: int,
    last_mbps: float | None,
    target_seconds: float = 5.0,
    minimum: int = 1_000_000,
) -> int:
    """Ajusta el tamaño de la prueba para que dure ~`target_seconds`.

    Evita gastar 10 MB en una conexión lenta y permite medir mejor una rápida.
    """
    if not last_mbps or last_mbps <= 0:
        return configured
    target = int(last_mbps * 1_000_000 / 8 * target_seconds)
    return max(minimum, min(configured, target))


def internet_status(
    *,
    online: bool,
    latency_ms: float | None,
    failures: int,
    warn_ms: float,
    critical_ms: float,
) -> str:
    if not online:
        return "critical"
    if failures >= 3:
        return "critical"
    if latency_ms is not None and latency_ms >= critical_ms:
        return "critical"
    if failures > 0:
        return "warn"
    if latency_ms is not None and latency_ms >= warn_ms:
        return "warn"
    return "ok"


def _iso(moment: datetime | None = None) -> str:
    return (moment or datetime.now(UTC)).isoformat()


class InternetMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._history: list[dict[str, Any]] = self._load_history()
        self._history_warning_logged = False
        self._last_ip_refresh = 0.0
        self._state: dict[str, Any] = {
            "enabled": settings.internet_monitor_enabled,
            "online": False,
            "checked_at": None,
            "latency_ms": None,
            "jitter_ms": None,
            "public_ip": None,
            "previous_ip": None,
            "ip_changed_at": None,
            "ip_version": None,
            "isp": None,
            "city": None,
            "region": None,
            "country": None,
            "colo": None,
            "http_version": None,
            "tls": None,
            "download_mbps": None,
            "upload_mbps": None,
            "last_test_at": None,
            "next_test_at": None,
            "last_error": None,
            "consecutive_failures": 0,
        }

    # --- ciclo de vida ---------------------------------------------------
    def start(self) -> None:
        if not self.settings.internet_monitor_enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="internet-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _run(self) -> None:
        self._check_connectivity(refresh_ip=True)
        check_seconds = max(10, self.settings.internet_check_seconds)
        next_check = time.monotonic() + check_seconds
        next_speed_test = time.monotonic() + 15
        self._set_next_test(next_speed_test)

        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_check:
                self._check_connectivity()
                next_check = now + check_seconds
            if now >= next_speed_test:
                self._speed_test()
                next_speed_test = now + max(1, self.settings.internet_speedtest_minutes) * 60
                self._set_next_test(next_speed_test)

            pause = min(next_check, next_speed_test) - time.monotonic()
            if self._stop.wait(max(1.0, pause)):
                break

    def _set_next_test(self, deadline: float) -> None:
        with self._lock:
            self._state["next_test_at"] = _iso(
                datetime.now(UTC) + timedelta(seconds=max(0, deadline - time.monotonic()))
            )

    # --- conectividad / IP ----------------------------------------------
    def _tcp_latency(self) -> tuple[float | None, float | None]:
        samples: list[float] = []
        for _ in range(3):
            for host, port in LATENCY_TARGETS:
                start = time.perf_counter()
                try:
                    with socket.create_connection((host, port), timeout=3):
                        samples.append((time.perf_counter() - start) * 1000)
                    break
                except OSError:
                    continue

        if not samples:
            return None, None
        latency = round(statistics.median(samples), 1)
        jitter = round(statistics.pstdev(samples), 1) if len(samples) > 1 else 0.0
        return latency, jitter

    def _check_connectivity(self, refresh_ip: bool = False) -> None:
        latency, jitter = self._tcp_latency()
        now = time.time()
        with self._lock:
            self._state["online"] = latency is not None
            self._state["latency_ms"] = latency
            self._state["jitter_ms"] = jitter
            self._state["checked_at"] = _iso()
        if latency is None:
            return
        if refresh_ip or now - self._last_ip_refresh >= self.settings.internet_ip_refresh_minutes * 60:
            self._last_ip_refresh = now
            self._refresh_ip()

    def _refresh_ip(self) -> None:
        try:
            response = httpx.get(
                self.settings.internet_trace_url,
                timeout=httpx.Timeout(8),
                follow_redirects=True,
                trust_env=False,
                headers={"User-Agent": "HomeLabDash-Agent/0.1"},
            )
            response.raise_for_status()
            trace = parse_trace(response.text)
        except (httpx.HTTPError, ValueError):
            return

        ip = trace.get("ip")
        info: dict[str, Any] = {}
        if ip and self.settings.internet_ipinfo_enabled:
            try:
                info_response = httpx.get(
                    f"{self.settings.internet_ipinfo_url}/{ip}/json",
                    timeout=httpx.Timeout(6),
                    follow_redirects=True,
                    trust_env=False,
                    headers={"User-Agent": "HomeLabDash-Agent/0.1"},
                )
                info_response.raise_for_status()
                payload = info_response.json()
                if isinstance(payload, dict):
                    info = payload
            except (httpx.HTTPError, ValueError):
                info = {}

        with self._lock:
            previous = self._state["public_ip"]
            if ip and previous and ip != previous:
                self._state["previous_ip"] = previous
                self._state["ip_changed_at"] = _iso()
            if ip:
                self._state["public_ip"] = ip
                self._state["ip_version"] = "IPv6" if ":" in ip else "IPv4"
            self._state["colo"] = trace.get("colo")
            self._state["country"] = trace.get("loc") or info.get("country")
            self._state["http_version"] = trace.get("http")
            self._state["tls"] = trace.get("tls")
            self._state["isp"] = info.get("org")
            self._state["city"] = info.get("city")
            self._state["region"] = info.get("region")

    # --- test de velocidad ----------------------------------------------
    def _download(self, size: int) -> float:
        url = f"{self.settings.internet_speedtest_url}/__down?bytes={size}"
        start = time.perf_counter()
        received = 0
        with httpx.stream(
            "GET",
            url,
            timeout=httpx.Timeout(connect=8, read=90, write=10, pool=8),
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "HomeLabDash-Agent/0.1"},
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                received += len(chunk)
        return mbps(received, time.perf_counter() - start)

    def _upload(self, size: int) -> float:
        payload = b"\0" * size
        start = time.perf_counter()
        response = httpx.post(
            f"{self.settings.internet_speedtest_url}/__up",
            content=payload,
            timeout=httpx.Timeout(connect=8, read=30, write=90, pool=8),
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "HomeLabDash-Agent/0.1"},
        )
        response.raise_for_status()
        return mbps(size, time.perf_counter() - start)

    def _speed_test(self) -> None:
        with self._lock:
            online = self._state["online"]
            last_download = self._state["download_mbps"]
            last_upload = self._state["upload_mbps"]
            latency = self._state["latency_ms"]

        if not online:
            self._record_failure("sin conexión")
            return

        download_size = adaptive_bytes(self.settings.internet_download_bytes, last_download, 6)
        upload_size = adaptive_bytes(
            self.settings.internet_upload_bytes, last_upload, 4, minimum=512_000
        )
        try:
            download = self._download(download_size)
            upload = self._upload(upload_size)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            self._record_failure(f"fallo de medición ({type(exc).__name__})")
            return

        sample = {
            "at": _iso(),
            "download_mbps": download,
            "upload_mbps": upload,
            "latency_ms": latency,
        }
        with self._lock:
            self._history.append(sample)
            self._history = self._history[-max(1, self.settings.internet_history_size) :]
            self._state["download_mbps"] = download
            self._state["upload_mbps"] = upload
            self._state["last_test_at"] = sample["at"]
            self._state["last_error"] = None
            self._state["consecutive_failures"] = 0
        self._save_history()

    def _record_failure(self, message: str) -> None:
        with self._lock:
            self._state["last_error"] = message
            self._state["consecutive_failures"] += 1
            self._state["next_test_at"] = _iso(
                datetime.now(UTC) + timedelta(minutes=max(1, self.settings.internet_speedtest_minutes))
            )

    # --- historial -------------------------------------------------------
    def _load_history(self) -> list[dict[str, Any]]:
        path = Path(self.settings.internet_history_path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, list):
            return []
        history = [
            item
            for item in raw
            if isinstance(item, dict)
            and isinstance(item.get("at"), str)
            and isinstance(item.get("download_mbps"), (int, float))
        ]
        return history[-max(1, self.settings.internet_history_size) :]

    def _save_history(self) -> None:
        path = Path(self.settings.internet_history_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._history, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(path)
        except OSError:
            if not self._history_warning_logged:
                self._history_warning_logged = True
                logger.warning("no se puede guardar el histórico de Internet en %s", path)

    # --- API -------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = copy.deepcopy(self._state)
            history = copy.deepcopy(self._history)
        data["history"] = history
        data["history_limit"] = self.settings.internet_history_size
        data["test_interval_minutes"] = self.settings.internet_speedtest_minutes
        data["check_interval_seconds"] = self.settings.internet_check_seconds
        data["download_test_bytes"] = self.settings.internet_download_bytes
        data["upload_test_bytes"] = self.settings.internet_upload_bytes
        return data

    def payload(self) -> dict[str, Any]:
        snap = self.snapshot()

        if not snap["enabled"]:
            return {
                "status": "unknown",
                "summary": {
                    "label": "Internet",
                    "value": "—",
                    "unit": "Mbps",
                    "detail": "Monitor deshabilitado",
                },
                "detail": snap,
            }

        status = internet_status(
            online=bool(snap["online"]),
            latency_ms=snap["latency_ms"],
            failures=int(snap["consecutive_failures"]),
            warn_ms=self.settings.internet_latency_warn_ms,
            critical_ms=self.settings.internet_latency_critical_ms,
        )

        if not snap["online"]:
            summary = {
                "label": "Bajada",
                "value": "—",
                "unit": "Mbps",
                "detail": "Sin conexión a Internet",
            }
        elif snap["download_mbps"] is None:
            summary = {
                "label": "Bajada",
                "value": "—",
                "unit": "Mbps",
                "detail": "Midiendo velocidad…",
            }
        else:
            latency = snap["latency_ms"]
            summary = {
                "label": "Bajada",
                "value": snap["download_mbps"],
                "unit": "Mbps",
                "detail": (
                    f"Subida {snap['upload_mbps']} Mbps · "
                    f"{latency if latency is not None else '—'} ms · "
                    f"IP {snap['public_ip'] or '—'}"
                ),
            }

        return {"status": status, "summary": summary, "detail": snap}

"""Cliente mínimo del protocolo TDDP del Mercusys AC12.

Solo lectura: inicia sesión, pide el bloque de dispositivos y el SSID. No
configura nada ni guarda la clave Wi-Fi que el router incluye en su respuesta.
"""

import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

SALT = "RDpbLfCPsJZ7fiv"
ALPHABET = (
    "yLwVl0zKqws7LgKPRQ84Mdt708T1qQ3Ha7xv3H7NyU84p21BriUWBU43odz3iP4rBL3cD02KZ"
    "ciXTysVXiV8ngg6vL48rPJyAUw0HurW20xqxv9aYb4M9wK1Ae0wlro510qXeU07kV57fQMc8L6"
    "aLgMLwygtc0F10a0Dg70TOoouyFhdysuRMO51yY5ZlOZZLEal1h0t9YQW0Ko7oBwmCAHoic4H"
    "YbUyVeU3sfQ1xtXcPcf1aT303wAQhv66qzW"
)
TYPE_LABELS = {
    "0": "Cable",
    "1": "2.4 GHz",
    "2": "2.4 GHz",
    "3": "5 GHz",
    "4": "5 GHz",
}


class RouterError(RuntimeError):
    """Error genérico del router."""


class RouterAuthError(RouterError):
    """El router rechazó las credenciales."""


class RouterSessionError(RouterError):
    """La sesión caducó o no está autorizada."""


@dataclass
class RouterDevice:
    mac: str
    ip: str
    name: str
    type_code: str
    connection: str
    online: bool
    blocked: bool
    up_bps: int
    down_bps: int


@dataclass
class RouterSnapshot:
    devices: list[RouterDevice]
    ssid: str | None
    model: str
    fetched_at: str
    wan_in_bytes: int | None = None
    wan_out_bytes: int | None = None
    wan_uptime: int | None = None


def security_encode(source: str, other: str, key: str) -> str:
    if not key:
        return ""
    output: list[str] = []
    for index in range(max(len(source), len(other))):
        left = ord(source[index]) if index < len(source) else 187
        right = ord(other[index]) if index < len(other) else 187
        output.append(key[(left ^ right) % len(key)])
    return "".join(output)


def org_auth_pwd(password: str) -> str:
    return security_encode(password, SALT, ALPHABET)


def parse_blocks(text: str) -> dict[int, dict[str, Any]]:
    lines = text.replace("\r", "").split("\n")
    if not lines or lines[0].strip() != "00000":
        raise RouterSessionError("respuesta TDDP no autorizada")
    blocks: dict[int, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("id "):
            try:
                block_id = int(line.split()[1])
            except (IndexError, ValueError):
                continue
            current = {"scalars": {}, "arrays": {}}
            blocks[block_id] = current
            continue
        if current is None:
            continue
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[1].isdigit():
            current["arrays"].setdefault(parts[0], {})[int(parts[1])] = parts[2]
        elif len(parts) >= 2:
            current["scalars"][parts[0]] = line.split(" ", 1)[1]
    return blocks


def parse_devices(text: str) -> list[RouterDevice]:
    blocks = parse_blocks(text)
    block = blocks.get(13)
    if not block:
        return []
    arrays = block["arrays"]
    devices: list[RouterDevice] = []
    for index, raw_ip in arrays.get("ip", {}).items():
        ip = raw_ip.strip()
        if not ip or ip == "0.0.0.0":
            continue
        raw_mac = arrays.get("mac", {}).get(index, "").strip().lower()
        mac = raw_mac.replace("-", ":")
        if not raw_mac or mac == "00:00:00:00:00:00":
            continue
        type_code = arrays.get("type", {}).get(index, "").strip()
        name = urllib.parse.unquote(arrays.get("name", {}).get(index, "").strip())
        devices.append(
            RouterDevice(
                mac=mac,
                ip=ip,
                name=name,
                type_code=type_code,
                connection=TYPE_LABELS.get(type_code, "Inalámbrico"),
                online=arrays.get("online", {}).get(index, "0") == "1",
                blocked=arrays.get("blocked", {}).get(index, "0") == "1",
                up_bps=int(arrays.get("up", {}).get(index, "0") or 0),
                down_bps=int(arrays.get("down", {}).get(index, "0") or 0),
            )
        )
    return devices


def parse_ssid(text: str) -> str | None:
    blocks = parse_blocks(text)
    for block_id in (33, 53):
        value = blocks.get(block_id, {}).get("scalars", {}).get("cSsid", "").strip()
        if value and not value.isdigit():
            return urllib.parse.unquote(value)
    return None


def parse_model(text: str) -> str:
    blocks = parse_blocks(text)
    return blocks.get(0, {}).get("scalars", {}).get("modelName", "AC12")


def parse_wan(text: str) -> tuple[int | None, int | None, int | None]:
    """Contadores WAN (`inOctets`, `outOctets`, `upTime`) del bloque 23/22."""
    blocks = parse_blocks(text)
    for block_id in (23, 22):
        scalars = blocks.get(block_id, {}).get("scalars", {})
        if "inOctets" in scalars and "outOctets" in scalars:
            try:
                return (
                    int(scalars["inOctets"]),
                    int(scalars["outOctets"]),
                    int(scalars.get("upTime", "0") or 0),
                )
            except (TypeError, ValueError):
                continue
    return None, None, None


class MercusysRouter:
    def __init__(
        self,
        base_url: str,
        password: str,
        timeout: float = 8.0,
        info_refresh_seconds: int = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.password = password
        self.timeout = timeout
        self.info_refresh_seconds = info_refresh_seconds
        self._session: str | None = None
        self._ssid: str | None = None
        self._model = "AC12"

    def _post(self, path: str, body: bytes = b"") -> tuple[int, str]:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                content=body,
                timeout=self.timeout,
                trust_env=False,
                headers={"User-Agent": "HomeLabDash-Agent/0.1"},
            )
        except httpx.HTTPError as exc:
            raise RouterError(f"router no disponible ({type(exc).__name__})") from exc
        return response.status_code, response.text

    def login(self) -> None:
        status, body = self._post("/?code=2&asyn=1")
        lines = body.replace("\r", "").split("\n")
        if status not in (401, 200) or len(lines) < 5:
            raise RouterAuthError("respuesta de autenticación inesperada")
        auth_source, auth_key = lines[3], lines[4]
        session = security_encode(auth_source, org_auth_pwd(self.password), auth_key)
        encoded = urllib.parse.quote(session, safe="")
        _, body = self._post(f"/?code=7&asyn=0&id={encoded}")
        if not body.startswith("00000"):
            raise RouterAuthError("credenciales del router rechazadas")
        self._session = session

    def _data(self, body: bytes) -> str:
        if self._session is None:
            self.login()
        encoded = urllib.parse.quote(self._session or "", safe="")
        status, text = self._post(f"/?code=2&asyn=0&id={encoded}", body)
        if status == 401 or text.startswith("00007"):
            self._session = None
            raise RouterSessionError("sesión del router caducada")
        if not text.startswith("00000"):
            raise RouterError("respuesta TDDP con error")
        return text

    def fetch(self) -> RouterSnapshot:
        try:
            text = self._data(b"13#22#23#33#53#0")
        except RouterSessionError:
            self.login()
            text = self._data(b"13#22#23#33#53#0")

        ssid = parse_ssid(text)
        model = parse_model(text)
        wan_in, wan_out, wan_uptime = parse_wan(text)
        if ssid:
            self._ssid = ssid
        if model:
            self._model = model

        return RouterSnapshot(
            devices=parse_devices(text),
            ssid=self._ssid,
            model=self._model,
            fetched_at=datetime.now(UTC).isoformat(),
            wan_in_bytes=wan_in,
            wan_out_bytes=wan_out,
            wan_uptime=wan_uptime,
        )

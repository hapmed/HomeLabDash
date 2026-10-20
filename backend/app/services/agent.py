"""Cliente HTTP del agente de métricas (solo red interna)."""

from functools import lru_cache
from typing import Any

import httpx

from app.core.config import get_settings


class AgentUnavailable(RuntimeError):
    """El agente no responde o devuelve una respuesta inválida."""


class AgentClient:
    def __init__(self, base_url: str, token: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        headers = {"X-Agent-Token": self._token, "Accept": "application/json"}
        try:
            response = httpx.get(
                f"{self._base_url}{path}", headers=headers, timeout=self._timeout
            )
        except httpx.HTTPError as exc:
            raise AgentUnavailable("agente no disponible") from exc

        if response.status_code != httpx.codes.OK:
            raise AgentUnavailable(f"el agente respondió {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AgentUnavailable("respuesta del agente no es JSON") from exc
        if not isinstance(payload, dict):
            raise AgentUnavailable("respuesta del agente inválida")
        return payload

    def summary(self) -> dict[str, Any]:
        return self._get("/v1/summary")

    def module(self, module_id: str) -> dict[str, Any]:
        return self._get(f"/v1/modules/{module_id}")

    def healthy(self) -> bool:
        try:
            response = httpx.get(f"{self._base_url}/healthz", timeout=self._timeout)
        except httpx.HTTPError:
            return False
        return response.status_code == httpx.codes.OK


@lru_cache
def get_agent_client() -> AgentClient:
    settings = get_settings()
    return AgentClient(
        base_url=settings.agent_url,
        token=settings.agent_token,
        timeout=settings.agent_timeout_seconds,
    )

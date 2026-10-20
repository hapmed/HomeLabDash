"""Cliente de solo lectura de la API interna de OpenCode.

Consulta estadísticas agregadas, proyectos, sesiones y configuración pública.
No lee mensajes, prompts ni credenciales.
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from app.billing import get_timezone


class OpenCodeError(RuntimeError):
    """No se pudo consultar la API de OpenCode."""


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _tokens(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    cache_value = value.get("cache")
    cache: dict[str, Any] = cache_value if isinstance(cache_value, dict) else {}
    return {
        "input": _int(value.get("input")),
        "output": _int(value.get("output")),
        "reasoning": _int(value.get("reasoning")),
        "cache_read": _int(cache.get("read")),
        "cache_write": _int(cache.get("write")),
    }


def sanitize_session(value: Any, projects: dict[str, str | None]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    model_value = value.get("model")
    model: dict[str, Any] = model_value if isinstance(model_value, dict) else {}
    location_value = value.get("location")
    location: dict[str, Any] = location_value if isinstance(location_value, dict) else {}
    times_value = value.get("time")
    times: dict[str, Any] = times_value if isinstance(times_value, dict) else {}
    project_id = str(value.get("projectID") or "")
    return {
        "id": value.get("id"),
        "title": value.get("title") or "Sin título",
        "project_id": project_id,
        "project_path": projects.get(project_id),
        "agent": value.get("agent"),
        "model": {
            "id": model.get("id"),
            "provider": model.get("providerID"),
            "variant": model.get("variant"),
        },
        "cost": round(_float(value.get("cost")), 6),
        "tokens": _tokens(value.get("tokens")),
        "outcome": value.get("outcome"),
        "created_at": _int(times.get("created")),
        "updated_at": _int(times.get("updated")),
        "directory": location.get("directory"),
    }


def sanitize_stats(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    data_value = value.get("data")
    data: dict[str, Any] = data_value if isinstance(data_value, dict) else value
    tools_value = data.get("tools")
    tools: dict[str, Any] = tools_value if isinstance(tools_value, dict) else {}
    totals_value = tools.get("totals")
    totals: dict[str, Any] = totals_value if isinstance(totals_value, dict) else {}
    models = []
    for item in data.get("models") or []:
        if not isinstance(item, dict):
            continue
        model_value = item.get("model")
        model: dict[str, Any] = model_value if isinstance(model_value, dict) else {}
        models.append(
            {
                "id": model.get("id"),
                "provider": model.get("providerID"),
                "variant": model.get("variant"),
                "steps": _int(item.get("steps")),
                "tokens": _tokens(item.get("tokens")),
                "cost": round(_float(item.get("cost")), 6),
            }
        )
    activity = [
        {"date": str(item.get("date")), "steps": _int(item.get("steps"))}
        for item in data.get("activity") or []
        if isinstance(item, dict)
    ]
    return {
        "sessions": _int(data.get("sessions")),
        "subagents": _int(data.get("subagents")),
        "prompts": _int(data.get("prompts")),
        "steps": _int(data.get("steps")),
        "tokens": _tokens(data.get("tokens")),
        "cost": round(_float(data.get("cost")), 6),
        "tools": {
            "calls": _int(totals.get("calls")),
            "succeeded": _int(totals.get("succeeded")),
            "failed": _int(totals.get("failed")),
            "unfinished": _int(totals.get("unfinished")),
        },
        "active_days": _int(data.get("activeDays")),
        "streak": _int(data.get("streak")),
        "activity": activity,
        "models": models,
    }


def sanitize_model(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    capabilities_value = value.get("capabilities")
    capabilities: dict[str, Any] = (
        capabilities_value if isinstance(capabilities_value, dict) else {}
    )
    variants_value = value.get("variants")
    variants = [
        item.get("id")
        for item in (variants_value if isinstance(variants_value, list) else [])
        if isinstance(item, dict) and item.get("id")
    ]
    return {
        "id": value.get("id") or value.get("modelID"),
        "name": value.get("name"),
        "provider": value.get("providerID"),
        "family": value.get("family"),
        "tools": bool(capabilities.get("tools")),
        "input": capabilities.get("input") or [],
        "output": capabilities.get("output") or [],
        "variants": variants,
    }


def sanitize_agents(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    agents = []
    data_value = value.get("data")
    for item in (data_value if isinstance(data_value, list) else []):
        if isinstance(item, dict):
            agents.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "mode": item.get("mode"),
                    "hidden": bool(item.get("hidden")),
                }
            )
    return agents


class OpenCodeClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timezone: str = "America/Monterrey",
        session_limit: int = 100,
        timeout: float = 8.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timezone = timezone
        self.session_limit = max(1, min(200, session_limit))
        self.timeout = timeout
        self._tz = get_timezone(timezone)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = httpx.get(
                f"{self.base_url}{path}",
                params=params,
                auth=self.auth,
                timeout=self.timeout,
                trust_env=False,
                headers={"User-Agent": "HomeLabDash-Agent/0.1"},
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenCodeError(f"OpenCode no disponible ({type(exc).__name__})") from exc

    def _safe(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            return self._get(path, params)
        except OpenCodeError:
            return None

    def fetch_app(self) -> dict[str, Any]:
        info = self._safe("/api/info")
        stats = self._safe(
            "/api/experimental/session/stats",
            {"timezone": self.timezone, "tools": "summary"},
        )
        projects_raw = self._safe("/api/project")
        sessions_raw = self._safe(
            "/api/session", {"limit": str(self.session_limit), "order": "desc"}
        )
        active_raw = self._safe("/api/session/active")
        model_raw = self._safe("/api/model/default")
        agents_raw = self._safe("/api/agent")
        location_raw = self._safe("/api/location")

        if info is None and stats is None and sessions_raw is None:
            raise OpenCodeError("OpenCode no respondió")

        projects_list = projects_raw if isinstance(projects_raw, list) else []
        project_paths: dict[str, str | None] = {
            str(item.get("id")): item.get("canonical")
            for item in projects_list
            if isinstance(item, dict) and item.get("id")
        }
        sessions_value = sessions_raw.get("data") if isinstance(sessions_raw, dict) else None
        sessions_data = sessions_value if isinstance(sessions_value, list) else []
        sessions = [
            session
            for item in sessions_data
            if (session := sanitize_session(item, project_paths)) is not None
        ]
        active_value = active_raw.get("data") if isinstance(active_raw, dict) else None
        active_data: dict[str, Any] = active_value if isinstance(active_value, dict) else {}
        active = [
            {
                "id": session_id,
                "type": value.get("type") if isinstance(value, dict) else None,
                "title": next(
                    (item["title"] for item in sessions if item["id"] == session_id),
                    None,
                ),
            }
            for session_id, value in active_data.items()
        ]

        aggregated: dict[str, dict[str, Any]] = {}
        for session in sessions:
            project_id = str(session.get("project_id") or "")
            if not project_id:
                continue
            entry = aggregated.setdefault(
                project_id,
                {
                    "sessions": 0,
                    "cost": 0.0,
                    "tokens": {
                        "input": 0,
                        "output": 0,
                        "reasoning": 0,
                        "cache_read": 0,
                        "cache_write": 0,
                    },
                    "last_active": 0,
                },
            )
            entry["sessions"] += 1
            entry["cost"] += float(session.get("cost") or 0)
            for key in ("input", "output", "reasoning", "cache_read", "cache_write"):
                entry["tokens"][key] += int((session.get("tokens") or {}).get(key, 0))
            entry["last_active"] = max(entry["last_active"], int(session.get("updated_at") or 0))

        projects = []
        for item in projects_list:
            if not isinstance(item, dict):
                continue
            project_id = str(item.get("id"))
            times_value = item.get("time")
            times: dict[str, Any] = times_value if isinstance(times_value, dict) else {}
            aggregate = aggregated.get(project_id, {})
            projects.append(
                {
                    "id": project_id,
                    "canonical": item.get("canonical"),
                    "vcs": item.get("vcs"),
                    "created_at": _int(times.get("created")),
                    "updated_at": _int(times.get("updated")),
                    "last_active": aggregate.get("last_active", 0),
                    "sessions": aggregate.get("sessions", 0),
                    "cost": round(float(aggregate.get("cost", 0)), 6),
                    "tokens": aggregate.get("tokens", {}),
                }
            )
        projects.sort(key=lambda item: item.get("last_active") or 0, reverse=True)

        model_value = model_raw.get("data") if isinstance(model_raw, dict) else None
        model_data = model_value if isinstance(model_value, dict) else None
        info_data: dict[str, Any] = info if isinstance(info, dict) else {}
        location: dict[str, Any] = location_raw if isinstance(location_raw, dict) else {}
        return {
            "info": {
                "version": info_data.get("version"),
                "pid": info_data.get("pid"),
                "urls": info_data.get("urls") or [],
                "capabilities": info_data.get("capabilities") or {},
            },
            "stats": sanitize_stats(stats),
            "projects": projects,
            "sessions": sessions,
            "active": active,
            "default_model": sanitize_model(model_data),
            "agents": sanitize_agents(agents_raw),
            "location": {
                "directory": location.get("directory"),
                "project": location.get("project"),
            },
            "timezone": self.timezone,
            "fetched_at": datetime.now(UTC).isoformat(),
        }

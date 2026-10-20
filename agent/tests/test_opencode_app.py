"""Tests de saneado de la API interna de OpenCode."""

from app.opencode_app import (
    sanitize_agents,
    sanitize_model,
    sanitize_session,
    sanitize_stats,
)

SESSION = {
    "id": "ses_1",
    "projectID": "p1",
    "title": "Trabajo",
    "agent": "build",
    "model": {"id": "m1", "providerID": "prov", "variant": "default"},
    "cost": 1.2345,
    "tokens": {"input": 100, "output": 20, "reasoning": 5, "cache": {"read": 50, "write": 0}},
    "outcome": "succeeded",
    "time": {"created": 1000, "updated": 2000},
    "location": {"directory": "/proyectos/HomeLabDash"},
    "messages": [{"secret": "no debe salir"}],
}

STATS = {
    "data": {
        "sessions": 3,
        "subagents": 2,
        "prompts": 10,
        "steps": 20,
        "tokens": {"input": 1000, "output": 200, "reasoning": 50, "cache": {"read": 500, "write": 0}},
        "cost": 2.5,
        "tools": {"mode": "summary", "totals": {"calls": 30, "succeeded": 28, "failed": 2, "unfinished": 0}},
        "activeDays": 5,
        "streak": 3,
        "activity": [{"date": "2026-10-20", "steps": 15}],
        "models": [
            {
                "model": {"id": "m1", "providerID": "prov", "variant": "default"},
                "steps": 20,
                "tokens": {"input": 1000, "output": 200, "reasoning": 50, "cache": {"read": 500, "write": 0}},
                "cost": 2.5,
            }
        ],
    }
}


def test_sanitize_session_no_expone_mensajes() -> None:
    result = sanitize_session(SESSION, {"p1": "/proyectos/HomeLabDash"})
    assert result is not None
    assert result["project_path"] == "/proyectos/HomeLabDash"
    assert result["tokens"]["cache_read"] == 50
    assert "messages" not in result


def test_sanitize_stats() -> None:
    result = sanitize_stats(STATS)
    assert result["sessions"] == 3
    assert result["tools"]["failed"] == 2
    assert result["models"][0]["id"] == "m1"
    assert result["activity"][0]["steps"] == 15


def test_sanitize_model_omite_headers_y_settings() -> None:
    model = {
        "id": "m1",
        "name": "Modelo",
        "providerID": "prov",
        "family": "test",
        "headers": {"authorization": "secreto"},
        "settings": {"baseURL": "https://example.invalid"},
        "capabilities": {"tools": True, "input": ["text"], "output": ["text"]},
        "variants": [{"id": "low"}, {"id": "high"}],
    }
    result = sanitize_model(model)
    assert result is not None
    assert "headers" not in result
    assert "settings" not in result
    assert result["variants"] == ["low", "high"]


def test_sanitize_agents() -> None:
    result = sanitize_agents(
        {"data": [{"id": "build", "name": "Build", "description": "x", "mode": "primary"}]}
    )
    assert result[0]["id"] == "build"
    assert result[0]["hidden"] is False

"""Fixtures de tests del agente."""

import os

os.environ.setdefault("AGENT_TOKEN", "test-agent-token")
os.environ.setdefault("HOST_ROOT", "/host-inexistente")
os.environ.setdefault("HOST_PROC", "/host-inexistente/proc")
os.environ.setdefault("HOST_SYS", "/host-inexistente/sys")

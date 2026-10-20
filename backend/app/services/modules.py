"""Registro único de módulos.

Añadir un módulo no debe exigir tocar el dashboard: basta con declararlo aquí
(y, cuando tenga datos, implementarlo en el agente). Los módulos `enabled=False`
permanecen en el catálogo para las fases siguientes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleMeta:
    id: str
    name: str
    description: str
    icon: str
    order: int
    enabled: bool


MODULES: tuple[ModuleMeta, ...] = (
    ModuleMeta("overview", "Resumen", "Estado general del servidor", "gauge", 10, True),
    ModuleMeta("cpu", "CPU", "Uso, carga y frecuencia", "cpu", 20, True),
    ModuleMeta("memory", "Memoria", "RAM, swap y presión", "memory-stick", 30, True),
    ModuleMeta("storage", "Discos", "Uso por punto de montaje", "hard-drive", 40, True),
    ModuleMeta("internet", "Internet", "Velocidad, IP pública y latencia", "globe", 45, True),
    ModuleMeta("devices", "Dispositivos", "Clientes de la red y presencia", "router", 46, True),
    ModuleMeta("docker", "Docker", "Contenedores y consumo", "container", 50, False),
    ModuleMeta("network", "Red", "Interfaces y tráfico", "network", 60, False),
    ModuleMeta("temperature", "Temperatura", "Sensores del host", "thermometer", 70, False),
    ModuleMeta("services", "Servicios", "Puertos y unidades", "server", 80, False),
    ModuleMeta("cloudflare", "Cloudflare", "Estado del túnel", "cloud", 90, False),
    ModuleMeta("backups", "Backups", "Última copia y resultado", "database-backup", 100, False),
    ModuleMeta("alerts", "Alertas", "Umbrales e historial", "bell-ring", 110, False),
)


def enabled_modules() -> list[ModuleMeta]:
    return [module for module in MODULES if module.enabled]


def get_module(module_id: str) -> ModuleMeta | None:
    return next((module for module in MODULES if module.id == module_id), None)

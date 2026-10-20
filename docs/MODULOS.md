# Módulos — HomeLabDash

Cada módulo es un widget del dashboard y una página de detalle en
`/modulo/<id>`. El estado se calcula en el agente y se expone por la API.

> **Estado:** implementados y desplegados `overview`, `cpu`, `memory`, `storage`,
> `internet`, `devices`, `docker`, `database`, `network`, `weather`,
> `temperature`, `hardware` y `opencode`. `services`, `cloudflare`, `backups` y
> `alerts` siguen en el registro con `enabled=false` hasta su fase.

## Catálogo

| ID | Módulo | Widget (resumen) | Detalle | Fuente | Fase |
|---|---|---|---|---|---|
| `overview` | Resumen | CPU, RAM, carga, uptime, alertas | Estado general y accesos rápidos | agente | 1 |
| `cpu` | CPU | % de uso y carga 1m | Por núcleo, frecuencia, histórico | `/proc/stat`, psutil | 2 |
| `memory` | Memoria | RAM usada / total | RAM, swap, presión, top procesos | `/proc/meminfo`, psutil | 2 |
| `storage` | Discos | % del disco raíz | Puntos de montaje, I/O, inodos | `df`, psutil, sysfs | 2 (implementado) |
| `internet` | Internet | Bajada (Mbps) e IP pública | Histórico, subida, latencia, ISP | Cloudflare speedtest, ipinfo | 1 |
| `devices` | Dispositivos | Dispositivos en línea | Inventario, nombres, SSID, tasas, consumo diario/mensual e histórico | ARP del host + router AC12 | 1 |
| `docker` | Docker | Contenedores activos / total | Lista, estado, CPU/RAM, red, disco y logs | Docker socket (ro) | 3 (implementado) |
| `database` | Base de datos | Tamaño y conexiones | Tablas, índices, caché, actividad e histórico | `pg_stat_*` | 3 (implementado) |
| `network` | Red | Tráfico actual | Interfaces, RX/TX, errores y descartes | `/sys/class/net` | 3 (implementado) |
| `weather` | Clima | Temperatura actual | Lluvia, humedad, AQI, hourly y diario | Open-Meteo | 3 (implementado) |
| `temperature` | Temperatura | Máxima | Sensores por chip/zona y ventiladores | `/sys/class/hwmon` | 3 (implementado) |
| `hardware` | Hardware | Batería / discos | Equipo, discos, inodos, SMART, batería/SAI, actualizaciones | sysfs, dpkg/apt, smartctl | 5 (implementado) |
| `opencode` | OpenCode | Estado del contenedor | Sesiones, proyectos, tokens, costo, modelos y logs | Docker + API interna | 4 (implementado) |
| `services` | Servicios | Servicios activos | Puertos, unidades, uptime | `systemctl`, sockets | 3 |
| `cloudflare` | Cloudflare | Estado del túnel | Latencia, conexiones, hostnames | API/cloudflared | 4 |
| `backups` | Backups | Último backup | Historial y resultado | job local | 4 |
| `alerts` | Alertas | Alertas activas | Umbrales e historial | BD | 4 |

El backend guarda una muestra compacta de cada módulo cada 5 minutos. Los
detalles de `overview`, `cpu`, `memory`, `storage`, `docker`, `network`,
`temperature` y `hardware` muestran gráficas de 24 h, 7 días y 30 días mediante
`GET /api/v1/modules/{id}/history?hours=24`.

## Contrato de un módulo

```ts
type ModuleStatus = 'ok' | 'warn' | 'critical' | 'unknown';

interface ModuleCard {
  id: string;
  name: string;
  description: string;
  icon: string;        // nombre Lucide
  order: number;
  enabled: boolean;
  status: ModuleStatus;
  summary: {
    label: string;
    value: string | number;
    unit?: string;
    detail?: string;
  };
}
```

## Reglas de UI (Apple HIG)

- Un widget = una idea. Métrica principal grande, contexto pequeño.
- Estado siempre con **color + icono + texto** (no solo color).
- Click en toda la tarjeta, con foco visible y navegación por teclado.
- Animaciones suaves (`cubic-bezier(0.22,0.61,0.36,1)`), sin rebotes.
- Modo claro y oscuro; respetar `prefers-reduced-motion`.
- En móvil, grid de una columna; en escritorio, 2–4 columnas.

## Criterios de aceptación (MVP)

- [ ] El dashboard carga en menos de 2 s en LAN.
- [ ] Cada widget muestra estado y métrica sin entrar al detalle.
- [ ] El detalle actualiza cada 5 s y no rompe si el agente no responde.
- [ ] La PWA se instala y abre sin conexión mostrando el último estado.
- [ ] Ningún secreto ni socket de Docker en el backend/frontend.
- [ ] `docker compose` levanta todo con healthchecks verdes.

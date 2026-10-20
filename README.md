# HomeLabDash

Dashboard de monitorización del **HomeLab** (`192.168.0.14`), instalable como
**PWA** y usable en escritorio y móvil.

- **Frontend:** SvelteKit 3 · Svelte 5 · TypeScript · Tailwind CSS v4 · Lucide
- **Backend:** FastAPI · SQLAlchemy 2 · Alembic · PyJWT · PostgreSQL 17 existente
- **Agente:** FastAPI de solo lectura del host (psutil sobre `/proc`, `/sys` y `/`)
- **Empaquetado:** Docker Compose · red `apps-net` · puerto local `127.0.0.1:8083`
- **Diseño:** Apple HIG con los tokens HAPMED de EVAS

## Cómo funciona

```
Navegador / PWA
      │ HTTPS (Cloudflare Tunnel)
      ▼
frontend SvelteKit (adapter-node)     127.0.0.1:8083
      │ /api/* (proxy interno, cookie de sesión JWT)
      ▼
backend FastAPI                       api:8000   ──► PostgreSQL (base homelabdash)
      │ /v1/* (token X-Agent-Token)
      ▼
agent FastAPI (solo lectura)           agent:8001
      ├── /proc, /sys, / (host, ro)
      └── Docker socket (ro) + SMART del host (JSON ro)
```

- El dashboard pinta un **widget por módulo**; al pulsarlo se abre `/modulo/<id>`.
- Los módulos se declaran en un registro (`backend/app/services/modules.py`); añadir
  uno nuevo no obliga a tocar el dashboard.
- El backend nunca monta el socket de Docker ni `/proc` del host: eso es cosa del
  agente, que solo expone lectura con un token interno.

## Módulos

| ID | Widget | Detalle | Fuente |
|---|---|---|---|
| `overview` | Carga 1m, CPU, RAM, uptime, alertas | Host, kernel, cargas | agente |
| `cpu` | Uso (%) y carga 1m | Por núcleo, frecuencia, cargas | `/proc/stat`, `psutil` |
| `memory` | RAM usada (%) | RAM, swap, presión | `/proc/meminfo` |
| `storage` | Disco raíz (%) | Montajes, I/O, inodos | `/proc/mounts` |
| `internet` | Velocidad de bajada e IP pública | Histórico, subida, latencia, ISP | Cloudflare speedtest + ipinfo |
| `devices` | Dispositivos en línea | Inventario, nombres, SSID, tasas, consumo diario/mensual y top consumidor | ARP del host + router AC12 |
| `docker` | Contenedores activos / total | CPU, RAM, red, disco, sistema y logs | Docker SDK (socket ro) |
| `database` | Tamaño y conexiones | Tablas, índices, caché, actividad e histórico | PostgreSQL `pg_stat_*` |
| `network` | Tráfico de bajada | Interfaces, velocidad, RX/TX, errores y descartes | `/sys/class/net` del host |
| `weather` | Temperatura actual | Lluvia, humedad, viento, UV, AQI, hourly y diario | Open-Meteo |
| `temperature` | Temperatura máxima | Sensores por chip/zona y ventiladores | `/sys/class/hwmon` y `thermal` |
| `hardware` | Batería / discos | Equipo, discos, inodos, SMART, batería/SAI y actualizaciones | sysfs, dpkg/apt y `smartctl` |
| `opencode` | Estado del contenedor | Recursos, sesiones, proyectos, tokens, costos y logs | Docker inspect + API interna |

Además, los módulos `overview`, `cpu`, `memory`, `storage`, `docker`,
`network`, `temperature` y `hardware` muestran un **histórico común** con
gráficas de 24 h, 7 días y 30 días. El backend guarda una muestra compacta cada
5 minutos en `module_snapshots` (retención de 30 días, hasta 600 puntos por
gráfica).

El monitor de Docker usa el socket en **solo lectura** para listar contenedores y
medir CPU, RAM, red, bloques, disco y logs; no inicia, detiene ni modifica nada.

El monitor de dispositivos sondea la red local cada minuto y mantiene un
inventario persistente con MAC, IP, fabricante, nombre, primera/última vez visto
y tiempo acumulado en línea. Con las credenciales del router AC12 obtiene el
SSID, los nombres DHCP y la tasa instantánea de cada cliente; el consumo por
dispositivo (MB/GB/TB) se **estima** integrando esas tasas cada 60 s. El consumo
total de Internet se toma de los contadores WAN del router. El ciclo se corta el
**día 10 de cada mes**, el consumo diario a las **00:00** y se guardan históricos
diario y mensual con el mayor consumidor de cada periodo.

El monitor de Internet comprueba la conectividad cada minuto y ejecuta un test de
velocidad cada hora (10 MB de bajada + 2 MB de subida, ≈ 290 MB/día). El
histórico (168 pruebas ≈ 7 días) se guarda en el volumen `agent-data`, así que
sobrevive a reinicios. Todo es configurable con `INTERNET_*` en `.env`.

El catálogo completo (servicios, Cloudflare, backups, alertas) está declarado
con `enabled=false` y se activará en fases posteriores — ver
[`docs/MODULOS.md`](./docs/MODULOS.md).

El clima usa **Open-Meteo** (sin API key): estado actual, previsión hourly/diaria,
lluvia acumulada, calidad del aire y un histórico diario persistente. La base de
datos solo consulta `homelabdash` mediante `pg_stat_*`, en modo lectura.

## Estructura

```
HomeLabDash/
├─ backend/   FastAPI + SQLAlchemy + Alembic (API /api/v1)
├─ agent/     FastAPI de solo lectura (/v1)
├─ frontend/  SvelteKit 3 + PWA
├─ ops/       compose.yaml (dev) · compose.prod.yaml (prod, sin PostgreSQL)
└─ docs/      ARQUITECTURA.md · MODULOS.md
```

## Arranque local (desarrollo)

Requisitos: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
# Backend
cd backend && uv sync
uv run ruff check . && uv run mypy app && uv run pytest

# Agente
cd ../agent && uv sync
uv run ruff check . && uv run mypy app && uv run pytest

# Frontend
cd ../frontend && npm install
npm run check && npm run test && npm run lint && npm run build
```

Para levantar la API y el agente en local (sin Docker) basta con definir
`DATABASE_URL`, `JWT_SECRET`, `ADMIN_USER`, `ADMIN_PASSWORD`, `AGENT_TOKEN` y
`AGENT_URL`, y ejecutar `uv run alembic upgrade head && uv run uvicorn app.main:app`.
El agente usa `/proc` real si no encuentra los montajes `/host/*`.

## Despliegue (servidor HomeLab)

```bash
# 1) Copiar el proyecto (sin node_modules ni .venv) a /opt/apps/HomeLabDash
# 2) Colocar el .env privado en la raíz del proyecto
# 3) Construir y arrancar
cd /opt/apps/HomeLabDash
docker compose -f ops/compose.prod.yaml up -d --build

# 4) Comprobar
docker compose -f ops/compose.prod.yaml ps
curl -s localhost:8083/api/v1/health
```

Solo se publica el frontend en `127.0.0.1:8083`. El backend y el agente viven en
una red interna; el backend además entra en `apps-net` para hablar con `postgres`.

### SMART y actualizaciones

El módulo `hardware` lee la batería, los discos, los inodos y el estado de
actualizaciones desde sysfs/dpkg. Para la salud SMART se instala `smartmontools`
en el host y se ejecuta un colector de solo lectura cada 6 horas:

```bash
sudo apt install smartmontools
sudo install -m 644 ops/systemd/homelabdash-hardware.service /etc/systemd/system/
sudo install -m 644 ops/systemd/homelabdash-hardware.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homelabdash-hardware.timer
sudo systemctl start homelabdash-hardware.service
```

El colector escribe `data/smart.json` de forma atómica; el agente lo lee a través
del montaje de solo lectura `/host`. Si no está instalado, el módulo sigue
funcionando y muestra SMART como «No disponible».

### Variables de entorno

Copia [`.env.example`](./.env.example) a `.env` (privado, en `.gitignore`). Las
claves se generan con `openssl rand -hex 32`. En producción `COOKIE_SECURE=true`
y el frontend usa `PROTOCOL_HEADER=x-forwarded-proto` para conocer el esquema
detrás del túnel de Cloudflare.

### Base de datos

Instancia PostgreSQL 17 existente (contenedor `postgres`, red `apps-net`). Base
`homelabdash` y usuario dedicado `homelabdash_app`; el esquema se crea **solo**
con migraciones Alembic (`backend/alembic`), que se aplican al arrancar el
contenedor de la API. No se toca `hapmed` ni `evas_admin`.

Tablas: `users`, `settings`, `module_snapshots`, `alerts`, `audit_log`.

## API

Backend (`/api/v1`, requiere sesión salvo `health`):

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Usuario/contraseña → JWT |
| `GET` | `/api/v1/auth/me` | Usuario de la sesión |
| `GET` | `/api/v1/modules` | Widgets del dashboard |
| `GET` | `/api/v1/modules/{id}` | Detalle del módulo |
| `GET` | `/api/v1/modules/{id}/history?hours=24` | Histórico compacto (1–720 h) |
| `GET` | `/api/v1/alerts` | Alertas activas |
| `GET` | `/api/v1/health` | Estado de la BD y del agente |
| `GET` | `/healthz` | Liveness |

Agente (red interna, cabecera `X-Agent-Token`):

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/summary` | Resumen de todos los widgets |
| `GET` | `/v1/modules/{id}` | Detalle de un módulo |
| `GET` | `/healthz` | Liveness |

La sesión se guarda en una cookie `hld_session` **HttpOnly** que el frontend
emite tras el login; el proxy `/api/*` la reenvía al backend. `GET /api/v1/modules`
nunca falla si el agente está caído: devuelve los widgets con estado `unknown`.

## PWA

`manifest.webmanifest`, service worker que cachea el **shell** y una página
offline, iconos 192/512 y metadatos iOS. El service worker **no** cachea `/api/*`
ni HTML autenticado. Instalable en iOS/iPadOS, Android, Windows y macOS.

## Seguridad

- Frontend en `127.0.0.1:8083`; nunca `0.0.0.0`.
- Token interno del agente distinto del JWT de usuario.
- Contraseñas con bcrypt; nunca en claro en BD ni en logs.
- Rate limit en login y auditoría de accesos (`audit_log`).
- Contenedores sin `privileged`, sin capabilities extra, usuario no root y
  `no-new-privileges`; el agente además es de raíz de solo lectura.
- El colector SMART es un `oneshot` del host (root) que solo lee los dispositivos
  y escribe un JSON; no se ejecuta dentro de los contenedores.
- `.env` y `ACCESOS.md` fuera de Git.

## Estado

- Fase 1 implementada y desplegada en `/opt/apps/HomeLabDash`.
- Módulos de red, temperatura y hardware desplegados, con histórico común de
  24 h / 7 d / 30 d y colector SMART cada 6 h.
- Dominio público verificado por HTTPS: `https://homelabdash.hapmed.qzz.io` (túnel `HomeLabServer` + CNAME proxied).
- Pendiente: repositorio `hapmed/HomeLabDash` (falta el token de `hapmed`).
- Pendiente: módulos de operación (Cloudflare, backups, alertas y notificaciones).

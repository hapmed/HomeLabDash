# AGENTS.md — HomeLabDash

Guía obligatoria para el agente que programe este proyecto.

## 0. Regla de oro

- Trabaja **solo** dentro de `/proyectos/HomeLabDash`.
- **No** toques `/proyectos/BitsoBot`, `evas`, `evas_admin`, `hapmedpage` ni ningún
  otro proyecto.
- **No** toques las bases `hapmed` ni `evas_admin`, ni borres volúmenes o
  contenedores.
- Los secretos están en [`ACCESOS.md`](./ACCESOS.md): úsalo, **no lo versiones**,
  no lo pegues en logs ni en el chat.
- No inventes resultados de pruebas. Si algo no se puede ejecutar, dilo.

## 1. Qué es

**HomeLabDash** es el dashboard de monitoreo del servidor HomeLab
(`192.168.0.14`). Debe funcionar como **PWA instalable** y en **escritorio**.

Experiencia:

1. El dashboard muestra un **grid de módulos**; cada módulo es un recuadro/widget
   con estado y métrica principal.
2. Al hacer **click en el widget** se abre `/modulo/<id>` con el detalle:
   gráficas, tablas, historial y acciones permitidas.
3. Los módulos se declaran en un registro; añadir uno no debe obligar a reescribir
   el dashboard.
4. Tema claro/oscuro, responsive y estética **Apple HIG**.

## 2. Stack — el mismo de los EVAS

| Capa | Tecnología |
|---|---|
| Frontend | SvelteKit 3 · Svelte 5 · TypeScript · Tailwind CSS v4 · Vite · Lucide |
| Backend | FastAPI · SQLAlchemy 2 · Alembic · psycopg · PyJWT · Python 3.12+ |
| Agente | FastAPI · psutil · Docker SDK (solo lectura) |
| BD | PostgreSQL 17 **existente** en el servidor |
| Empaquetado | Docker · Docker Compose · red `apps-net` |
| Diseño | Apple HIG (`apple-design-skill`) + tokens EVAS |

Referencias públicas (se pueden clonar sin token):

- <https://github.com/hapmed/eva_Admin> — arquitectura, seguridad, Docker y el
  sistema de diseño en `docs/EVAS_ADMIN/`.
- <https://github.com/hapmed/eva-admon> — ejemplo real de app con este stack.
- Plantilla base: `eva_Admin/templates/eva-starter/`.

## 3. Arquitectura

```
Navegador / PWA / escritorio
          │ HTTPS (Cloudflare Tunnel)
          ▼
frontend SvelteKit (adapter-node)     127.0.0.1:8083
          │ /api/* (JWT, mismo origen)
          ▼
backend FastAPI                        api:8000  (solo red interna)
          │ /v1/* (token interno)
          ▼
agent FastAPI (solo lectura)           agent:8001 (solo red interna)
          ├── /proc, /sys, / (host, ro)
          └── /var/run/docker.sock (ro)
                     │
                     ▼
       PostgreSQL existente · base homelabdash
```

Reglas:

- El **backend nunca** monta el socket de Docker ni `/proc` del host.
- El **agente** es el único que ve Docker y métricas del host; expone una API
  mínima de solo lectura protegida por token.
- El **frontend** habla solo con el backend. Para evitar CORS, SvelteKit debe
  proxear `/api/*` al backend (`hooks.server.ts` o ruta `+server.ts`).
- El backend y el agente **no** se publican al host; solo el frontend en
  `127.0.0.1:8083`.

## 4. Base de datos

Decisión tomada: **usar la instancia PostgreSQL existente**, sin crear otro
servidor de base de datos.

- Instancia: contenedor `postgres` (PostgreSQL 17), red `apps-net`.
- Base nueva: `homelabdash`.
- Usuario dedicado: `homelabdash_app`.
- Credenciales de administrador y servidor: [`ACCESOS.md`](./ACCESOS.md).
- **No** tocar `hapmed` ni `evas_admin`.

Cadena para el backend:

```
DATABASE_URL=postgresql+psycopg://homelabdash_app:<clave>@postgres:5432/homelabdash
```

Creación (una sola vez, desde el host o un contenedor con acceso):

```sql
CREATE DATABASE homelabdash;
CREATE USER homelabdash_app WITH ENCRYPTED PASSWORD '<clave-generada>';
GRANT CONNECT ON DATABASE homelabdash TO homelabdash_app;
\c homelabdash
ALTER SCHEMA public OWNER TO homelabdash_app;
GRANT USAGE, CREATE ON SCHEMA public TO homelabdash_app;
```

- Genera la clave con `openssl rand -hex 24` y guárdala en `ACCESOS.md`.
- Esquema y tablas **solo** con migraciones Alembic. No crear tablas a mano.
- Tablas mínimas: `users`, `settings`, `module_snapshots`, `alerts`,
  `audit_log`.
- Al arrancar: crear el admin desde `ADMIN_USER` / `ADMIN_PASSWORD` si no existe
  (hash bcrypt/argon2; nunca guardar la contraseña en claro).

## 5. Módulos

| ID | Módulo | Widget | Detalle | Fase |
|---|---|---|---|---|
| `overview` | Resumen | CPU, RAM, carga, uptime, alertas | Estado general y accesos | 1 |
| `cpu` | CPU | % de uso y carga 1m | Por núcleo, frecuencia, histórico | 2 |
| `memory` | Memoria | RAM usada / total | RAM, swap, presión | 2 |
| `storage` | Discos | % del disco raíz | Montajes, I/O, SMART | 2 |
| `docker` | Docker | Activos / total | Lista, estado, consumo, logs | 3 |
| `network` | Red | Tráfico actual | Interfaces, RX/TX, errores | 3 |
| `temperature` | Temperatura | Máxima | Sensores por zona | 3 |
| `services` | Servicios | Activos | Puertos y unidades | 3 |
| `cloudflare` | Cloudflare | Estado del túnel | Latencia y hostnames | 4 |
| `backups` | Backups | Último backup | Historial y resultado | 4 |
| `alerts` | Alertas | Activas | Umbrales e historial | 4 |

Contrato de widget:

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

El backend expone `GET /api/v1/modules` y `GET /api/v1/modules/{id}`. El
frontend pinta un `ModuleCard` por entrada y navega a `/modulo/<id>`.

## 6. Diseño — Apple HIG

Referencia: `eva_Admin/docs/EVAS_ADMIN/UX_DESIGN_SYSTEM.md` (skill
`apple-design-skill` aplicado a web). Si el skill no está disponible en el
entorno, aplica estas reglas:

**Color (tokens EVAS):**

| Token | Claro | Oscuro |
|---|---|---|
| `--bg` | `#fbfbfd` | `#0b0c0e` |
| `--surface` | `#ffffff` | `#141518` |
| `--surface-2` | `#f2f2f7` | `#1b2340` |
| `--ink` | `#1d1d1f` | `#f5f5f7` |
| `--ink-2` | `#6e6e73` | `#a7abb3` |
| `--ink-3` | `#8a8a8f` | `#6e737c` |
| `--line` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.10)` |
| `--accent` | `#2e6bff` | `#5b8cff` |
| `--accent-2` | `#00c2b8` | `#2fd6cd` |
| `--green` | `#34c759` | igual |
| `--orange` | `#ff9500` | igual |
| `--red` | `#ff3b30` | igual |

- Radios: `24px` principal, `16px` secundario.
- Easing: `cubic-bezier(0.22, 0.61, 0.36, 1)`.
- Fuente: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.
- Jerarquía por tamaño + peso + color; evitar pesos light.
- Estado siempre con **color + icono + texto**.
- Tarjetas con material sutil, sin sombras exageradas ni gradientes morados.
- Modo claro/oscuro y `prefers-reduced-motion`.
- En móvil 1 columna; escritorio 2–4 columnas.

## 7. PWA y escritorio

- `manifest.webmanifest`: nombre `HomeLabDash`, `short_name` `HomeLab`,
  `display: standalone`, `theme_color` `#0b0c0e`, iconos 192 y 512.
- Iconos: reutilizar los de marca HAPMED de `eva_Admin/brand/` o generar un set
  coherente (`favicon-64.png`, `apple-touch-icon.png`, `og-image.png`).
- Service worker: cachea el shell y la última vista; **nunca** cachea respuestas
  autenticadas con datos sensibles.
- Instalable en iOS/iPadOS, Android, Windows y macOS.
- Fase posterior: wrapper Tauri opcional reutilizando el frontend.

## 8. Estructura esperada

```
HomeLabDash/
├─ ACCESOS.md                  # privado, en .gitignore
├─ AGENTS.md
├─ README.md
├─ .env.example
├─ .gitignore
├─ backend/
│  ├─ app/{main.py, core/config.py, api/{health,auth,modules}.py,
│  │        models/, services/agent.py, db/}
│  ├─ alembic/
│  ├─ tests/
│  ├─ pyproject.toml
│  └─ Dockerfile
├─ agent/
│  ├─ app/{main.py, config.py, metrics.py, docker_metrics.py}
│  ├─ tests/
│  ├─ pyproject.toml
│  └─ Dockerfile
├─ frontend/
│  ├─ src/{app.css, app.html, hooks.server.ts,
│  │        lib/{api,components,modules.ts,stores},
│  │        routes/{+layout.svelte,+page.svelte,
│  │                login/+page.svelte,modulo/[id]/+page.svelte}}
│  ├─ static/{manifest.webmanifest,sw.js,brand/}
│  ├─ package.json
│  └─ Dockerfile
├─ ops/{compose.yaml,compose.prod.yaml}
└─ docs/{ARQUITECTURA.md,MODULOS.md}
```

## 9. API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Usuario/contraseña → JWT |
| `GET` | `/api/v1/modules` | Widgets del dashboard |
| `GET` | `/api/v1/modules/{id}` | Detalle del módulo |
| `GET` | `/api/v1/alerts` | Alertas activas |
| `GET` | `/api/v1/health` | Salud del backend |
| `GET` | `/healthz` | Liveness |

Agente (solo red interna, token `X-Agent-Token`):

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/summary` | Resumen de todos los widgets |
| `GET` | `/v1/modules/{id}` | Detalle de un módulo |
| `GET` | `/healthz` | Liveness |

## 10. Seguridad

- Frontend en `127.0.0.1:8083`; backend y agente solo en la red Docker.
- Token interno `AGENT_TOKEN` distinto del JWT de usuario.
- Contraseña de admin con hash; nunca en claro en BD ni logs.
- Socket Docker **solo** en el agente y en modo lectura.
- Contenedores sin `privileged`, procesos no root, imágenes con versión fija.
- `.env` y `ACCESOS.md` en `.gitignore`.
- Rate limit en login y auditoría de accesos.

## 11. Fase 1 — entregable inmediato

1. **Esqueleto monorepo**: `backend/`, `agent/`, `frontend/`, `ops/`.
2. **Backend**: health, login JWT, bootstrap de admin, proxy al agente,
   `/api/v1/modules` con los módulos de Fase 1.
3. **Agente**: `/v1/summary` con CPU, RAM, disco, carga y uptime; token auth.
4. **Frontend**: layout HIG, login, dashboard con grid de widgets, ruta
   `/modulo/<id>` con detalle (aunque sea básico), tema claro/oscuro.
5. **PWA**: manifest, service worker, iconos, instalable.
6. **Docker**: `compose.yaml` de desarrollo y `compose.prod.yaml` sin servicio
   PostgreSQL (usa el existente).
7. **Calidad**: tests de backend/agente y `npm run check` + build del frontend.
8. **Docs**: `README.md` con arranque local y despliegue.

**Aceptación de Fase 1:**

- [ ] `docker compose up` levanta frontend, backend y agente con healthchecks.
- [ ] Login funciona con el admin definido en `.env`.
- [ ] El dashboard muestra los widgets de Fase 1 con datos reales del host.
- [ ] Click en un widget abre su detalle.
- [ ] La PWA se instala y el shell abre offline.
- [ ] `pytest` y `npm run check` pasan.
- [ ] No hay secretos en Git.

## 12. Verificación

```bash
# Backend y agente
cd backend && uv sync && uv run ruff check . && uv run mypy app && uv run pytest
cd agent   && uv sync && uv run ruff check . && uv run mypy app && uv run pytest

# Frontend
cd frontend && npm install && npm run check && npm run lint && npm run test && npm run build

# Compose
docker compose -f ops/compose.yaml config
```

Si el entorno de trabajo no tiene Node/Python, ejecuta las pruebas con Docker en
el servidor o instala el toolchain. **No reportes como verificado lo que no se
ejecutó.**

## 13. Bloqueos conocidos

- **Token de GitHub de `hapmed`**: no está disponible en el contenedor. No se
  puede crear ni subir `hapmed/HomeLabDash` todavía. Trabaja local y reporta.
- **Creación de la base**: requiere las credenciales de administrador de
  `ACCESOS.md`. Si no hay acceso al servidor, deja la migración lista y reporta.
- **DNS de Cloudflare**: pendiente de configurar `homelabdash.hapmed.qzz.io`.

## 14. Reporte al terminar

1. Qué se implementó y qué no.
2. Archivos creados/modificados.
3. Comandos ejecutados y su salida (build/tests).
4. Cómo se probó el dashboard y la PWA.
5. Bloqueos y siguiente paso recomendado.

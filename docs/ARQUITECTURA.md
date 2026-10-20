# Arquitectura — HomeLabDash

## Objetivo

Monitorizar el servidor HomeLab desde una sola interfaz, con módulos
independientes que se ven como widgets en el dashboard y se abren en su detalle.
Debe funcionar como PWA instalable y como aplicación de escritorio.

## Componentes

```
Navegador / PWA / escritorio
          │  HTTPS (Cloudflare Tunnel)
          ▼
   frontend (SvelteKit 3, adapter-node)   :8083
          │  /api/*  (JWT)
          ▼
   backend (FastAPI + SQLAlchemy)         :8000  ──► PostgreSQL existente
          │  /v1/*  (token interno)                  base: homelabdash
          ▼
   agent (FastAPI, solo lectura)          :8001
          │
          ├── /proc, /sys, /  (host, read-only)
          └── /var/run/docker.sock (read-only)
```

**Por qué un agente:** el backend nunca monta el socket de Docker ni `/proc` del
host. El agente expone una API mínima y de solo lectura, protegida por token. Así
una vulnerabilidad del backend no da control del servidor.

## Stack

- **Frontend:** SvelteKit 3, Svelte 5, TypeScript, Tailwind v4, Lucide.
  `adapter-node` para SSR/API y PWA.
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, psycopg, PyJWT.
- **Agente:** FastAPI, psutil, docker SDK (solo lectura).
- **BD:** PostgreSQL 17 existente; base `homelabdash` y usuario dedicado.
- **Diseño:** Apple HIG según el `apple-design-skill` aplicado en EVAS
  (`docs/EVAS_ADMIN/UX_DESIGN_SYSTEM.md`): tokens de color, tipografía del
  sistema, radios, materiales, modo claro/oscuro y estados con color + icono + texto.

## Registro de módulos

El dashboard no conoce los módulos de forma hardcodeada. El backend expone
`GET /api/v1/modules` con metadatos:

```json
{
  "id": "cpu",
  "name": "CPU",
  "description": "Uso, carga y frecuencia",
  "icon": "cpu",
  "order": 20,
  "enabled": true,
  "status": "ok",
  "summary": { "value": 23, "unit": "%", "label": "uso" }
}
```

El frontend pinta un `ModuleCard` por entrada y navega a `/modulo/<id>`. El
detalle se obtiene de `GET /api/v1/modules/<id>`.

## API principal

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Contraseña de administrador → JWT |
| `GET` | `/api/v1/modules` | Widgets del dashboard |
| `GET` | `/api/v1/modules/{id}` | Detalle del módulo |
| `GET` | `/api/v1/alerts` | Alertas activas e historial |
| `GET` | `/api/v1/health` | Salud del backend |
| `GET` | `/healthz` | Liveness (Docker) |

Agente:

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/v1/summary` | Resumen para todos los widgets |
| `GET` | `/v1/modules/{id}` | Detalle de un módulo |
| `GET` | `/healthz` | Liveness |

## Datos

Tablas mínimas:

- `users` — administradores (hash de contraseña, nunca en claro).
- `settings` — umbrales de alertas, retención, zona horaria.
- `module_snapshots` — métricas agregadas por módulo y fecha (histórico).
- `alerts` — alerta, severidad, inicio, fin, reconocida.
- `audit_log` — accesos y acciones.

Las métricas en vivo **no** se guardan en cada lectura; el agente las sirve y un
job periódico guarda snapshots agregados.

## Configuración y proxy

- Todo se configura por entorno (ver [`.env.example`](../.env.example)): `DATABASE_URL`,
  `JWT_SECRET`, `ADMIN_USER`/`ADMIN_PASSWORD`, `AGENT_URL`/`AGENT_TOKEN` y los
  umbrales de estado.
- El frontend proxya `/api/*` al backend desde `hooks.server.ts` (mismo origen, sin
  CORS) y guarda la sesión en una cookie `hld_session` HttpOnly.
- Detrás del túnel, SvelteKit necesita `PROTOCOL_HEADER=x-forwarded-proto` y
  `HOST_HEADER=host` para deducir su origen y validar los envíos de formulario
  (protección CSRF). Sin esos encabezados, el login responde 403.
- El registro de módulos vive en `backend/app/services/modules.py`; el agente solo
  aporta `status`, `summary` y `detail` por módulo.
- El módulo `internet` mantiene su propio hilo en el agente: conectividad cada
  minuto, IP pública cada 15 min y test de velocidad cada hora. El histórico se
  persiste en el volumen `agent-data` (`/data/internet-history.json`).
- El módulo `opencode` inspecciona su contenedor por el socket Docker (recursos,
montajes, configuración y logs). El módulo de clima usa Open-Meteo (sin clave) y guarda un histórico diario en
`/data/weather-history.json`; el de base de datos consulta `pg_stat_*` de
`homelabdash` y guarda snapshots en `module_snapshots` cada 5 minutos.

El módulo `devices` sondea la red con UDP y lee la tabla ARP del host
  (`/host/proc/1/net/arp`); guarda el inventario en
  `/data/network-devices.json`. Con credenciales del router consulta su TDDP
  (solo lectura) para obtener SSID, nombres y tasas; el consumo se estima
  integrando `(up + down) × intervalo` y se etiqueta como estimado. El total
  de Internet usa `inOctets`/`outOctets` del WAN; el ciclo se corta el día 10
  (zona configurable) y el día a las 00:00; se archivan históricos diario y
  mensual por dispositivo.

## Seguridad

- Backend y agente publicados solo en `127.0.0.1`; el túnel llega al frontend.
- Token interno agente ↔ backend, distinto del JWT de usuario.
- Contraseña de administrador con hash (bcrypt/argon2), no en texto plano.
- Socket de Docker **solo** en el agente, montado en `ro`; el código solo hace
  lecturas (lista, stats, logs), nunca start/stop.
- Contenedores sin `privileged`, procesos no root, imágenes con versión fija.
- Secretos en `.env` fuera de Git; `ACCESOS.md` ignorado por Git.
- Rate limit en login y auditoría de accesos.

## PWA y escritorio

- `manifest.webmanifest` con iconos 192/512 y `display: standalone`.
- Service worker: cachea el shell y la última vista; nunca cachea datos sensibles.
- Instalable en iOS/iPadOS, Android, Windows y macOS desde el navegador.
- Layout responsive: grid de 1 columna en móvil, 2–4 en escritorio.
- Fase posterior: wrapper de escritorio (Tauri) reutilizando el mismo frontend.

## Despliegue

- Código en `/opt/apps/HomeLabDash` del servidor.
- `docker compose -f ops/compose.prod.yaml up -d --build`.
- Backend en `apps-net` para hablar con `postgres:5432`.
- Frontend en `127.0.0.1:8083`.
- Cloudflare: `homelabdash.hapmed.qzz.io` → `http://localhost:8083`.
- Migraciones Alembic al arrancar o en un contenedor efímero.

## Fases

1. **Base:** monorepo, compose, healthchecks, login, PWA shell, dashboard vacío.
2. **Módulos núcleo:** resumen, CPU, memoria, discos.
3. **Host:** Docker, red, temperatura, servicios.
4. **Operación:** Cloudflare, backups, alertas e histórico.
5. **Escritorio:** PWA pulida y wrapper Tauri opcional.

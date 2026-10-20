# Módulos — HomeLabDash

Cada módulo es un widget del dashboard y una página de detalle en
`/modulo/<id>`. El estado se calcula en el agente y se expone por la API.

> **Estado (Fase 1):** implementados y desplegados `overview`, `cpu`, `memory`,
> `storage`, `internet` y `devices`. El resto está en el registro con
> `enabled=false` hasta su fase.

## Catálogo

| ID | Módulo | Widget (resumen) | Detalle | Fuente | Fase |
|---|---|---|---|---|---|
| `overview` | Resumen | CPU, RAM, carga, uptime, alertas | Estado general y accesos rápidos | agente | 1 |
| `cpu` | CPU | % de uso y carga 1m | Por núcleo, frecuencia, histórico | `/proc/stat`, psutil | 2 |
| `memory` | Memoria | RAM usada / total | RAM, swap, presión, top procesos | `/proc/meminfo`, psutil | 2 |
| `storage` | Discos | % del disco raíz | Puntos de montaje, I/O, SMART | `df`, psutil | 2 |
| `internet` | Internet | Bajada (Mbps) e IP pública | Histórico, subida, latencia, ISP | Cloudflare speedtest, ipinfo | 1 |
| `devices` | Dispositivos | Dispositivos en línea | Inventario, nombres, SSID, tasas, consumo diario/mensual e histórico | ARP del host + router AC12 | 1 |
| `docker` | Docker | Contenedores activos / total | Lista, estado, CPU/RAM, logs | Docker socket (ro) | 3 |
| `network` | Red | Tráfico actual | Interfaces, RX/TX, errores | `/proc/net/dev` | 3 |
| `temperature` | Temperatura | Temperatura máxima | Sensores por zona | `/sys/class/thermal` | 3 |
| `services` | Servicios | Servicios activos | Puertos, unidades, uptime | `systemctl`, sockets | 3 |
| `cloudflare` | Cloudflare | Estado del túnel | Latencia, conexiones, hostnames | API/cloudflared | 4 |
| `backups` | Backups | Último backup | Historial y resultado | job local | 4 |
| `alerts` | Alertas | Alertas activas | Umbrales e historial | BD | 4 |

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

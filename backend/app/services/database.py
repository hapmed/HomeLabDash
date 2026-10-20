"""Estadísticas de la base de datos PostgreSQL (solo lectura).

Consulta únicamente la base actual (`homelabdash`). No toca `hapmed` ni
`evas_admin`. Todas las consultas son de metadatos y `pg_stat_*`.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.snapshot import ModuleSnapshot
from app.schemas.module import ModuleCard, ModuleDetail, ModuleStatus, ModuleSummary
from app.services.modules import ModuleMeta

DB_INFO_SQL = text(
    """
    SELECT current_database() AS name,
           pg_database_size(current_database()) AS size_bytes,
           pg_size_pretty(pg_database_size(current_database())) AS size_pretty,
           current_setting('server_version') AS server_version,
           version() AS version_full,
           pg_postmaster_start_time() AS started_at
    """
)

CONNECTIONS_SQL = text(
    """
    SELECT count(*) FILTER (WHERE datname = current_database()) AS current,
           count(*) FILTER (
               WHERE datname = current_database() AND state = 'active'
           ) AS active,
           count(*) FILTER (
               WHERE datname = current_database() AND state = 'idle'
           ) AS idle,
           count(*) FILTER (
               WHERE datname = current_database()
                 AND state = 'idle in transaction'
           ) AS idle_in_transaction,
           count(*) FILTER (
               WHERE datname = current_database()
                 AND state = 'idle in transaction (aborted)'
           ) AS idle_in_transaction_aborted,
           coalesce(
               max(EXTRACT(EPOCH FROM (now() - query_start))) FILTER (
                   WHERE datname = current_database()
                     AND state = 'active'
                     AND query_start IS NOT NULL
               ), 0
           ) AS longest_query_seconds,
           coalesce(
               max(EXTRACT(EPOCH FROM (now() - xact_start))) FILTER (
                   WHERE datname = current_database()
                     AND xact_start IS NOT NULL
               ), 0
           ) AS longest_transaction_seconds
    FROM pg_stat_activity
    """
)

DATABASE_STATS_SQL = text(
    """
    SELECT xact_commit, xact_rollback, blks_read, blks_hit,
           tup_returned, tup_fetched, tup_inserted, tup_updated, tup_deleted,
           conflicts, temp_files, temp_bytes, deadlocks,
           blk_read_time, blk_write_time, stats_reset
    FROM pg_stat_database
    WHERE datname = current_database()
    """
)

TABLES_SQL = text(
    """
    SELECT schemaname, relname, n_live_tup, n_dead_tup,
           n_tup_ins, n_tup_upd, n_tup_del,
           seq_scan, seq_tup_read, idx_scan, idx_tup_fetch,
           pg_total_relation_size(relid) AS total_bytes,
           pg_relation_size(relid) AS heap_bytes,
           pg_indexes_size(relid) AS index_bytes,
           greatest(
               pg_total_relation_size(relid)
               - pg_relation_size(relid)
               - pg_indexes_size(relid), 0
           ) AS toast_bytes,
           last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
    FROM pg_stat_user_tables
    ORDER BY total_bytes DESC
    LIMIT 30
    """
)

INDEXES_SQL = text(
    """
    SELECT schemaname, relname AS table_name, indexrelname,
           idx_scan, idx_tup_read, idx_tup_fetch,
           pg_relation_size(indexrelid) AS size_bytes
    FROM pg_stat_user_indexes
    ORDER BY size_bytes DESC
    LIMIT 30
    """
)

COUNTS_SQL = text(
    """
    SELECT
      (SELECT count(*) FROM pg_stat_user_tables) AS tables,
      (SELECT count(*) FROM pg_stat_user_indexes) AS indexes,
      (SELECT coalesce(sum(n_dead_tup), 0) FROM pg_stat_user_tables) AS dead_tuples,
      (SELECT coalesce(sum(n_live_tup), 0) FROM pg_stat_user_tables) AS live_tuples,
      (SELECT count(*) FROM pg_locks WHERE NOT granted) AS waiting_locks
    """
)

SETTINGS_SQL = text(
    """
    SELECT name, setting, unit
    FROM pg_settings
    WHERE name IN (
        'max_connections', 'shared_buffers', 'work_mem',
        'maintenance_work_mem', 'effective_cache_size', 'autovacuum'
    )
    """
)

STATES_SQL = text(
    """
    SELECT coalesce(state, 'unknown') AS state, count(*) AS count
    FROM pg_stat_activity
    WHERE datname = current_database()
    GROUP BY 1
    ORDER BY 2 DESC
    """
)


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _database_name() -> str:
    return "homelabdash"


def collect_stats(db: Session) -> dict[str, Any]:
    """Recoge estadísticas de la base actual. Lanza excepción si la BD falla."""
    info = db.execute(DB_INFO_SQL).mappings().first()
    connections = db.execute(CONNECTIONS_SQL).mappings().first()
    activity = db.execute(DATABASE_STATS_SQL).mappings().first()
    counts = db.execute(COUNTS_SQL).mappings().first()
    settings_rows = db.execute(SETTINGS_SQL).mappings().all()
    tables_rows = db.execute(TABLES_SQL).mappings().all()
    indexes_rows = db.execute(INDEXES_SQL).mappings().all()
    states_rows = db.execute(STATES_SQL).mappings().all()

    settings = {
        str(row["name"]): {"setting": row["setting"], "unit": row["unit"]}
        for row in settings_rows
    }
    max_connections = _int(settings.get("max_connections", {}).get("setting"), 100)

    tables = [
        {
            "schema": row["schemaname"],
            "name": row["relname"],
            "rows": _int(row["n_live_tup"]),
            "dead_rows": _int(row["n_dead_tup"]),
            "inserted": _int(row["n_tup_ins"]),
            "updated": _int(row["n_tup_upd"]),
            "deleted": _int(row["n_tup_del"]),
            "seq_scan": _int(row["seq_scan"]),
            "seq_tup_read": _int(row["seq_tup_read"]),
            "idx_scan": _int(row["idx_scan"]),
            "idx_tup_fetch": _int(row["idx_tup_fetch"]),
            "total_bytes": _int(row["total_bytes"]),
            "heap_bytes": _int(row["heap_bytes"]),
            "index_bytes": _int(row["index_bytes"]),
            "toast_bytes": _int(row["toast_bytes"]),
            "last_vacuum": _iso(row["last_vacuum"]),
            "last_autovacuum": _iso(row["last_autovacuum"]),
            "last_analyze": _iso(row["last_analyze"]),
            "last_autoanalyze": _iso(row["last_autoanalyze"]),
        }
        for row in tables_rows
    ]
    indexes = [
        {
            "schema": row["schemaname"],
            "table": row["table_name"],
            "name": row["indexrelname"],
            "scans": _int(row["idx_scan"]),
            "tuples_read": _int(row["idx_tup_read"]),
            "tuples_fetched": _int(row["idx_tup_fetch"]),
            "size_bytes": _int(row["size_bytes"]),
        }
        for row in indexes_rows
    ]

    if info is None or connections is None or activity is None or counts is None:
        raise RuntimeError("PostgreSQL no devolvió estadísticas")

    size_bytes = _int(info["size_bytes"])
    size_pretty = str(info["size_pretty"])
    started_at = info["started_at"]
    uptime_seconds = (
        max(0, int((datetime.now(UTC) - started_at).total_seconds()))
        if isinstance(started_at, datetime)
        else 0
    )
    current_connections = _int(connections["current"])
    connection_percent = (
        round(current_connections / max_connections * 100, 1) if max_connections else 0.0
    )
    blks_hit = _int(activity["blks_hit"])
    blks_read = _int(activity["blks_read"])
    cache_hit_ratio = (
        round(blks_hit / (blks_hit + blks_read) * 100, 2) if blks_hit + blks_read else 100.0
    )
    dead_tuples = _int(counts["dead_tuples"])
    live_tuples = _int(counts["live_tuples"])
    dead_ratio = (
        round(dead_tuples / (dead_tuples + live_tuples) * 100, 1)
        if dead_tuples + live_tuples
        else 0.0
    )
    waiting_locks = _int(counts["waiting_locks"])
    longest_query = _float(connections["longest_query_seconds"])
    longest_transaction = _float(connections["longest_transaction_seconds"])

    settings_obj = get_settings()
    alerts: list[str] = []
    status: ModuleStatus = "ok"
    if connection_percent >= settings_obj.database_connection_critical_percent:
        status = "critical"
        alerts.append(f"Conexiones al {connection_percent:.0f}% ({current_connections}/{max_connections})")
    elif connection_percent >= settings_obj.database_connection_warn_percent:
        status = "warn"
        alerts.append(f"Conexiones al {connection_percent:.0f}% ({current_connections}/{max_connections})")
    if cache_hit_ratio < settings_obj.database_cache_warn_percent:
        status = "warn" if status == "ok" else status
        alerts.append(f"Caché de PostgreSQL al {cache_hit_ratio:.1f}%")
    if dead_ratio >= settings_obj.database_dead_tuple_warn_percent and dead_tuples > 1000:
        status = "warn" if status == "ok" else status
        alerts.append(f"{dead_ratio:.1f}% de tuplas muertas ({dead_tuples})")
    if waiting_locks > 0:
        status = "warn" if status == "ok" else status
        alerts.append(f"{waiting_locks} bloqueo(s) en espera")
    if longest_query >= settings_obj.database_long_query_warn_seconds:
        status = "warn" if status == "ok" else status
        alerts.append(f"Consulta activa desde hace {longest_query:.0f} s")

    summary = {
        "label": "Tamaño",
        "value": size_pretty,
        "detail": (
            f"{_int(counts['tables'])} tablas · "
            f"{current_connections}/{max_connections} conexiones · "
            f"caché {cache_hit_ratio:.1f}%"
        ),
    }
    detail = {
        "database": {
            "name": str(info["name"]),
            "size_bytes": size_bytes,
            "size_pretty": size_pretty,
            "server_version": str(info["server_version"]),
            "version": str(info["version_full"]).split(" on ")[0],
            "started_at": _iso(started_at),
            "uptime_seconds": uptime_seconds,
            "tables": _int(counts["tables"]),
            "indexes": _int(counts["indexes"]),
        },
        "connections": {
            "current": current_connections,
            "max": max_connections,
            "percent": connection_percent,
            "active": _int(connections["active"]),
            "idle": _int(connections["idle"]),
            "idle_in_transaction": _int(connections["idle_in_transaction"])
            + _int(connections["idle_in_transaction_aborted"]),
            "waiting_locks": waiting_locks,
            "longest_query_seconds": round(longest_query, 1),
            "longest_transaction_seconds": round(longest_transaction, 1),
            "states": [
                {"state": str(row["state"]), "count": _int(row["count"])} for row in states_rows
            ],
        },
        "activity": {
            "xact_commit": _int(activity["xact_commit"]),
            "xact_rollback": _int(activity["xact_rollback"]),
            "blks_read": blks_read,
            "blks_hit": blks_hit,
            "cache_hit_ratio": cache_hit_ratio,
            "tup_returned": _int(activity["tup_returned"]),
            "tup_fetched": _int(activity["tup_fetched"]),
            "tup_inserted": _int(activity["tup_inserted"]),
            "tup_updated": _int(activity["tup_updated"]),
            "tup_deleted": _int(activity["tup_deleted"]),
            "conflicts": _int(activity["conflicts"]),
            "temp_files": _int(activity["temp_files"]),
            "temp_bytes": _int(activity["temp_bytes"]),
            "deadlocks": _int(activity["deadlocks"]),
            "blk_read_time": round(_float(activity["blk_read_time"]), 2),
            "blk_write_time": round(_float(activity["blk_write_time"]), 2),
            "stats_reset": _iso(activity["stats_reset"]),
            "live_tuples": live_tuples,
            "dead_tuples": dead_tuples,
            "dead_ratio": dead_ratio,
        },
        "tables": tables,
        "indexes": indexes,
        "settings": settings,
        "alerts": alerts,
    }
    return {
        "status": status,
        "summary": summary,
        "detail": detail,
        "sampled_at": datetime.now(UTC).isoformat(),
    }


def unavailable_stats(exc: Exception) -> dict[str, Any]:
    message = f"Base de datos no disponible ({type(exc).__name__})"
    return {
        "status": "critical",
        "summary": {"label": "Tamaño", "value": "—", "detail": message},
        "detail": {"error": message, "database": {"name": _database_name()}},
        "sampled_at": datetime.now(UTC).isoformat(),
    }


def get_history(db: Session, hours: int = 24) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    try:
        rows = db.scalars(
            select(ModuleSnapshot)
            .where(
                ModuleSnapshot.module_id == "database",
                ModuleSnapshot.captured_at >= cutoff,
            )
            .order_by(ModuleSnapshot.captured_at.asc())
            .limit(600)
        ).all()
    except Exception:  # noqa: BLE001 - el histórico no debe romper el detalle
        return []
    history: list[dict[str, Any]] = []
    for row in rows:
        payload = row.payload if isinstance(row.payload, dict) else {}
        raw_metrics = payload.get("metrics")
        metrics: dict[str, Any] = raw_metrics if isinstance(raw_metrics, dict) else payload
        history.append(
            {
                "at": row.captured_at.isoformat() if row.captured_at else None,
                "size_bytes": _int(metrics.get("size_bytes")),
                "connections": _int(metrics.get("connections")),
                "cache_hit_ratio": _float(metrics.get("cache_hit_ratio")),
            }
        )
    return history


def build_card(meta: ModuleMeta, stats: dict[str, Any]) -> ModuleCard:
    updated_at: datetime | None = None
    raw = stats.get("sampled_at")
    if isinstance(raw, str):
        try:
            updated_at = datetime.fromisoformat(raw)
        except ValueError:
            updated_at = None
    return ModuleCard(
        id=meta.id,
        name=meta.name,
        description=meta.description,
        icon=meta.icon,
        order=meta.order,
        enabled=meta.enabled,
        status=cast(ModuleStatus, stats["status"]),
        summary=ModuleSummary.model_validate(stats["summary"]),
        updated_at=updated_at,
    )


def build_detail(
    meta: ModuleMeta, stats: dict[str, Any], history: list[dict[str, Any]]
) -> ModuleDetail:
    card = build_card(meta, stats)
    available = stats["status"] != "critical"
    detail = dict(stats["detail"])
    detail["history"] = history
    return ModuleDetail(
        **card.model_dump(),
        available=available,
        detail=detail,
        error=None if available else detail.get("error"),
    )

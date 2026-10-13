"""
AegisOps AI - Operational Database Access & Schema Initialization
Manages connection pools to aegisops_db and executes idempotent schema migrations and batch inserts.
"""

import os
from pathlib import Path
from typing import Any, List, Optional, Tuple
import asyncpg

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "infrastructure" / "postgres" / "schema.sql"


def get_postgres_dsn(database: str = "aegisops_db") -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def get_connection_pool(
    database: str = "aegisops_db",
    min_size: int = 2,
    max_size: int = 10,
) -> asyncpg.Pool:
    dsn = get_postgres_dsn(database)
    return await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)


async def init_db_schema(pool: Optional[asyncpg.Pool] = None) -> bool:
    """Executes schema.sql against aegisops_db idempotently."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    sql_content = SCHEMA_PATH.read_text(encoding="utf-8")

    if pool:
        async with pool.acquire() as conn:
            await conn.execute(sql_content)
        return True
    else:
        dsn = get_postgres_dsn("aegisops_db")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(sql_content)
            return True
        finally:
            await conn.close()


async def batch_insert_logs(pool: asyncpg.Pool, log_rows: List[Tuple]) -> int:
    if not log_rows:
        return 0
    query = """
    INSERT INTO raw_logs (id, timestamp, service, level, message, environment, trace_id, metadata)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
    ON CONFLICT (id) DO NOTHING;
    """
    async with pool.acquire() as conn:
        await conn.executemany(query, log_rows)
    return len(log_rows)


async def batch_insert_metrics(pool: asyncpg.Pool, metric_rows: List[Tuple]) -> int:
    if not metric_rows:
        return 0
    query = """
    INSERT INTO raw_metrics (id, timestamp, service, metric_name, value, unit, dimensions)
    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
    ON CONFLICT (id) DO NOTHING;
    """
    async with pool.acquire() as conn:
        await conn.executemany(query, metric_rows)
    return len(metric_rows)


async def batch_insert_deployments(pool: asyncpg.Pool, deployment_rows: List[Tuple]) -> int:
    if not deployment_rows:
        return 0
    query = """
    INSERT INTO deployment_events (id, timestamp, service, version, previous_version, git_commit, author, status, metadata)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
    ON CONFLICT (id) DO NOTHING;
    """
    async with pool.acquire() as conn:
        await conn.executemany(query, deployment_rows)
    return len(deployment_rows)


async def insert_incident(pool: asyncpg.Pool, incident_row: Tuple) -> str:
    query = """
    INSERT INTO incidents (incident_id, title, service, severity, status, created_at, updated_at, summary, primary_root_cause, confidence_score, metadata)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
    ON CONFLICT (incident_id) DO UPDATE SET
        updated_at = EXCLUDED.updated_at,
        status = EXCLUDED.status,
        summary = EXCLUDED.summary,
        metadata = EXCLUDED.metadata;
    """
    async with pool.acquire() as conn:
        await conn.execute(query, *incident_row)
    return incident_row[0]

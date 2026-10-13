"""
AegisOps AI - Database Diagnostic Tools
Implements health checks, connection pool metrics, slow query analysis,
active connection introspection, and validated read-only SQL queries.
"""

import time
from typing import Any, Dict, List, Optional
import asyncpg

from apps.common.mcp.budget import TokenBudgetGuard
from apps.mcp_database.models import (
    ActiveConnectionItem,
    ActiveConnectionsResult,
    ConnectionPoolResult,
    DatabaseHealthResult,
    ReadOnlyQueryInput,
    ReadOnlyQueryResult,
    SlowQueriesInput,
    SlowQueryItem,
    SlowQueriesResult,
)
from apps.mcp_database.validator import SQLMutationValidator


class DatabaseTools:
    """
    Diagnostic tooling for the target database (demo_payment_db).
    Operates against an asyncpg connection pool or provides high-fidelity in-memory mock telemetry.
    """

    def __init__(
        self,
        pool: Optional[asyncpg.Pool] = None,
        mock_data: Optional[Dict[str, Any]] = None,
    ):
        self.pool = pool
        self.mock_data = mock_data or self._default_mock_data()

    def _default_mock_data(self) -> Dict[str, Any]:
        """Provides realistic default telemetry for demo_payment_db."""
        return {
            "health": {
                "database": "demo_payment_db",
                "status": "healthy",
                "version": "PostgreSQL 16.2 on x86_64-pc-linux-gnu",
                "uptime_seconds": 124500.0,
                "database_size_bytes": 48234496,
                "total_connections": 12,
                "max_connections": 50,
            },
            "pool": {
                "database": "demo_payment_db",
                "total_connections": 12,
                "active_connections": 4,
                "idle_connections": 7,
                "idle_in_transaction": 1,
                "waiting_connections": 0,
                "max_connections": 50,
            },
            "slow_queries": [
                {
                    "pid": 2041,
                    "duration_ms": 1450.5,
                    "query": "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at ASC",
                    "state": "active",
                    "wait_event_type": "IO",
                    "wait_event": "DataFileRead",
                },
                {
                    "pid": 2045,
                    "duration_ms": 420.0,
                    "query": "SELECT count(*) FROM audit_logs WHERE created_at < NOW() - INTERVAL '30 days'",
                    "state": "active",
                    "wait_event_type": None,
                    "wait_event": None,
                },
            ],
            "active_connections": [
                {
                    "pid": 2041,
                    "usename": "payment_user",
                    "client_addr": "172.20.0.5",
                    "state": "active",
                    "wait_event_type": "IO",
                    "wait_event": "DataFileRead",
                    "duration_seconds": 1.45,
                    "query_preview": "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at ASC",
                },
                {
                    "pid": 2042,
                    "usename": "payment_user",
                    "client_addr": "172.20.0.5",
                    "state": "idle in transaction",
                    "wait_event_type": "Client",
                    "wait_event": "ClientRead",
                    "duration_seconds": 0.05,
                    "query_preview": "SELECT balance FROM accounts WHERE id = 'acc_1001'",
                },
            ],
            "mock_tables": {
                "payments": [
                    {"id": "pay_001", "account_id": "acc_1001", "amount": 150.0, "status": "completed", "created_at": "2026-10-10T08:00:00Z"},
                    {"id": "pay_002", "account_id": "acc_1002", "amount": 89.5, "status": "failed", "created_at": "2026-10-10T08:05:00Z"},
                    {"id": "pay_003", "account_id": "acc_1003", "amount": 2500.0, "status": "failed", "created_at": "2026-10-10T08:10:00Z"},
                    {"id": "pay_004", "account_id": "acc_1001", "amount": 42.0, "status": "completed", "created_at": "2026-10-10T08:15:00Z"},
                ]
            },
        }

    async def get_database_health(self) -> DatabaseHealthResult:
        """Inspects target database operational state, version, and connection totals."""
        if not self.pool:
            data = self.mock_data["health"]
            return DatabaseHealthResult(**data)

        async with self.pool.acquire() as conn:
            version_str = await conn.fetchval("SELECT version();")
            db_size = await conn.fetchval("SELECT pg_database_size(current_database());")
            uptime_sec = await conn.fetchval(
                "SELECT extract(epoch from (now() - pg_postmaster_start_time()));"
            )
            total_conn = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();"
            )

            status = "healthy"
            if total_conn >= 48:
                status = "exhausted"
            elif total_conn >= 40:
                status = "degraded"

            return DatabaseHealthResult(
                database="demo_payment_db",
                status=status,
                version=version_str or "PostgreSQL",
                uptime_seconds=float(uptime_sec or 0.0),
                database_size_bytes=int(db_size or 0),
                total_connections=int(total_conn or 0),
                max_connections=50,
            )

    async def get_connection_pool(self) -> ConnectionPoolResult:
        """Analyzes active, idle, waiting, and leaking connection states."""
        if not self.pool:
            p = self.mock_data["pool"]
            total = p["total_connections"]
            max_conn = p["max_connections"]
            pct = round((total / max_conn) * 100, 2)
            status = "healthy"
            if pct >= 90:
                status = "exhausted"
            elif pct >= 75:
                status = "warning"
            return ConnectionPoolResult(
                database=p["database"],
                total_connections=total,
                active_connections=p["active_connections"],
                idle_connections=p["idle_connections"],
                idle_in_transaction=p["idle_in_transaction"],
                waiting_connections=p["waiting_connections"],
                max_connections=max_conn,
                utilization_percent=pct,
                pool_status=status,
            )

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    state,
                    wait_event IS NOT NULL AS is_waiting,
                    count(*) AS count
                FROM pg_stat_activity
                WHERE datname = current_database()
                GROUP BY state, (wait_event IS NOT NULL);
                """
            )
            active = 0
            idle = 0
            idle_in_tx = 0
            waiting = 0
            total = 0

            for r in rows:
                c = r["count"]
                total += c
                state = r["state"]
                if state == "active":
                    active += c
                elif state == "idle":
                    idle += c
                elif state == "idle in transaction":
                    idle_in_tx += c
                if r["is_waiting"]:
                    waiting += c

            max_conn = 50
            pct = round((total / max_conn) * 100, 2)
            status = "healthy"
            if pct >= 90:
                status = "exhausted"
            elif pct >= 75:
                status = "warning"

            return ConnectionPoolResult(
                database="demo_payment_db",
                total_connections=total,
                active_connections=active,
                idle_connections=idle,
                idle_in_transaction=idle_in_tx,
                waiting_connections=waiting,
                max_connections=max_conn,
                utilization_percent=pct,
                pool_status=status,
            )

    async def get_slow_queries(self, input_data: SlowQueriesInput) -> SlowQueriesResult:
        """Retrieves currently running queries exceeding the duration threshold."""
        if not self.pool:
            filtered = [
                SlowQueryItem(**q)
                for q in self.mock_data["slow_queries"]
                if q["duration_ms"] >= input_data.min_duration_ms
            ][: input_data.limit]
            return SlowQueriesResult(count=len(filtered), queries=filtered)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    pid,
                    extract(epoch from (now() - query_start)) * 1000 AS duration_ms,
                    query,
                    state,
                    wait_event_type,
                    wait_event
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state != 'idle'
                  AND query_start IS NOT NULL
                  AND extract(epoch from (now() - query_start)) * 1000 >= $1
                ORDER BY duration_ms DESC
                LIMIT $2;
                """,
                input_data.min_duration_ms,
                input_data.limit,
            )
            items = [
                SlowQueryItem(
                    pid=r["pid"],
                    duration_ms=float(r["duration_ms"] or 0.0),
                    query=r["query"] or "",
                    state=r["state"] or "",
                    wait_event_type=r["wait_event_type"],
                    wait_event=r["wait_event"],
                )
                for r in rows
            ]
            return SlowQueriesResult(count=len(items), queries=items)

    async def get_active_connections(self) -> ActiveConnectionsResult:
        """Inspects active non-idle backends, client addresses, and running query previews."""
        if not self.pool:
            items = [ActiveConnectionItem(**c) for c in self.mock_data["active_connections"]]
            return ActiveConnectionsResult(count=len(items), connections=items)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    pid,
                    usename,
                    client_addr::text,
                    state,
                    wait_event_type,
                    wait_event,
                    extract(epoch from (now() - query_start)) AS duration_seconds,
                    left(query, 200) AS query_preview
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state != 'idle'
                ORDER BY duration_seconds DESC NULLS LAST
                LIMIT 50;
                """
            )
            items = [
                ActiveConnectionItem(
                    pid=r["pid"],
                    usename=r["usename"],
                    client_addr=r["client_addr"],
                    state=r["state"] or "unknown",
                    wait_event_type=r["wait_event_type"],
                    wait_event=r["wait_event"],
                    duration_seconds=float(r["duration_seconds"] or 0.0),
                    query_preview=r["query_preview"] or "",
                )
                for r in rows
            ]
            return ActiveConnectionsResult(count=len(items), connections=items)

    async def run_readonly_query(self, input_data: ReadOnlyQueryInput) -> ReadOnlyQueryResult:
        """
        Validates SQL through SQLMutationValidator, applies row limits, executes in a
        read-only transaction, and applies token budgeting to protect LLM context windows.
        """
        t0 = time.time()
        # 1. Strict AST / lexical read-only validation
        validated_sql = SQLMutationValidator.validate_sql(input_data.query)
        clamped_row_limit = min(max(1, input_data.row_limit), 100)

        columns: List[str] = []
        raw_rows: List[Dict[str, Any]] = []

        if not self.pool:
            # Mock query runner
            mock_payments = self.mock_data["mock_tables"]["payments"]
            if "payments" in validated_sql.lower():
                columns = ["id", "account_id", "amount", "status", "created_at"]
                raw_rows = mock_payments[:clamped_row_limit]
            else:
                columns = ["result"]
                raw_rows = [{"result": 1}]
        else:
            async with self.pool.acquire() as conn:
                # Enforce read-only transaction and statement timeout
                timeout_ms = int(input_data.timeout_seconds * 1000)
                async with conn.transaction(readonly=True):
                    await conn.execute(f"SET LOCAL statement_timeout = {timeout_ms};")
                    # Fetch records bounded by clamped limit
                    records = await conn.fetch(f"{validated_sql} LIMIT {clamped_row_limit};")
                    if records:
                        columns = list(records[0].keys())
                        raw_rows = [dict(r) for r in records]

        # 2. Token budgeting and pagination
        pagination = TokenBudgetGuard.paginate_records(
            items=raw_rows,
            limit=clamped_row_limit,
            max_tokens=4000,
        )
        budgeted_rows = pagination["items"]
        truncated = pagination["truncated_by_budget"]
        token_count = pagination["estimated_tokens"]
        duration_ms = round((time.time() - t0) * 1000, 2)

        return ReadOnlyQueryResult(
            query=validated_sql,
            row_count=len(budgeted_rows),
            columns=columns,
            rows=budgeted_rows,
            execution_duration_ms=duration_ms,
            token_count=token_count,
            truncated=truncated,
        )

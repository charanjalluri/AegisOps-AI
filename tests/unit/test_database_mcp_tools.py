"""
Unit tests for Database diagnostic tools (apps.mcp_database.tools).
Tests health checks, connection pool metrics, slow query filtering,
active connection introspection, and read-only query execution offline.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from apps.mcp_database.models import ReadOnlyQueryInput, SlowQueriesInput
from apps.mcp_database.tools import DatabaseTools


@pytest.mark.anyio
async def test_get_database_health_mock():
    tools = DatabaseTools()
    health = await tools.get_database_health()
    assert health.database == "demo_payment_db"
    assert health.status == "healthy"
    assert "PostgreSQL" in health.version
    assert health.uptime_seconds > 0
    assert health.max_connections == 50


@pytest.mark.anyio
async def test_get_connection_pool_mock():
    tools = DatabaseTools()
    pool_res = await tools.get_connection_pool()
    assert pool_res.database == "demo_payment_db"
    assert pool_res.total_connections == 12
    assert pool_res.active_connections == 4
    assert pool_res.idle_connections == 7
    assert pool_res.max_connections == 50
    assert pool_res.utilization_percent == 24.0
    assert pool_res.pool_status == "healthy"


@pytest.mark.anyio
async def test_get_slow_queries_mock():
    tools = DatabaseTools()
    res = await tools.get_slow_queries(SlowQueriesInput(min_duration_ms=500.0, limit=5))
    assert res.count == 1
    assert res.queries[0].pid == 2041
    assert res.queries[0].duration_ms > 1000

    res_all = await tools.get_slow_queries(SlowQueriesInput(min_duration_ms=50.0, limit=5))
    assert res_all.count == 2


@pytest.mark.anyio
async def test_get_active_connections_mock():
    tools = DatabaseTools()
    res = await tools.get_active_connections()
    assert res.count == 2
    assert res.connections[0].pid == 2041
    assert res.connections[0].state == "active"
    assert "SELECT * FROM payments" in res.connections[0].query_preview


@pytest.mark.anyio
async def test_run_readonly_query_mock():
    tools = DatabaseTools()
    res = await tools.run_readonly_query(
        ReadOnlyQueryInput(query="SELECT * FROM payments WHERE status = 'failed'", row_limit=2)
    )
    assert res.row_count == 2
    assert "id" in res.columns
    assert "amount" in res.columns
    assert res.token_count > 0
    assert not res.truncated


@pytest.mark.anyio
async def test_run_readonly_query_rejects_mutations():
    tools = DatabaseTools()
    with pytest.raises(ValueError, match="DELETE"):
        await tools.run_readonly_query(
            ReadOnlyQueryInput(query="DELETE FROM payments WHERE status = 'failed'")
        )

    with pytest.raises(ValueError, match="DROP"):
        await tools.run_readonly_query(
            ReadOnlyQueryInput(query="DROP TABLE payments")
        )


@pytest.mark.anyio
async def test_run_readonly_query_with_mock_asyncpg_pool():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    # Setup transaction context manager
    mock_tx = AsyncMock()
    mock_tx.__aenter__.return_value = None
    mock_tx.__aexit__.return_value = None
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    mock_record_1 = {"id": "pay_999", "amount": 100.0, "status": "failed"}
    mock_record_2 = {"id": "pay_998", "amount": 200.0, "status": "failed"}
    mock_conn.fetch.return_value = [mock_record_1, mock_record_2]

    # Setup acquire context manager
    mock_acquire = AsyncMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire.return_value = mock_acquire

    tools = DatabaseTools(pool=mock_pool)
    res = await tools.run_readonly_query(
        ReadOnlyQueryInput(query="SELECT id, amount, status FROM payments WHERE status = 'failed'", row_limit=5)
    )

    assert res.row_count == 2
    assert res.columns == ["id", "amount", "status"]
    assert res.rows[0]["id"] == "pay_999"
    mock_conn.transaction.assert_called_once_with(readonly=True)

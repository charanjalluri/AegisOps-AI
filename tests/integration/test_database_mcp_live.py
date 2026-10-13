"""
Integration test for Database MCP server against live running PostgreSQL demo_payment_db.
Decorated with @pytest.mark.integration so it does not run in offline test passes.
"""

import pytest

from apps.mcp_database.server import create_database_mcp_server


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_database_mcp_query():
    import asyncpg
    from apps.ingestion.database import get_connection_pool

    try:
        pool = await get_connection_pool("demo_payment_db")
        server = create_database_mcp_server(pool=pool)
        resp = await server.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": "live-db-1",
            "method": "tools/call",
            "params": {
                "name": "run_readonly_query",
                "arguments": {"query": "SELECT 1 AS live_check", "row_limit": 1},
            },
        })
        assert resp.error is None
        assert not resp.result.is_error
        await pool.close()
    except (OSError, asyncpg.PostgresError) as e:
        pytest.skip(f"Live PostgreSQL demo_payment_db not reachable on localhost:5432: {e}")

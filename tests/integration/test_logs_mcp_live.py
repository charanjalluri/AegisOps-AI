"""
Integration test for Logs MCP server against live running PostgreSQL container.
Decorated with @pytest.mark.integration so it does not run in offline test passes.
"""

import pytest
from httpx import AsyncClient

from apps.mcp_logs.models import SearchLogsInput
from apps.mcp_logs.server import create_logs_mcp_server


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_logs_mcp_postgres_query():
    import asyncpg
    from apps.ingestion.database import get_connection_pool

    try:
        pool = await get_connection_pool("aegisops_db")
        server = create_logs_mcp_server(pool=pool)
        resp = await server.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": "live-1",
            "method": "tools/call",
            "params": {"name": "search_logs", "arguments": {"limit": 10}},
        })
        assert resp.error is None
        await pool.close()
    except (OSError, asyncpg.PostgresError) as e:
        pytest.skip(f"Live PostgreSQL not reachable on localhost:5432: {e}")

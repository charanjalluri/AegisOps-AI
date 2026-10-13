"""
Integration test for Incident MCP server against live running PostgreSQL aegisops_db and Kafka.
Decorated with @pytest.mark.integration so it does not run in offline test passes.
"""

import pytest

from apps.mcp_incident.server import create_incident_mcp_server
from apps.mcp_incident.storage import InvestigationStorage


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_incident_mcp_storage():
    import asyncpg
    from apps.ingestion.database import get_connection_pool

    try:
        pool = await get_connection_pool("aegisops_db")
        storage = InvestigationStorage(pool=pool)
        await storage.init_schema()
        server = create_incident_mcp_server(storage=storage)

        resp = await server.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": "live-inc-1",
            "method": "tools/call",
            "params": {
                "name": "create_incident",
                "arguments": {
                    "incident_id": "live-test-inc-1",
                    "title": "Live PostgreSQL integration incident",
                    "service": "payment-service",
                    "severity": "SEV-2",
                },
            },
        })
        assert resp.error is None
        assert not resp.result["is_error"]
        await pool.close()
    except (OSError, asyncpg.PostgresError) as e:
        pytest.skip(f"Live PostgreSQL aegisops_db not reachable on localhost:5432: {e}")

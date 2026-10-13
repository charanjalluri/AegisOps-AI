"""
AegisOps AI - Database MCP Server Factory
Registers all 5 database diagnostic tools on BaseMCPServer with JSON-RPC 2.0 schemas.
"""

from typing import Any, Dict, Optional
import asyncpg

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_database.models import ReadOnlyQueryInput, SlowQueriesInput
from apps.mcp_database.tools import DatabaseTools


def create_database_mcp_server(
    pool: Optional[asyncpg.Pool] = None,
    mock_data: Optional[Dict[str, Any]] = None,
) -> BaseMCPServer:
    """Creates and configures the Database MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-database-mcp",
        version="0.1.0",
        description="Strictly read-only database health, connection pool introspection, and SQL diagnostic MCP server",
    )
    tools = DatabaseTools(pool=pool, mock_data=mock_data)

    @server.tool(
        name="get_database_health",
        description="Inspect target database operational status, uptime, version, and connection totals",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
    )
    async def get_database_health():
        res = await tools.get_database_health()
        return res.model_dump(mode="json")

    @server.tool(
        name="get_connection_pool",
        description="Retrieve connection pool metrics including active, idle, waiting connections, and utilization %",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
    )
    async def get_connection_pool():
        res = await tools.get_connection_pool()
        return res.model_dump(mode="json")

    @server.tool(
        name="get_slow_queries",
        description="Retrieve currently executing queries exceeding a duration threshold (ms)",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=SlowQueriesInput,
    )
    async def get_slow_queries(input_data: SlowQueriesInput):
        res = await tools.get_slow_queries(input_data)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_active_connections",
        description="Inspect active client backends, process IDs, wait events, query previews, and client addresses",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
    )
    async def get_active_connections():
        res = await tools.get_active_connections()
        return res.model_dump(mode="json")

    @server.tool(
        name="run_readonly_query",
        description="Execute a strictly validated single-statement read-only SELECT query against demo_payment_db",
        timeout_seconds=15.0,
        rate_limit_rpm=60,
        pydantic_model=ReadOnlyQueryInput,
    )
    async def run_readonly_query(input_data: ReadOnlyQueryInput):
        res = await tools.run_readonly_query(input_data)
        return res.model_dump(mode="json")

    return server

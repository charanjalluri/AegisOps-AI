"""
AegisOps AI - Logs MCP Server Factory
Registers all 5 log introspection tools on BaseMCPServer with JSON-RPC 2.0 schemas and timeout enforcement.
"""

from typing import Any, Dict, List, Optional
import asyncpg

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_logs.models import (
    GetCorrelatedErrorsInput,
    GetErrorRateInput,
    GetLogsAroundEventInput,
    GetServiceLogsInput,
    SearchLogsInput,
)
from apps.mcp_logs.tools import LogsTools


def create_logs_mcp_server(
    pool: Optional[asyncpg.Pool] = None,
    in_memory_logs: Optional[List[Dict[str, Any]]] = None,
) -> BaseMCPServer:
    """Creates and configures the Logs MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-logs-mcp",
        version="0.1.0",
        description="Read-only log introspection, error rate analytics, and window extraction MCP server",
    )
    tools = LogsTools(pool=pool, in_memory_logs=in_memory_logs)

    @server.tool(
        name="search_logs",
        description="Search and filter logs by service, level, pattern, and time range with token budgeting",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=SearchLogsInput,
    )
    async def search_logs(input_data: SearchLogsInput):
        res = await tools.search_logs(input_data)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_service_logs",
        description="Get recent logs for a specific service with minimum level filter",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetServiceLogsInput,
    )
    async def get_service_logs(input_data: GetServiceLogsInput):
        res = await tools.get_service_logs(input_data)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_error_rate",
        description="Calculate log error rates grouped into time interval buckets",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetErrorRateInput,
    )
    async def get_error_rate(input_data: GetErrorRateInput):
        res = await tools.get_error_rate(input_data)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_correlated_errors",
        description="Find temporal log correlations and nearby events around specific error patterns",
        timeout_seconds=20.0,
        rate_limit_rpm=60,
        pydantic_model=GetCorrelatedErrorsInput,
    )
    async def get_correlated_errors(input_data: GetCorrelatedErrorsInput):
        res = await tools.get_correlated_errors(input_data)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_logs_around_event",
        description="Extract a chronological log window spanning before and after an event timestamp",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetLogsAroundEventInput,
    )
    async def get_logs_around_event(input_data: GetLogsAroundEventInput):
        res = await tools.get_logs_around_event(input_data)
        return res.model_dump(mode="json")

    return server

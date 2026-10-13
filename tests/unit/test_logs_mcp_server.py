"""
Tests for apps.mcp_logs.server and apps.mcp_logs.main
Verifies Logs MCP server registration, JSON-RPC 2.0 dispatch for all 5 tools,
and HTTP endpoints offline.
"""

from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
import pytest

from apps.common.mcp.protocol import MCPErrorCode
from apps.mcp_logs.main import app
from apps.mcp_logs.server import create_logs_mcp_server


@pytest.fixture
def test_server():
    base_time = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    mock_logs = [
        {
            "id": "log-1",
            "timestamp": base_time,
            "service": "payment-service",
            "level": "INFO",
            "message": "Payment received",
            "environment": "staging",
            "trace_id": "tr-1",
            "metadata": {},
        },
        {
            "id": "log-2",
            "timestamp": base_time,
            "service": "payment-service",
            "level": "ERROR",
            "message": "QueuePool limit reached, connection pool exhausted",
            "environment": "staging",
            "trace_id": "tr-2",
            "metadata": {},
        },
    ]
    return create_logs_mcp_server(in_memory_logs=mock_logs)


@pytest.mark.anyio
async def test_logs_mcp_tools_list(test_server):
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    resp = await test_server.handle_jsonrpc(req)

    assert resp.error is None
    assert "tools" in resp.result
    tool_names = [t["name"] for t in resp.result["tools"]]
    assert len(tool_names) == 5
    assert "search_logs" in tool_names
    assert "get_service_logs" in tool_names
    assert "get_error_rate" in tool_names
    assert "get_correlated_errors" in tool_names
    assert "get_logs_around_event" in tool_names


@pytest.mark.anyio
async def test_logs_mcp_call_search_logs(test_server):
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_logs",
            "arguments": {"service": "payment-service", "level": "ERROR"},
        },
    }
    resp = await test_server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    assert len(resp.result["content"]) == 1


@pytest.mark.anyio
async def test_logs_mcp_call_get_service_logs(test_server):
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_service_logs",
            "arguments": {"service": "payment-service", "min_level": "INFO"},
        },
    }
    resp = await test_server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False


@pytest.mark.anyio
async def test_logs_mcp_call_get_error_rate(test_server):
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_error_rate",
            "arguments": {
                "service": "payment-service",
                "interval_seconds": 60,
                "window_minutes": 30,
                "end_time": "2026-10-10T12:05:00Z",
            },
        },
    }
    resp = await test_server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False


@pytest.mark.anyio
async def test_logs_mcp_call_get_correlated_errors(test_server):
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "get_correlated_errors",
            "arguments": {
                "service": "payment-service",
                "error_pattern": "connection pool exhausted",
                "window_seconds": 30,
            },
        },
    }
    resp = await test_server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False


@pytest.mark.anyio
async def test_logs_mcp_call_get_logs_around_event(test_server):
    req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "get_logs_around_event",
            "arguments": {
                "timestamp": "2026-10-10T12:00:00Z",
                "window_seconds": 60,
                "service": "payment-service",
            },
        },
    }
    resp = await test_server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False


@pytest.mark.anyio
async def test_logs_mcp_http_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Healthcheck
        h_resp = await client.get("/health")
        assert h_resp.status_code == 200
        h_data = h_resp.json()
        assert h_data["status"] == "healthy"
        assert h_data["registered_tools"] == 5

        # Tools list via GET /tools
        t_resp = await client.get("/tools")
        assert t_resp.status_code == 200
        assert len(t_resp.json()["tools"]) == 5

        # JSON-RPC via POST /mcp
        rpc_resp = await client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 100, "method": "tools/list"},
        )
        assert rpc_resp.status_code == 200
        rpc_data = rpc_resp.json()
        assert rpc_data["error"] is None
        assert len(rpc_data["result"]["tools"]) == 5

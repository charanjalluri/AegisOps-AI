"""
Unit tests for Database MCP Server JSON-RPC and HTTP API endpoints.
Verifies tool discovery, tool execution, mutation rejection, and HTTP routing.
"""

import httpx
import pytest
from httpx import ASGITransport

from apps.mcp_database.main import app
from apps.mcp_database.server import create_database_mcp_server


@pytest.mark.anyio
async def test_database_mcp_tools_list():
    server = create_database_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/list",
        "params": {},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    tools = resp.result["tools"]
    tool_names = [t["name"] for t in tools]
    assert len(tools) == 5
    assert "get_database_health" in tool_names
    assert "get_connection_pool" in tool_names
    assert "get_slow_queries" in tool_names
    assert "get_active_connections" in tool_names
    assert "run_readonly_query" in tool_names


@pytest.mark.anyio
async def test_database_mcp_call_health():
    server = create_database_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {"name": "get_database_health", "arguments": {}},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["database"] == "demo_payment_db"
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_database_mcp_call_connection_pool():
    server = create_database_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {"name": "get_connection_pool", "arguments": {}},
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["total_connections"] == 12
    assert data["pool_status"] == "healthy"


@pytest.mark.anyio
async def test_database_mcp_call_run_readonly_query_success():
    server = create_database_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {
            "name": "run_readonly_query",
            "arguments": {
                "query": "SELECT * FROM payments WHERE status = 'failed'",
                "row_limit": 5,
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["row_count"] > 0
    assert "id" in data["columns"]


@pytest.mark.anyio
async def test_database_mcp_call_run_readonly_query_mutation_rejection():
    server = create_database_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tools/call",
        "params": {
            "name": "run_readonly_query",
            "arguments": {
                "query": "DROP TABLE payments",
                "row_limit": 5,
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    # Mutation violation raises ValueError, captured in JSONRPCError with message
    assert resp.error is not None
    assert "DROP" in resp.error.message or "Prohibited" in resp.error.message


@pytest.mark.anyio
async def test_database_mcp_http_endpoints():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "healthy"
        assert r_health.json()["registered_tools"] == 5

        # Tools list
        r_tools = await client.get("/tools")
        assert r_tools.status_code == 200
        assert len(r_tools.json()["tools"]) == 5

        # POST /mcp JSON-RPC
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": "http-1",
            "method": "tools/call",
            "params": {"name": "get_database_health", "arguments": {}},
        }
        r_rpc = await client.post("/mcp", json=rpc_payload)
        assert r_rpc.status_code == 200
        resp_json = r_rpc.json()
        assert resp_json["id"] == "http-1"
        assert not resp_json["result"]["is_error"]

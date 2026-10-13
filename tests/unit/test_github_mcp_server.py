"""
Unit tests for GitHub MCP Server JSON-RPC and HTTP API endpoints.
Verifies tool discovery, tool execution, commit retrieval, error handling, and HTTP routing.
"""

import httpx
import pytest
from httpx import ASGITransport

from apps.mcp_github.main import app
from apps.mcp_github.server import create_github_mcp_server


@pytest.mark.anyio
async def test_github_mcp_tools_list():
    server = create_github_mcp_server()
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
    assert "get_recent_commits" in tool_names
    assert "get_commit" in tool_names
    assert "get_pull_requests" in tool_names
    assert "get_changed_files" in tool_names
    assert "get_deployment_history" in tool_names


@pytest.mark.anyio
async def test_github_mcp_call_recent_commits():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/call",
        "params": {
            "name": "get_recent_commits",
            "arguments": {"service": "payment-service", "limit": 5},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["count"] == 2
    assert data["commits"][0]["short_sha"] == "c0ffee1"


@pytest.mark.anyio
async def test_github_mcp_call_get_commit_success():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {
            "name": "get_commit",
            "arguments": {"service": "payment-service", "commit_sha": "c0ffee1"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["short_sha"] == "c0ffee1"
    assert "Temporary pool bypass" in data["diff"]


@pytest.mark.anyio
async def test_github_mcp_call_get_commit_not_found():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {
            "name": "get_commit",
            "arguments": {"service": "payment-service", "commit_sha": "unknown_sha_99"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is not None
    assert "not found in repository" in resp.error.message


@pytest.mark.anyio
async def test_github_mcp_call_pull_requests():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tools/call",
        "params": {
            "name": "get_pull_requests",
            "arguments": {"service": "payment-service", "state": "all"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    data = resp.result["content"][0]["data"]
    assert data["count"] == 2


@pytest.mark.anyio
async def test_github_mcp_call_changed_files():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "6",
        "method": "tools/call",
        "params": {
            "name": "get_changed_files",
            "arguments": {"service": "payment-service", "commit_sha_or_pr": "c0ffee1"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    data = resp.result["content"][0]["data"]
    assert data["count"] == 1
    assert data["files"][0]["filename"] == "apps/payment_service/database.py"


@pytest.mark.anyio
async def test_github_mcp_call_deployment_history():
    server = create_github_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "7",
        "method": "tools/call",
        "params": {
            "name": "get_deployment_history",
            "arguments": {"service": "payment-service"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    data = resp.result["content"][0]["data"]
    assert data["count"] == 2
    assert data["deployments"][0]["release_tag"] == "v2.8.1"


@pytest.mark.anyio
async def test_github_mcp_http_endpoints():
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
            "id": "http-gh-1",
            "method": "tools/call",
            "params": {"name": "get_deployment_history", "arguments": {"service": "payment-service"}},
        }
        r_rpc = await client.post("/mcp", json=rpc_payload)
        assert r_rpc.status_code == 200
        resp_json = r_rpc.json()
        assert resp_json["id"] == "http-gh-1"
        assert not resp_json["result"]["is_error"]

"""
AegisOps AI - Deployment & n8n MCP Integration Tests (MCP-06, MCP-07)
Exercises HTTP endpoints and tool chains against FastAPI applications.
"""

import pytest
import httpx

from apps.mcp_deployment.main import app as deployment_app
from apps.mcp_n8n.main import app as n8n_app


@pytest.mark.integration
@pytest.mark.anyio
async def test_deployment_mcp_http_endpoints():
    """Tests Deployment MCP HTTP endpoints /health and /mcp."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=deployment_app), base_url="http://test") as client:
        # 1. Health probe
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert health_data["server"] == "aegisops-deployment-mcp"

        # 2. List tools
        tools_resp = await client.get("/tools")
        assert tools_resp.status_code == 200
        assert len(tools_resp.json()["tools"]) >= 5

        # 3. JSON-RPC tools/call
        rpc_req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "get_current_version",
                "arguments": {"service": "payment-service"},
            },
        }
        rpc_resp = await client.post("/mcp", json=rpc_req)
        assert rpc_resp.status_code == 200
        data = rpc_resp.json()
        assert data.get("result") is not None


@pytest.mark.integration
@pytest.mark.anyio
async def test_n8n_mcp_http_endpoints():
    """Tests n8n MCP HTTP endpoints /health and /mcp."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=n8n_app), base_url="http://test") as client:
        # 1. Health probe
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert health_data["server"] == "aegisops-n8n-mcp"

        # 2. JSON-RPC tools/call with fallback
        rpc_req = {
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {
                "name": "execute_workflow",
                "arguments": {
                    "workflow_name": "incident-alert-slack",
                    "payload": {"message": "Test integration alert"},
                },
            },
        }
        rpc_resp = await client.post("/mcp", json=rpc_req)
        assert rpc_resp.status_code == 200
        data = rpc_resp.json()
        assert data.get("result") is not None
        assert data["result"]["content"][0]["data"]["status"] == "success"

"""
AegisOps AI - n8n MCP Server Unit Tests (MCP-07)
Validates JSON-RPC 2.0 dispatch for workflow execution and status introspection.
"""

import pytest

from apps.mcp_n8n.server import create_n8n_mcp_server
from apps.mcp_n8n.tools import N8nTools


@pytest.fixture
def server():
    tools = N8nTools(force_mock=True)
    return create_n8n_mcp_server(tools_instance=tools)


@pytest.mark.anyio
async def test_n8n_tools_list(server):
    """Verifies execute_workflow and get_execution_status are exposed in tools/list."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None

    tool_names = [t["name"] for t in resp.result["tools"]]
    assert "execute_workflow" in tool_names
    assert "get_execution_status" in tool_names


@pytest.mark.anyio
async def test_execute_workflow_jsonrpc(server):
    """Verifies execute_workflow dispatches via JSON-RPC 2.0."""
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "execute_workflow",
            "arguments": {
                "workflow_name": "incident-alert-slack",
                "payload": {"channel": "#incident-ops", "message": "Alert triggered"},
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    data = resp.result["content"][0]["data"]
    assert data["status"] == "success"
    assert data["workflow_name"] == "incident-alert-slack"
    assert data["is_mock"] is True


@pytest.mark.anyio
async def test_get_execution_status_jsonrpc(server):
    """Verifies get_execution_status queries via JSON-RPC 2.0."""
    # First trigger workflow via JSON-RPC
    trigger_req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "execute_workflow",
            "arguments": {
                "workflow_name": "test-flow",
                "payload": {},
            },
        },
    }
    trigger_resp = await server.handle_jsonrpc(trigger_req)
    assert trigger_resp.error is None
    exec_id = trigger_resp.result["content"][0]["data"]["execution_id"]

    # Now query status via JSON-RPC
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "get_execution_status",
            "arguments": {"execution_id": exec_id},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    data = resp.result["content"][0]["data"]
    assert data["execution_id"] == exec_id
    assert data["status"] == "success"

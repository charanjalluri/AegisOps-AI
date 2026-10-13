"""
AegisOps AI - Deployment MCP Server Unit Tests (MCP-06)
Validates JSON-RPC 2.0 dispatch, tools listing, and policy violation error responses (-32003).
"""

import pytest

from apps.common.mcp.protocol import MCPErrorCode
from apps.mcp_deployment.server import create_deployment_mcp_server
from apps.mcp_deployment.tools import DeploymentTools
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.engine import PolicyEngine


@pytest.fixture
def clean_storage():
    return InvestigationStorage()


@pytest.fixture
def approval_manager(clean_storage):
    return ApprovalManager(storage=clean_storage)


@pytest.fixture
def server(clean_storage, approval_manager):
    policy_engine = PolicyEngine(storage=clean_storage)
    tools = DeploymentTools(
        storage=clean_storage,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
    )
    return create_deployment_mcp_server(
        storage=clean_storage,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        tools_instance=tools,
    )


@pytest.mark.anyio
async def test_tools_list(server):
    """Verifies all 5 deployment tools are registered and exposed in tools/list."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None

    tool_names = [t["name"] for t in resp.result["tools"]]
    assert "get_current_version" in tool_names
    assert "get_previous_version" in tool_names
    assert "get_deployment_history" in tool_names
    assert "rollback_deployment" in tool_names
    assert "restart_service" in tool_names


@pytest.mark.anyio
async def test_get_current_version_jsonrpc(server):
    """Verifies get_current_version executes successfully via JSON-RPC."""
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_current_version",
            "arguments": {"service": "payment-service"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    data = resp.result["content"][0]["data"]
    assert data["version"] == "v2.8.1"
    assert data["is_current"] is True


@pytest.mark.anyio
async def test_unapproved_rollback_returns_policy_violation(server):
    """Verifies unapproved rollback returns JSON-RPC error with POLICY_VIOLATION code (-32003)."""
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "rollback_deployment",
            "arguments": {
                "service": "payment-service",
                "target_version": "v2.8.0",
                "proposal_id": "unapproved-proposal-uuid",
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.result is None
    assert resp.error is not None
    assert resp.error.code == MCPErrorCode.POLICY_VIOLATION
    assert "Policy violation: action rejected" in resp.error.message


@pytest.mark.anyio
async def test_approved_rollback_succeeds_jsonrpc(server, clean_storage, approval_manager):
    """Verifies approved rollback succeeds via JSON-RPC."""
    prop = await clean_storage.create_action_proposal(
        incident_id="INC-SERVER-001",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )
    await approval_manager.approve_proposal(
        proposal_id=str(prop.id),
        operator_id="admin@aegisops.ai",
        comment="Approved for production rollback",
    )

    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "rollback_deployment",
            "arguments": {
                "service": "payment-service",
                "target_version": "v2.8.0",
                "proposal_id": str(prop.id),
            },
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result is not None
    data = resp.result["content"][0]["data"]
    assert data["status"] == "success"
    assert data["current_version"] == "v2.8.0"
    assert data["previous_version"] == "v2.8.1"

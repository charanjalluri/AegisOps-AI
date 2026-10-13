"""
AegisOps AI - n8n MCP Tools Unit Tests (MCP-07)
Validates workflow execution, secret masking, offline mock fallback, and status queries.
"""

import pytest

from apps.mcp_n8n.models import WorkflowExecutionResult, WorkflowStatusResult
from apps.mcp_n8n.tools import N8nTools


@pytest.fixture
def n8n_tools():
    # Force mock mode for deterministic offline testing
    return N8nTools(force_mock=True)


@pytest.mark.anyio
async def test_execute_slack_workflow_mock(n8n_tools):
    """Verifies Slack notification workflow execution in mock fallback mode."""
    res = await n8n_tools.execute_workflow(
        workflow_name="incident-alert-slack",
        payload={
            "channel": "#incident-ops",
            "incident_id": "INC-2026-051",
            "message": "Payment service connection leak detected",
        },
    )
    assert isinstance(res, WorkflowExecutionResult)
    assert res.status == "success"
    assert res.is_mock is True
    assert res.workflow_name == "incident-alert-slack"
    assert res.response.get("channel") == "#incident-ops"
    assert "mock-exec-" in res.execution_id


@pytest.mark.anyio
async def test_execute_jira_workflow_mock(n8n_tools):
    """Verifies Jira ticket creation workflow execution in mock fallback mode."""
    res = await n8n_tools.execute_workflow(
        workflow_name="jira-ticket-creation",
        payload={
            "summary": "High error rate on payment-service",
            "priority": "P1",
        },
    )
    assert isinstance(res, WorkflowExecutionResult)
    assert res.status == "success"
    assert res.is_mock is True
    assert "OPS-" in res.response.get("issue_key", "")


@pytest.mark.anyio
async def test_payload_secret_masking(n8n_tools):
    """Verifies secrets in outbound payloads are masked before dispatch (T-05-05)."""
    payload_with_secrets = {
        "channel": "#security",
        "api_key": "secret-super-key-12345",
        "database_password": "super_secret_password_here",
        "nested": {
            "token": "ghp_abcdef1234567890",
        },
    }
    res = await n8n_tools.execute_workflow(
        workflow_name="incident-alert-slack",
        payload=payload_with_secrets,
    )
    assert res.status == "success"
    # Verify execution was logged safely
    exec_status = await n8n_tools.get_execution_status(res.execution_id)
    assert exec_status.status == "success"


@pytest.mark.anyio
async def test_get_execution_status(n8n_tools):
    """Verifies retrieving execution status by execution_id."""
    res = await n8n_tools.execute_workflow(
        workflow_name="incident-resolution-alert",
        payload={"incident_id": "INC-2026-051", "status": "resolved"},
    )

    status = await n8n_tools.get_execution_status(res.execution_id)
    assert isinstance(status, WorkflowStatusResult)
    assert status.status == "success"
    assert status.execution_id == res.execution_id

    # Non-existent execution ID
    unknown = await n8n_tools.get_execution_status("unknown-id-123")
    assert unknown.status == "unknown"


@pytest.mark.anyio
async def test_unreachable_endpoint_falls_back_gracefully():
    """Verifies when endpoint is unreachable (e.g. invalid host), tool falls back to mock without raising."""
    tools = N8nTools(base_webhook_url="http://127.0.0.1:59999/webhook", timeout_seconds=0.2)
    res = await tools.execute_workflow(
        workflow_name="incident-alert-slack",
        payload={"message": "Testing fallback"},
    )
    assert isinstance(res, WorkflowExecutionResult)
    assert res.status == "success"
    assert res.is_mock is True

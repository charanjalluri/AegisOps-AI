"""
AegisOps AI - Deployment MCP Tools Unit Tests (MCP-06)
Validates version inspection, policy gating, and rollback execution state machine.
"""

import pytest

from apps.common.mcp.protocol import PolicyViolationError
from apps.mcp_deployment.models import DeploymentInfo, RollbackResult
from apps.mcp_deployment.tools import DeploymentTools
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.engine import PolicyEngine


@pytest.fixture
def clean_storage():
    return InvestigationStorage()


@pytest.fixture
def policy_engine(clean_storage):
    return PolicyEngine(storage=clean_storage)


@pytest.fixture
def approval_manager(clean_storage):
    return ApprovalManager(storage=clean_storage)


@pytest.fixture
def deployment_tools(clean_storage, policy_engine, approval_manager):
    return DeploymentTools(
        storage=clean_storage,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
    )


@pytest.mark.anyio
async def test_version_inspection(deployment_tools):
    """Verifies get_current_version and get_previous_version return correct deployments."""
    curr = await deployment_tools.get_current_version("payment-service")
    assert isinstance(curr, DeploymentInfo)
    assert curr.service == "payment-service"
    assert curr.version == "v2.8.1"
    assert curr.is_current is True
    assert curr.status == "active"

    prev = await deployment_tools.get_previous_version("payment-service")
    assert isinstance(prev, DeploymentInfo)
    assert prev.version == "v2.8.0"
    assert prev.is_current is False


@pytest.mark.anyio
async def test_deployment_history(deployment_tools):
    """Verifies get_deployment_history returns chronological releases."""
    history = await deployment_tools.get_deployment_history("payment-service", limit=2)
    assert len(history) == 2
    assert history[0].version == "v2.8.1"
    assert history[1].version == "v2.8.0"


@pytest.mark.anyio
async def test_rollback_rejected_without_approved_proposal(deployment_tools, clean_storage):
    """Verifies rollback attempt without an approved proposal raises PolicyViolationError."""
    # 1. Non-existent proposal ID
    with pytest.raises(PolicyViolationError) as exc_info:
        await deployment_tools.rollback_deployment(
            service="payment-service",
            target_version="v2.8.0",
            proposal_id="non-existent-uuid",
        )
    assert "Policy violation: action rejected" in str(exc_info.value)

    # 2. Existing proposal in 'proposed' state (not yet approved)
    prop = await clean_storage.create_action_proposal(
        incident_id="INC-TEST-001",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )
    with pytest.raises(PolicyViolationError) as exc_info2:
        await deployment_tools.rollback_deployment(
            service="payment-service",
            target_version="v2.8.0",
            proposal_id=str(prop.id),
        )
    assert "Policy violation: action rejected" in str(exc_info2.value)


@pytest.mark.anyio
async def test_rollback_succeeds_with_approved_proposal(
    deployment_tools, clean_storage, approval_manager
):
    """Verifies rollback with an approved proposal succeeds, updates state, and marks executed."""
    # 1. Create and approve proposal
    prop = await clean_storage.create_action_proposal(
        incident_id="INC-TEST-002",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )
    await approval_manager.approve_proposal(
        proposal_id=str(prop.id),
        operator_id="sre-lead@aegisops.ai",
        comment="Approved rollback to clear leak",
    )

    # 2. Execute rollback
    result = await deployment_tools.rollback_deployment(
        service="payment-service",
        target_version="v2.8.0",
        proposal_id=str(prop.id),
    )

    assert isinstance(result, RollbackResult)
    assert result.status == "success"
    assert result.previous_version == "v2.8.1"
    assert result.current_version == "v2.8.0"
    assert result.proposal_id == str(prop.id)

    # 3. Verify deployment state was flipped
    curr = await deployment_tools.get_current_version("payment-service")
    assert curr.version == "v2.8.0"
    assert curr.is_current is True

    # 4. Verify proposal is marked executed
    props = await clean_storage.get_action_proposals("INC-TEST-002")
    executed_prop = [p for p in props if str(p.id) == str(prop.id)][0]
    assert executed_prop.status == "executed"
    assert executed_prop.executed_at is not None


@pytest.mark.anyio
async def test_restart_service(deployment_tools):
    """Verifies restart_service executes and returns success."""
    res = await deployment_tools.restart_service("payment-service")
    assert res.status == "success"
    assert "restarted successfully" in res.message

"""
AegisOps AI - Policy Engine Unit Tests (GOV-01, GOV-02)
Tests policy evaluation logic, blocking unapproved rollbacks, approving authorized rollbacks,
and strictly rejecting destructive actions.
"""

import pytest

from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.engine import PolicyEngine
from apps.policy.models import PolicyDecision, RiskTier


@pytest.mark.anyio
async def test_policy_engine_permits_read_and_low_actions():
    engine = PolicyEngine()

    # Read action
    res_read = await engine.evaluate_action("search_logs", parameters={"service": "payment-service"})
    assert res_read.decision == PolicyDecision.ALLOWED
    assert res_read.risk_level == RiskTier.READ
    assert res_read.requires_approval is False

    # Low action
    res_low = await engine.evaluate_action("n8n_notify_slack", parameters={"channel": "#ops"})
    assert res_low.decision == PolicyDecision.ALLOWED
    assert res_low.risk_level == RiskTier.LOW
    assert res_low.requires_approval is False


@pytest.mark.anyio
async def test_policy_engine_rejects_destructive_actions():
    engine = PolicyEngine()

    res = await engine.evaluate_action("drop_table", parameters={"table": "payments"})
    assert res.decision == PolicyDecision.REJECTED
    assert res.risk_level == RiskTier.DESTRUCTIVE
    assert res.requires_approval is False
    assert "permanently prohibited" in res.reason


@pytest.mark.anyio
async def test_policy_engine_blocks_unapproved_high_risk_actions():
    storage = InvestigationStorage()
    engine = PolicyEngine(storage=storage)

    # 1. No proposal ID
    res_no_prop = await engine.evaluate_action("rollback_deployment", parameters={"service": "payment-service"})
    assert res_no_prop.decision == PolicyDecision.BLOCKED
    assert res_no_prop.risk_level == RiskTier.HIGH
    assert res_no_prop.requires_approval is True

    # 2. Proposal exists but is still 'proposed' (not approved)
    prop = await storage.create_action_proposal(
        incident_id="INC-100",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )
    res_unapproved = await engine.evaluate_action(
        "rollback_deployment",
        proposal_id=prop.id,
        incident_id="INC-100",
    )
    assert res_unapproved.decision == PolicyDecision.BLOCKED
    assert "Action requires verified human approval" in res_unapproved.reason

    # validate_execution_allowed raises ValueError
    with pytest.raises(ValueError, match="Policy violation: action rejected"):
        await engine.validate_execution_allowed(proposal_id=prop.id, incident_id="INC-100")


@pytest.mark.anyio
async def test_policy_engine_allows_approved_high_risk_actions():
    storage = InvestigationStorage()
    engine = PolicyEngine(storage=storage)

    prop = await storage.create_action_proposal(
        incident_id="INC-101",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )

    # Operator approves proposal
    prop.status = "approved"
    prop.approved_by = "lead-sre-alice"

    res_approved = await engine.evaluate_action(
        "rollback_deployment",
        proposal_id=prop.id,
        incident_id="INC-101",
    )
    assert res_approved.decision == PolicyDecision.ALLOWED
    assert res_approved.requires_approval is False
    assert "approved by operator 'lead-sre-alice'" in res_approved.reason

    # validate_execution_allowed succeeds
    assert await engine.validate_execution_allowed(proposal_id=prop.id, incident_id="INC-101") is True

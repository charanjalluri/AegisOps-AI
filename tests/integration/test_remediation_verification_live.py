"""
AegisOps AI - Remediation Verification Live Integration Tests (GOV-03)
Tests closed-loop remediation verification against real/simulated components.
"""

import pytest

from apps.mcp_deployment.tools import DeploymentTools
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.audit import GovernanceAuditLogger
from apps.policy.engine import PolicyEngine
from apps.verification.closure import IncidentClosurePipeline
from apps.verification.models import MetricCondition, VerificationTarget
from apps.verification.verifier import RemediationVerifier


@pytest.mark.integration
@pytest.mark.anyio
async def test_end_to_end_rollback_verification_closure():
    """Validates full flow: rollback executed -> metrics verified -> incident closed."""
    storage = InvestigationStorage()
    audit_logger = GovernanceAuditLogger(storage=storage)
    approval_manager = ApprovalManager(storage=storage, audit_logger=audit_logger)
    policy_engine = PolicyEngine(storage=storage)

    deployment_tools = DeploymentTools(
        storage=storage,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
    )

    # 1. Create incident and proposal
    incident_id = "INC-INTEG-001"
    inc = await storage.create_incident(
        incident_id=incident_id,
        title="Live Integration Outage",
        service="payment-service",
        severity="CRITICAL",
    )
    prop = await storage.create_action_proposal(
        incident_id=inc.incident_id,
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )

    # 2. Approve and execute rollback
    await approval_manager.approve_proposal(str(prop.id), operator_id="sre-integration@aegisops.ai")
    rollback_res = await deployment_tools.rollback_deployment(
        service="payment-service",
        target_version="v2.8.0",
        proposal_id=str(prop.id),
    )
    assert rollback_res.status == "success"

    # 3. Verification & closure pipeline
    def telemetry_collector(service: str, metric_name: str) -> float:
        if metric_name == "error_rate":
            return 0.001
        if metric_name == "active_connections":
            return 2.0
        return 0.0

    verifier = RemediationVerifier(metric_collector=telemetry_collector)
    pipeline = IncidentClosurePipeline(
        verifier=verifier,
        storage=storage,
        approval_manager=approval_manager,
        audit_logger=audit_logger,
    )

    target = VerificationTarget(
        service="payment-service",
        conditions=[
            MetricCondition(metric_name="error_rate", operator="<", threshold=0.01),
            MetricCondition(metric_name="active_connections", operator="<", threshold=15.0),
        ],
        min_consecutive_successes=2,
        poll_interval_sec=0.01,
        timeout_sec=1.0,
    )

    closure_res = await pipeline.execute_verification_and_close(
        incident_id=inc.incident_id,
        proposal_id=str(prop.id),
        root_cause="Bad release v2.8.1 leak",
        target=target,
    )

    assert closure_res.status == "resolved"
    stored_inc = await storage.get_incident(inc.incident_id)
    assert stored_inc.status == "resolved"

"""
AegisOps AI - Incident Closure Pipeline Unit Tests (GOV-03, GOV-04)
Validates verified incident closure, proposal state transitions, audit trail durability,
n8n notification dispatch, and escalation on failed verifications.
"""

import pytest

from apps.mcp_incident.storage import InvestigationStorage
from apps.mcp_n8n.tools import N8nTools
from apps.policy.approval import ApprovalManager
from apps.policy.audit import GovernanceAuditLogger
from apps.verification.closure import IncidentClosurePipeline
from apps.verification.models import MetricCondition, VerificationTarget
from apps.verification.verifier import RemediationVerifier


@pytest.fixture
def clean_storage():
    return InvestigationStorage()


@pytest.fixture
def audit_logger(clean_storage):
    return GovernanceAuditLogger(storage=clean_storage)


@pytest.mark.anyio
async def test_closure_pipeline_happy_path(clean_storage, audit_logger):
    """Verifies complete end-to-end verified closure flow."""
    # 1. Setup incident, hypothesis, and proposal in storage
    incident_id = "INC-2026-051"
    inc = await clean_storage.create_incident(
        incident_id=incident_id,
        title="Payment Service DB Connection Exhaustion",
        service="payment-service",
        severity="CRITICAL",
        summary="Service experiencing 500 errors due to connection leak",
    )

    hypo = await clean_storage.add_or_update_hypothesis(
        incident_id=incident_id,
        title="Connection leak introduced in v2.8.1",
        confidence_score=0.92,
    )

    prop = await clean_storage.create_action_proposal(
        incident_id=incident_id,
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )

    # Operator approves proposal
    approval_manager = ApprovalManager(storage=clean_storage, audit_logger=audit_logger)
    await approval_manager.approve_proposal(str(prop.id), operator_id="lead-sre@aegisops.ai")
    await approval_manager.mark_proposal_executed(str(prop.id))

    # 2. Setup mock verifier that returns healthy metrics
    def healthy_collector(service: str, metric_name: str) -> float:
        if metric_name == "error_rate":
            return 0.002
        if metric_name == "active_connections":
            return 3.0
        return 0.0

    verifier = RemediationVerifier(metric_collector=healthy_collector)
    n8n_tools = N8nTools(force_mock=True)

    emitted_events = []
    async def mock_emitter(topic, payload):
        emitted_events.append((topic, payload))

    pipeline = IncidentClosurePipeline(
        verifier=verifier,
        storage=clean_storage,
        approval_manager=approval_manager,
        audit_logger=audit_logger,
        n8n_tools=n8n_tools,
        event_emitter=mock_emitter,
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

    # 3. Execute verification and closure
    result = await pipeline.execute_verification_and_close(
        incident_id=incident_id,
        proposal_id=str(prop.id),
        root_cause="Connection leak in unclosed cursor in v2.8.1 release",
        winning_hypothesis_id=str(hypo.id),
        target=target,
    )

    # 4. Verify outcomes
    assert result.status == "resolved"
    assert result.incident_id == incident_id
    assert result.winning_hypothesis_id == str(hypo.id)
    assert result.audit_id is not None

    # Proposal state is verified
    proposals = await clean_storage.get_action_proposals(incident_id)
    verified_prop = [p for p in proposals if str(p.id) == str(prop.id)][0]
    assert verified_prop.status == "verified"

    # Incident state is resolved
    stored_inc = await clean_storage.get_incident(incident_id)
    assert stored_inc.status == "resolved"
    assert stored_inc.resolved_at is not None

    # Hypothesis is validated
    hypotheses = await clean_storage.get_hypotheses(incident_id)
    validated_hypo = [h for h in hypotheses if str(h.id) == str(hypo.id)][0]
    assert validated_hypo.status == "validated"
    assert validated_hypo.confidence_score == 1.0

    # Audit entry is durably recorded
    audit_history = audit_logger.get_entries(incident_id=incident_id)
    resolved_audits = [a for a in audit_history if a.event_type == "INCIDENT_CLOSED_VERIFIED"]
    assert len(resolved_audits) == 1

    # Kafka event was emitted
    resolved_kafka = [e for e in emitted_events if e[0] == "incidents.updated" and e[1]["status"] == "resolved"]
    assert len(resolved_kafka) == 1

    # n8n resolution alert was executed
    assert len(n8n_tools.executions) >= 1


@pytest.mark.anyio
async def test_closure_pipeline_failed_verification(clean_storage, audit_logger):
    """Verifies that failed verification loop escalates incident and marks proposal failed."""
    # 1. Setup incident and proposal
    incident_id = "INC-FAIL-001"
    inc = await clean_storage.create_incident(
        incident_id=incident_id,
        title="Unresolved Incident",
        service="payment-service",
        severity="HIGH",
    )

    prop = await clean_storage.create_action_proposal(
        incident_id=incident_id,
        action_type="rollback_deployment",
        parameters={"service": "payment-service"},
    )
    approval_manager = ApprovalManager(storage=clean_storage, audit_logger=audit_logger)
    await approval_manager.approve_proposal(str(prop.id), operator_id="admin@aegisops.ai")
    await approval_manager.mark_proposal_executed(str(prop.id))

    # Collector returning degraded metrics
    def degraded_collector(service: str, metric_name: str) -> float:
        return 0.05  # 5% error rate (>1%)

    verifier = RemediationVerifier(metric_collector=degraded_collector)
    n8n_tools = N8nTools(force_mock=True)

    emitted_events = []
    async def mock_emitter(topic, payload):
        emitted_events.append((topic, payload))

    pipeline = IncidentClosurePipeline(
        verifier=verifier,
        storage=clean_storage,
        approval_manager=approval_manager,
        audit_logger=audit_logger,
        n8n_tools=n8n_tools,
        event_emitter=mock_emitter,
    )

    target = VerificationTarget(
        service="payment-service",
        conditions=[MetricCondition(metric_name="error_rate", operator="<", threshold=0.01)],
        min_consecutive_successes=2,
        poll_interval_sec=0.01,
        timeout_sec=0.05,
    )

    # 2. Execute verification and closure
    result = await pipeline.execute_verification_and_close(
        incident_id=incident_id,
        proposal_id=str(prop.id),
        root_cause="Unknown",
        target=target,
    )

    # 3. Verify escalation outcomes
    assert result.status == "escalated"

    # Proposal state is failed
    proposals = await clean_storage.get_action_proposals(incident_id)
    failed_prop = [p for p in proposals if str(p.id) == str(prop.id)][0]
    assert failed_prop.status == "failed"

    # Incident state is escalated
    stored_inc = await clean_storage.get_incident(incident_id)
    assert stored_inc.status == "escalated"

    # Audit entry is durably recorded
    audit_history = audit_logger.get_entries(incident_id=incident_id)
    failed_audits = [a for a in audit_history if a.event_type == "REMEDIATION_VERIFICATION_FAILED"]
    assert len(failed_audits) == 1

    # Kafka escalation event emitted
    escalated_kafka = [e for e in emitted_events if e[0] == "incidents.updated" and e[1]["status"] == "escalated"]
    assert len(escalated_kafka) == 1

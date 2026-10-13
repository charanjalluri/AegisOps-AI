"""
AegisOps AI - Human-in-the-Loop Approval & Governance Audit Tests (GOV-02, GOV-04)
Tests operator authorization, approve/reject state transitions, rejection reasons,
audit trail integrity, and Kafka event broadcasts.
"""

import pytest

from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.audit import GovernanceAuditLogger
from apps.policy.models import RiskTier


@pytest.mark.anyio
async def test_hitl_approval_successful_flow():
    storage = InvestigationStorage()
    audit = GovernanceAuditLogger(storage=storage)
    events = []

    async def mock_emitter(topic, payload):
        events.append((topic, payload))

    manager = ApprovalManager(storage=storage, audit_logger=audit, event_emitter=mock_emitter)

    # 1. Proposal created by agent
    prop = await storage.create_action_proposal(
        incident_id="INC-301",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
        rationale="Eliminate connection leak from v2.8.1",
    )
    assert prop.status == "proposed"
    assert prop.approved_by is None

    # 2. Check pending list
    pending = await manager.list_pending_proposals("INC-301")
    assert len(pending) == 1
    assert pending[0].id == prop.id

    # 3. Operator approves proposal
    approved_prop = await manager.approve_proposal(
        proposal_id=prop.id,
        operator_id="sre-lead-bob",
        comment="Authorized emergency rollback after team review",
        incident_id="INC-301",
    )
    assert approved_prop.status == "approved"
    assert approved_prop.approved_by == "sre-lead-bob"

    # 4. Pending list is now empty
    pending_after = await manager.list_pending_proposals("INC-301")
    assert len(pending_after) == 0

    # 5. Kafka event emitted
    assert len(events) == 1
    assert events[0][0] == "ai.actions"
    assert events[0][1]["status"] == "approved"
    assert events[0][1]["operator_id"] == "sre-lead-bob"

    # 6. Audit entry recorded
    audit_entries = audit.get_entries(proposal_id=prop.id)
    assert len(audit_entries) == 1
    assert audit_entries[0].event_type == "PROPOSAL_APPROVED"
    assert audit_entries[0].operator_id == "sre-lead-bob"


@pytest.mark.anyio
async def test_hitl_rejection_flow():
    storage = InvestigationStorage()
    audit = GovernanceAuditLogger(storage=storage)
    events = []

    async def mock_emitter(topic, payload):
        events.append((topic, payload))

    manager = ApprovalManager(storage=storage, audit_logger=audit, event_emitter=mock_emitter)

    prop = await storage.create_action_proposal(
        incident_id="INC-302",
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
    )

    # Operator rejects proposal
    rejected_prop = await manager.reject_proposal(
        proposal_id=prop.id,
        operator_id="eng-manager-carol",
        reason="Scheduled maintenance window already active; manual fix in progress.",
        incident_id="INC-302",
    )
    assert rejected_prop.status == "rejected"

    # Cannot re-approve rejected proposal
    with pytest.raises(ValueError, match="Cannot approve proposal"):
        await manager.approve_proposal(
            proposal_id=prop.id,
            operator_id="sre-lead-bob",
            incident_id="INC-302",
        )

    # Event emitted
    assert len(events) == 1
    assert events[0][1]["status"] == "rejected"
    assert events[0][1]["operator_id"] == "eng-manager-carol"

    # Audit recorded
    entries = audit.get_entries(proposal_id=prop.id)
    assert len(entries) == 1
    assert entries[0].event_type == "PROPOSAL_REJECTED"


@pytest.mark.anyio
async def test_hitl_mandates_operator_id():
    storage = InvestigationStorage()
    manager = ApprovalManager(storage=storage)

    prop = await storage.create_action_proposal(
        incident_id="INC-303",
        action_type="rollback_deployment",
        parameters={},
        risk_level="HIGH",
    )

    # Empty operator ID rejected
    with pytest.raises(ValueError, match="Operator ID must be a non-empty string"):
        await manager.approve_proposal(proposal_id=prop.id, operator_id="", incident_id="INC-303")

    with pytest.raises(ValueError, match="Operator ID must be a non-empty string"):
        await manager.approve_proposal(proposal_id=prop.id, operator_id="   ", incident_id="INC-303")

"""
AegisOps AI - RCA Synthesis Unit Tests (REASON-05)
Tests Root Cause Analysis synthesis, action proposal creation, and Kafka broadcasting.
"""

import pytest

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.reasoning.hypotheses import EvaluatedHypothesis, HypothesisStatus
from apps.agent.reasoning.rca import RCAReport, RCASynthesizer
from apps.common.schemas.events import IncidentEvent, IncidentSeverity, IncidentStatus
from apps.mcp_incident.storage import InvestigationStorage


@pytest.mark.anyio
async def test_rca_synthesis_model_and_content():
    incident = IncidentEvent(
        incident_id="INC-RCA-001",
        title="Payment Service Connection Timeout",
        service="payment-service",
        severity=IncidentSeverity.SEV1,
        status=IncidentStatus.INVESTIGATING,
        summary="Error rate 32%",
    )

    winning_hypo = EvaluatedHypothesis(
        title="H1: Database Connection Pool Exhaustion (Code Release / Leak)",
        status=HypothesisStatus.VALIDATED,
        prior_probability=0.40,
        confidence_score=0.92,
        source_tools_used=["mcp_database", "mcp_github"],
    )

    all_hypos = [
        winning_hypo,
        EvaluatedHypothesis(
            title="H2: Infrastructure Degradation",
            status=HypothesisStatus.REFUTED,
            prior_probability=0.25,
            confidence_score=0.04,
        ),
    ]

    ev_db = CanonicalEvidence(
        incident_id=incident.incident_id,
        source_tool="mcp_database",
        signal_type="pool_exhaustion",
        confidence_weight=0.95,
        fact_statement="Active connections reached 50/50 capacity",
    )
    ev_git = CanonicalEvidence(
        incident_id=incident.incident_id,
        source_tool="mcp_github",
        signal_type="code_diff_leak",
        confidence_weight=0.90,
        fact_statement="Commit 8f9b2d1 omitted connection close statement",
    )

    tool_history = [
        {"tool_name": "get_connection_pool", "duration_ms": 45.0},
        {"tool_name": "get_commit", "duration_ms": 62.0},
    ]

    rca = RCASynthesizer.synthesize(
        incident=incident,
        winning_hypothesis=winning_hypo,
        hypotheses=all_hypos,
        evidence_history=[ev_db, ev_git],
        tool_history=tool_history,
    )

    assert rca.incident_id == incident.incident_id
    assert rca.service == "payment-service"
    assert rca.primary_root_cause == winning_hypo.title
    assert rca.confidence_score == 0.92
    assert len(rca.key_evidence) == 2
    assert len(rca.timeline) >= 4
    assert rca.recommended_remediation["action_type"] == "rollback_deployment"
    assert rca.recommended_remediation["risk_level"] == "HIGH"
    assert len(rca.preventative_actions) >= 3


@pytest.mark.anyio
async def test_rca_persist_and_publish():
    incident = IncidentEvent(
        incident_id="INC-RCA-002",
        title="Payment Service DB Outage",
        service="payment-service",
        severity=IncidentSeverity.SEV1,
        status=IncidentStatus.INVESTIGATING,
        summary="Active outage",
    )

    storage = InvestigationStorage()
    await storage.create_incident(
        incident_id=incident.incident_id,
        title=incident.title,
        service=incident.service,
        severity="SEV-1",
    )

    winning_hypo = EvaluatedHypothesis(
        title="Database Connection Pool Leak",
        confidence_score=0.91,
    )

    rca = RCASynthesizer.synthesize(
        incident=incident,
        winning_hypothesis=winning_hypo,
        hypotheses=[winning_hypo],
        evidence_history=[],
        tool_history=[],
    )

    events_emitted = []
    async def mock_emitter(topic, payload):
        events_emitted.append((topic, payload))

    persisted = await RCASynthesizer.persist_and_publish(
        rca=rca,
        storage=storage,
        event_emitter=mock_emitter,
    )

    # 1. Action proposal ID populated
    assert persisted.action_proposal_id is not None

    # 2. Storage action proposal created
    proposals = await storage.get_action_proposals(incident.incident_id)
    assert len(proposals) == 1
    assert proposals[0].id == persisted.action_proposal_id
    assert proposals[0].action_type == "rollback_deployment"
    assert proposals[0].risk_level == "HIGH"

    # 3. Incident status transitioned to 'mitigating'
    inc = await storage.get_incident(incident.incident_id)
    assert inc.status == "mitigating"

    # 4. Kafka event emitted on ai.analysis
    assert len(events_emitted) == 1
    assert events_emitted[0][0] == "ai.analysis"
    assert events_emitted[0][1]["action_proposal_id"] == persisted.action_proposal_id

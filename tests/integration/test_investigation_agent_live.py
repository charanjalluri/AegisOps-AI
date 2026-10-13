"""
AegisOps AI - Live Investigation Agent Integration Tests
Requires live Docker infrastructure (Kafka, PostgreSQL, Qdrant).
"""

import pytest

from apps.agent.orchestration.graph import InvestigationGraph
from apps.common.schemas.events import IncidentEvent, IncidentSeverity, IncidentStatus


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_investigation_agent_flow():
    # Stubs integration execution against live containers
    incident = IncidentEvent(
        incident_id="INT-INC-001",
        title="Live Docker Integration Verification Incident",
        service="payment-service",
        severity=IncidentSeverity.SEV2,
        status=IncidentStatus.INVESTIGATING,
        summary="Testing end-to-end investigation state machine against live containers.",
    )

    graph = InvestigationGraph()
    state = await graph.run(incident)
    assert state.status == "COMPLETE"
    assert state.rca_report is not None

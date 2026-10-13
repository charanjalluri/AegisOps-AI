"""
AegisOps AI - Investigation State Machine Unit Tests (REASON-02)
Tests full cyclic investigation state transitions, multi-tool evidence convergence,
and graceful termination under budget constraints.
"""

import pytest

from apps.agent.orchestration.budget import InvestigationBudget
from apps.agent.orchestration.graph import InvestigationGraph
from apps.common.schemas.events import IncidentEvent, IncidentSeverity, IncidentStatus
from apps.mcp_incident.storage import InvestigationStorage


@pytest.mark.anyio
async def test_investigation_graph_full_cycle_convergence():
    incident = IncidentEvent(
        incident_id="INC-TEST-099",
        title="Payment Service DB Pool Saturation",
        service="payment-service",
        severity=IncidentSeverity.SEV1,
        status=IncidentStatus.INVESTIGATING,
        summary="Error rate 28% with connection acquisition timeouts.",
    )

    storage = InvestigationStorage()
    await storage.create_incident(
        incident_id=incident.incident_id,
        title=incident.title,
        service=incident.service,
        severity="SEV-1",
        summary=incident.summary,
    )

    events_emitted = []
    async def mock_emitter(topic, payload):
        events_emitted.append((topic, payload))

    graph = InvestigationGraph(
        storage=storage,
        event_emitter=mock_emitter,
    )

    final_state = await graph.run(incident)

    # 1. Verification of lifecycle completion
    assert final_state.status == "COMPLETE"
    assert final_state.step_count >= 2
    assert len(final_state.tool_history) >= 3
    assert len(final_state.evidence) >= 3

    # 2. Winning hypothesis converged with corroborating evidence
    winning = final_state.winning_hypothesis
    assert winning is not None
    assert "Connection Pool" in winning.title
    assert winning.confidence_score >= 0.85
    assert len(winning.source_tools_used) >= 2

    # 3. RCA report produced
    assert final_state.rca_report is not None
    rca = final_state.rca_report
    assert rca["primary_root_cause"] == winning.title
    assert rca["confidence_score"] >= 0.85
    assert rca["recommended_remediation"]["action_type"] == "rollback_deployment"
    assert rca["action_proposal_id"] is not None

    # 4. Storage updated
    stored_proposals = await storage.get_action_proposals(incident.incident_id)
    assert len(stored_proposals) == 1
    assert stored_proposals[0].action_type == "rollback_deployment"

    stored_inc = await storage.get_incident(incident.incident_id)
    assert stored_inc.status == "mitigating"

    # 5. Kafka event broadcast
    assert len(events_emitted) == 1
    assert events_emitted[0][0] == "ai.analysis"
    assert events_emitted[0][1]["incident_id"] == incident.incident_id


@pytest.mark.anyio
async def test_investigation_graph_budget_exhaustion_graceful_termination():
    incident = IncidentEvent(
        incident_id="INC-BUDGET-001",
        title="High Latency Warning",
        service="payment-service",
        severity=IncidentSeverity.SEV3,
        status=IncidentStatus.INVESTIGATING,
        summary="Minor latency fluctuations.",
    )

    # Restrict budget to only 1 tool call
    budget = InvestigationBudget(max_tool_calls=1)
    graph = InvestigationGraph(budget=budget)

    final_state = await graph.run(incident)

    # Must terminate cleanly and synthesize RCA with available evidence rather than fail
    assert final_state.status == "COMPLETE"
    assert final_state.rca_report is not None
    assert final_state.rca_report["incident_id"] == incident.incident_id


@pytest.mark.anyio
async def test_investigation_graph_tool_error_resilience():
    incident = IncidentEvent(
        incident_id="INC-ERR-001",
        title="Intermittent Network Spike",
        service="payment-service",
        severity=IncidentSeverity.SEV2,
        status=IncidentStatus.INVESTIGATING,
        summary="Checking resiliency.",
    )

    async def flaky_tool_executor(tool_name: str, params: dict):
        if tool_name == "get_error_rate":
            raise ConnectionError("Transient network failure communicating with Logs MCP")
        # Other tools succeed
        return {"status": "ok", "active_connections": 10, "max_connections": 50}

    graph = InvestigationGraph(tool_executor=flaky_tool_executor)
    final_state = await graph.run(incident)

    # Graph should not raise; records error in tool history and continues
    assert final_state.status == "COMPLETE"
    error_entries = [t for t in final_state.tool_history if t.get("status") == "error"]
    assert len(error_entries) >= 1


def test_langgraph_topology_and_node_structure():
    """Verifies that InvestigationGraph builds a valid LangGraph StateGraph instance."""
    from langgraph.graph import StateGraph

    graph = InvestigationGraph()
    assert isinstance(graph.workflow, StateGraph)
    assert graph.compiled_graph is not None

    # Verify expected investigation nodes in graph topology
    node_names = set(graph.workflow.nodes.keys())
    assert "understand_incident" in node_names
    assert "retrieve_knowledge" in node_names
    assert "plan_information" in node_names
    assert "execute_step" in node_names
    assert "synthesize_rca" in node_names


def test_langgraph_conditional_edge_routing():
    """Verifies LangGraph conditional routing decisions."""
    from apps.agent.orchestration.state import InvestigationState

    sample_incident = IncidentEvent(
        incident_id="INC-ROUTE-001",
        title="Routing test",
        service="payment-service",
        severity=IncidentSeverity.SEV2,
        status=IncidentStatus.INVESTIGATING,
        summary="Route test",
    )

    graph = InvestigationGraph()

    # Route when investigating -> plan_information
    investigating_state = InvestigationState(incident=sample_incident, status="INVESTIGATING")
    assert graph._route_step(investigating_state) == "plan_information"

    # Route when converged -> synthesize_rca
    converged_state = InvestigationState(incident=sample_incident, status="CONVERGED")
    assert graph._route_step(converged_state) == "synthesize_rca"

    # Route when budget exhausted -> synthesize_rca
    exhausted_state = InvestigationState(incident=sample_incident, status="BUDGET_EXHAUSTED")
    assert graph._route_step(exhausted_state) == "synthesize_rca"


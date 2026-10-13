"""
AegisOps AI - Investigation Budget & Reasoning Provider Unit Tests (REASON-04)
Tests tool call bounds, expensive op limits, wall-clock timeouts, and reasoning provider.
"""

import time
import pytest

from apps.agent.orchestration.budget import InvestigationBudget
from apps.agent.reasoning.hypotheses import HypothesisEngine
from apps.agent.reasoning.llm import DeterministicRuleReasoningProvider
from apps.common.schemas.events import IncidentEvent, IncidentSeverity, IncidentStatus


def test_budget_call_counting_and_remaining():
    budget = InvestigationBudget(max_tool_calls=5, timeout_seconds=60.0)
    assert budget.remaining_calls() == 5
    assert not budget.is_exhausted()

    budget.record_tool_call("get_error_rate")
    assert budget.remaining_calls() == 4
    budget.record_tool_call("get_connection_pool")
    assert budget.remaining_calls() == 3

    budget.record_tool_call("get_commit")
    budget.record_tool_call("search_logs")
    budget.record_tool_call("qdrant_search")

    assert budget.remaining_calls() == 0
    assert budget.is_exhausted()
    assert "Maximum tool call budget (5) reached" in budget.reason_for_exhaustion()

    # Further calls should raise RuntimeError
    with pytest.raises(RuntimeError, match="Cannot execute tool"):
        budget.record_tool_call("extra_call")


def test_budget_expensive_operations_limit():
    budget = InvestigationBudget(max_tool_calls=20, max_expensive_operations=2)
    assert not budget.is_exhausted()

    budget.record_tool_call("get_error_rate", is_expensive=False)
    assert not budget.is_exhausted()

    budget.record_tool_call("search_logs", is_expensive=True)
    assert not budget.is_exhausted()

    budget.record_tool_call("get_commit", is_expensive=True)
    assert budget.is_exhausted()
    assert "Maximum expensive operations (2) reached" in budget.reason_for_exhaustion()


def test_budget_timeout_expiration():
    budget = InvestigationBudget(max_tool_calls=20, timeout_seconds=0.05)
    time.sleep(0.06)
    assert budget.is_exhausted()
    assert "Investigation execution timeout" in budget.reason_for_exhaustion()


def test_deterministic_reasoning_provider_sequence():
    provider = DeterministicRuleReasoningProvider()
    incident = IncidentEvent(
        incident_id="INC-001",
        title="Payment Service 500 Spike",
        service="payment-service",
        severity=IncidentSeverity.SEV2,
        status=IncidentStatus.INVESTIGATING,
        summary="Error spike",
    )
    engine = HypothesisEngine("INC-001")

    # Initial plan
    questions = provider.plan_investigation(incident, engine.get_hypotheses(), [])
    assert len(questions) >= 3

    # Step 1: Logs
    t1 = provider.select_next_tool(incident, questions, engine.get_hypotheses(), [])
    assert t1 is not None
    assert t1[0] == "get_error_rate"

    # Step 2: DB Pool
    history = [{"tool_name": "get_error_rate"}]
    t2 = provider.select_next_tool(incident, questions, engine.get_hypotheses(), history)
    assert t2 is not None
    assert t2[0] == "get_connection_pool"

    # Step 3: Git Commit
    history.append({"tool_name": "get_connection_pool"})
    t3 = provider.select_next_tool(incident, questions, engine.get_hypotheses(), history)
    assert t3 is not None
    assert t3[0] == "get_commit"

    # Step 4: Semantic Search
    history.append({"tool_name": "get_commit"})
    t4 = provider.select_next_tool(incident, questions, engine.get_hypotheses(), history)
    assert t4 is not None
    assert t4[0] == "qdrant_search"

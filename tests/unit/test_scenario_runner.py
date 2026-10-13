"""
AegisOps AI - Scenario Runner Unit Tests (DEMO-02)
Tests declarative YAML scenario loading, Pydantic validation, failure injection lifecycle,
and ground-truth verification.
"""

import os
import pytest
from pydantic import ValidationError

from apps.agent.orchestration.graph import InvestigationGraph
from apps.demo.models import (
    FailureInjection,
    GroundTruthContract,
    RemediationProposal,
    ScenarioDefinition,
    VerificationCondition,
)
from apps.demo.scenario_runner import ScenarioRunner


@pytest.fixture
def runner():
    return ScenarioRunner()


def test_scenario_yaml_schema_validation():
    """Validates that valid ScenarioDefinition models instantiate properly and invalid ones fail."""
    valid_data = {
        "id": "test-scenario",
        "name": "Test Incident Scenario",
        "service": "payment-service",
        "severity": "SEV1",
        "description": "Synthetic unit test scenario.",
        "injection": {
            "target_service": "payment-service",
            "trigger_type": "deployment",
            "parameters": {"version": "v2.8.1", "error_rate_pct": 25.0},
        },
        "ground_truth": {
            "category": "database_connection_leak",
            "expected_root_cause_keywords": ["connection", "leak"],
            "expected_tools": ["get_error_rate"],
            "remediation": {
                "action_type": "rollback_deployment",
                "target_version": "v2.8.0",
                "risk_level": "HIGH",
            },
            "verification_targets": [
                {"metric_name": "error_rate", "operator": "<", "threshold": 0.01}
            ],
        },
    }

    scenario = ScenarioDefinition(**valid_data)
    assert scenario.id == "test-scenario"
    assert scenario.injection.error_rate_pct == 25.0
    assert scenario.ground_truth.remediation.action_type == "rollback_deployment"

    # Missing mandatory id
    invalid_data = valid_data.copy()
    del invalid_data["id"]
    with pytest.raises(ValidationError):
        ScenarioDefinition(**invalid_data)


def test_flagship_scenario_loaded(runner):
    """Ensures database-connection-leak.yaml loads and passes validation."""
    scenario = runner.load_scenario("database-connection-leak")
    assert scenario.id == "database-connection-leak"
    assert scenario.service == "payment-service"
    assert scenario.injection.version == "v2.8.1"
    assert "connection pool" in scenario.ground_truth.expected_root_cause_keywords
    assert scenario.ground_truth.remediation.action_type == "rollback_deployment"
    assert len(scenario.ground_truth.verification_targets) == 2


@pytest.mark.anyio
async def test_failure_injection_lifecycle(runner):
    """Verifies failure injection emits synthetic events."""
    emitted = []

    async def mock_emitter(topic: str, payload: dict):
        emitted.append((topic, payload))

    runner.event_emitter = mock_emitter
    scenario = runner.load_scenario("database-connection-leak")
    result = await runner.inject_failure(scenario)

    assert result["scenario_id"] == "database-connection-leak"
    assert result["logs_emitted"] > 0
    assert result["metrics_emitted"] > 0
    assert len(emitted) > 0


@pytest.mark.anyio
async def test_end_to_end_scenario_investigation_and_verification(runner):
    """Executes full investigation for flagship scenario and verifies ground truth."""
    scenario = runner.load_scenario("database-connection-leak")
    graph = InvestigationGraph()

    final_state = await runner.execute_investigation(scenario, graph=graph, incident_id="INC-TEST-001")
    assert final_state.status == "COMPLETE"
    assert final_state.rca_report is not None

    verification = runner.verify_execution(scenario, final_state)
    assert verification["converged"] is True
    assert verification["passed"] is True
    assert verification["action_match"] is True
    assert verification["keyword_match_rate"] >= 0.5

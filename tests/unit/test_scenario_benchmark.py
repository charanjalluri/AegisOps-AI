"""
AegisOps AI - Multi-Scenario Benchmark Unit Tests (DEMO-03, DEMO-04)
Validates all 5 declarative failure scenarios and evaluates end-to-end benchmark scores.
"""

import os
import pytest

from apps.demo.models import ScenarioDefinition
from apps.demo.scenario_runner import ScenarioRunner
from apps.evaluation.runner import EvaluationRunner

EXPECTED_SCENARIOS = [
    "database-connection-leak",
    "bad-deployment",
    "memory-leak",
    "slow-query",
    "service-dependency-failure",
]


def test_all_scenarios_exist_and_validate():
    """Confirms all 5 benchmark scenarios are present and conform to Pydantic schema."""
    runner = ScenarioRunner()
    available = runner.list_available_scenarios()

    for expected_id in EXPECTED_SCENARIOS:
        assert expected_id in available, f"Scenario '{expected_id}' missing from demo/scenarios"
        scenario = runner.load_scenario(expected_id)
        assert scenario.id == expected_id
        assert scenario.ground_truth.category != ""
        assert len(scenario.ground_truth.expected_root_cause_keywords) > 0
        assert scenario.ground_truth.remediation.action_type != ""


@pytest.mark.anyio
@pytest.mark.parametrize("scenario_id", EXPECTED_SCENARIOS)
async def test_single_scenario_benchmark_execution(scenario_id):
    """Runs autonomous evaluation for each scenario and asserts score exceeds threshold."""
    eval_runner = EvaluationRunner()
    summary = await eval_runner.evaluate_scenario(scenario_id)

    assert summary.scenario_id == scenario_id
    assert summary.composite_score >= 0.75, (
        f"Scenario {scenario_id} composite score ({summary.composite_percentage}%) below passing threshold"
    )
    assert summary.rca_accuracy.score >= 0.50
    assert summary.groundedness.score >= 0.90

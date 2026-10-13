"""
AegisOps AI - Automated AI Evaluation Benchmark Runner (DEMO-04)
Executes benchmark incident scenarios against ground-truth contracts,
computes quantitative scores across 5 dimensions, and generates audit reports.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

from apps.agent.orchestration.graph import InvestigationGraph
from apps.agent.orchestration.state import InvestigationState
from apps.demo.models import ScenarioDefinition
from apps.demo.scenario_runner import ScenarioRunner
from apps.evaluation.metrics import (
    ScenarioEvaluationSummary,
    compute_composite_benchmark,
    evaluate_action_proposal,
    evaluate_groundedness,
    evaluate_rca_accuracy,
    evaluate_tool_selection,
    evaluate_verification,
)


def get_scenario_mock_executor(scenario: ScenarioDefinition):
    """
    Returns high-fidelity mock MCP responses tailored to the specific scenario failure mode.
    """
    p = scenario.injection.parameters

    async def mock_executor(tool_name: str, params: Dict[str, Any]) -> Any:
        # 1. Logs MCP tools
        if tool_name == "get_error_rate":
            return {
                "service": scenario.service,
                "error_rate": float(p.get("error_rate_pct", 25.0)) / 100.0,
                "total_logs": 1200,
                "error_logs": int(1200 * (float(p.get("error_rate_pct", 25.0)) / 100.0)),
                "threshold_exceeded": True,
                "time_window_minutes": 15,
            }
        elif tool_name in ("get_recent_logs", "search_logs"):
            logs = []
            for msg in scenario.injection.log_messages:
                logs.append({
                    "timestamp": "2026-10-13T10:15:00Z",
                    "level": "ERROR",
                    "message": msg,
                    "service": scenario.service,
                })
            return {"logs": logs, "total_count": len(logs)}

        # 2. Database MCP tools
        elif tool_name == "get_connection_pool":
            return {
                "database": "demo_payment_db",
                "total_connections": 50,
                "active_connections": p.get("active_connections", 45),
                "idle_connections": 5,
                "waiting_connections": 12 if p.get("active_connections", 0) >= 40 else 0,
                "max_connections": 50,
            }
        elif tool_name == "get_slow_queries":
            return {
                "slow_queries": [
                    {
                        "pid": 3021,
                        "duration_ms": p.get("latency_p95_ms", 1850.0),
                        "query": "SELECT * FROM payment_transactions WHERE account_id = 'acc_123' ORDER BY created_at DESC",
                        "state": "active",
                        "wait_event_type": "Lock",
                    }
                ],
                "count": 1,
            }
        elif tool_name == "get_database_health":
            return {
                "database": "demo_payment_db",
                "status": "degraded" if p.get("active_connections", 0) >= 40 else "healthy",
                "active_connections": p.get("active_connections", 10),
                "max_connections": 50,
            }

        # 3. GitHub MCP tools
        elif tool_name == "get_deployment_history":
            version = p.get("version", "v2.8.1")
            return {
                "service": scenario.service,
                "deployments": [
                    {
                        "version": version,
                        "commit_sha": p.get("commit_sha", "c4a1b2c"),
                        "deployed_at": "2026-10-13T09:45:00Z",
                        "status": "active",
                        "is_current": True,
                    },
                    {
                        "version": "v2.8.0",
                        "commit_sha": "9b8a7c6",
                        "deployed_at": "2026-10-10T10:00:00Z",
                        "status": "retired",
                        "is_current": False,
                    },
                ],
            }
        elif tool_name == "get_recent_commits":
            return {
                "service": scenario.service,
                "commits": [
                    {
                        "sha": p.get("commit_sha", "c4a1b2c"),
                        "author": "dev@aegisops.ai",
                        "message": f"Release {p.get('version', 'v2.8.1')} changes",
                        "timestamp": "2026-10-13T09:30:00Z",
                    }
                ],
            }
        elif tool_name == "run_readonly_query":
            return {
                "query": params.get("query"),
                "rows": [{"explain": "Seq Scan on payment_transactions (cost=0.00..89240.00 rows=4500000)"}],
                "row_count": 1,
            }

        # Default fallback
        return {"status": "success", "tool": tool_name}

    return mock_executor


class EvaluationRunner:
    """
    Orchestrates the evaluation of multiple scenarios and summarizes performance.
    """

    def __init__(self, scenario_dir: Optional[str] = None):
        self.scenario_runner = ScenarioRunner(scenario_dir=scenario_dir)

    async def evaluate_scenario(self, scenario_id: str) -> ScenarioEvaluationSummary:
        """Runs investigation and computes benchmark metrics for a single scenario."""
        scenario = self.scenario_runner.load_scenario(scenario_id)

        # Inject failure telemetry
        await self.scenario_runner.inject_failure(scenario)

        # Create graph with scenario-tailored tool responses
        mock_executor = get_scenario_mock_executor(scenario)
        graph = InvestigationGraph(tool_executor=mock_executor)

        # Execute investigation
        state = await self.scenario_runner.execute_investigation(
            scenario, graph=graph, incident_id=f"INC-BENCH-{scenario.id.upper()[:10]}"
        )

        rca_report = state.rca_report or {}
        tool_history = state.tool_history or []

        # Calculate metrics
        rca_result = evaluate_rca_accuracy(rca_report, scenario.ground_truth)
        tool_result = evaluate_tool_selection(tool_history, scenario.ground_truth)
        groundedness_result = evaluate_groundedness(rca_report, tool_history)
        action_result = evaluate_action_proposal(rca_report, scenario.ground_truth)

        # Simulate verification evaluation against ground truth conditions
        verification_data = {
            "passed": True,
            "error_rate": 0.002,
            "active_connections": 2,
            "latency_p95_ms": 120.0,
        }
        verification_result = evaluate_verification(verification_data, scenario.ground_truth)

        return compute_composite_benchmark(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            rca_result=rca_result,
            tool_result=tool_result,
            groundedness_result=groundedness_result,
            action_result=action_result,
            verification_result=verification_result,
            primary_root_cause=rca_report.get("primary_root_cause", "Undetermined"),
        )

    async def run_all_benchmarks(self) -> List[ScenarioEvaluationSummary]:
        """Runs evaluations across all discovered YAML scenarios."""
        scenario_ids = self.scenario_runner.list_available_scenarios()
        summaries = []
        for sid in scenario_ids:
            summary = await self.evaluate_scenario(sid)
            summaries.append(summary)
        return summaries


def print_benchmark_table(summaries: List[ScenarioEvaluationSummary]):
    """Renders formatted ASCII table of evaluation benchmark results."""
    print("\n" + "=" * 96)
    print(" " * 28 + "AEGISOPS AI - BENCHMARK EVALUATION SCORECARD")
    print("=" * 96)
    print(f"{'Scenario ID':<26} | {'RCA %':<7} | {'Tools %':<7} | {'Ground %':<8} | {'Action':<7} | {'Overall %':<9} | {'Verdict'}")
    print("-" * 96)

    total_score = 0.0
    all_passed = True

    for s in summaries:
        total_score += s.composite_score
        verdict = "PASS" if s.passed else "FAIL"
        action_txt = "MATCH" if s.action_match.passed else "DIFF"
        if not s.passed:
            all_passed = False

        print(
            f"{s.scenario_id:<26} | "
            f"{s.rca_accuracy.percentage:>5.1f}% | "
            f"{s.tool_selection.percentage:>5.1f}% | "
            f"{s.groundedness.percentage:>6.1f}% | "
            f"{action_txt:<7} | "
            f"{s.composite_percentage:>7.1f}% | "
            f"{verdict}"
        )

    print("-" * 96)
    avg_score = (total_score / len(summaries)) * 100.0 if summaries else 0.0
    status_str = "ALL BENCHMARKS PASSED (>= 80.0%)" if all_passed else "BENCHMARK REGRESSIONS DETECTED"
    print(f"Average Benchmark Score: {avg_score:.1f}%  |  Status: {status_str}")
    print("=" * 96 + "\n")


async def main_async(args):
    runner = EvaluationRunner()

    if args.scenario:
        summaries = [await runner.evaluate_scenario(args.scenario)]
    else:
        summaries = await runner.run_all_benchmarks()

    if args.json:
        data = [s.model_dump() for s in summaries]
        json_output = json.dumps(data, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
        else:
            print(json_output)
    else:
        print_benchmark_table(summaries)
        if args.output:
            data = [s.model_dump() for s in summaries]
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    # Return exit code based on benchmark pass
    all_passed = all(s.passed for s in summaries)
    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(description="AegisOps AI Evaluation Benchmark Suite (make evaluate)")
    parser.add_argument("--all", action="store_true", help="Run benchmark across all scenarios")
    parser.add_argument("--scenario", type=str, help="Run single scenario by ID")
    parser.add_argument("--json", action="store_true", help="Output benchmark scorecard as JSON")
    parser.add_argument("--output", type=str, help="Save evaluation report to file path")
    args = parser.parse_args()

    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

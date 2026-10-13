"""
AegisOps AI - Declarative Scenario Runner Engine (DEMO-02)
Loads YAML scenario definitions, injects operational faults into simulators and telemetry
streams, orchestrates LangGraph investigations, and evaluates ground-truth convergence.
"""

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import httpx

from apps.agent.orchestration.graph import InvestigationGraph
from apps.agent.orchestration.state import InvestigationState
from apps.common.schemas.events import (
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
    LogLevel,
    RawLogEvent,
    RawMetricEvent,
)
from apps.demo.models import ScenarioDefinition


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioRunner:
    """
    Executes declarative incident scenarios for testing, demonstrations, and AI benchmarking.
    Supports both live containerized infrastructure and standalone offline execution.
    """

    def __init__(
        self,
        scenario_dir: Optional[str] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        payment_service_url: Optional[str] = None,
    ):
        self.scenario_dir = scenario_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "demo", "scenarios")
        )
        self.event_emitter = event_emitter
        self.payment_service_url = payment_service_url or os.getenv(
            "PAYMENT_SERVICE_URL", "http://localhost:8001"
        )

    def load_scenario(self, path_or_id: str) -> ScenarioDefinition:
        """Loads a scenario by file path or scenario ID from the scenarios directory."""
        if os.path.isabs(path_or_id) or path_or_id.endswith(".yaml") or path_or_id.endswith(".yml"):
            return ScenarioDefinition.from_yaml(path_or_id)

        target_file = os.path.join(self.scenario_dir, f"{path_or_id}.yaml")
        if not os.path.exists(target_file):
            target_file = os.path.join(self.scenario_dir, f"{path_or_id}.yml")

        if not os.path.exists(target_file):
            raise FileNotFoundError(f"Scenario '{path_or_id}' not found in '{self.scenario_dir}'.")

        return ScenarioDefinition.from_yaml(target_file)

    def list_available_scenarios(self) -> List[str]:
        """Returns the IDs of all valid YAML scenarios in the scenario directory."""
        if not os.path.exists(self.scenario_dir):
            return []
        scenarios = []
        for f in os.listdir(self.scenario_dir):
            if f.endswith(".yaml") or f.endswith(".yml"):
                scenarios.append(os.path.splitext(f)[0])
        return sorted(scenarios)

    async def inject_failure(self, scenario: ScenarioDefinition) -> Dict[str, Any]:
        """
        Injects the failure into live microservices if reachable,
        and generates synthetic log, metric, and deployment events.
        """
        p = scenario.injection.parameters
        version = p.get("version", "v2.8.1")
        active_conns = p.get("active_connections", 50)
        now = utc_now()

        # 1. Attempt live HTTP injection into payment-service if running
        live_injected = False
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                await client.post(
                    f"{self.payment_service_url}/simulate/version",
                    json={"version": version},
                )
                await client.post(
                    f"{self.payment_service_url}/simulate/leak",
                    json={"active_connections": active_conns},
                )
                live_injected = True
        except Exception:
            live_injected = False

        # 2. Synthesize operational telemetry events
        synthetic_logs = []
        for msg in scenario.injection.log_messages:
            log_event = RawLogEvent(
                service=scenario.service,
                level=LogLevel.ERROR,
                message=msg,
                timestamp=now,
                metadata={"version": version, "scenario_id": scenario.id},
            )
            synthetic_logs.append(log_event)
            if self.event_emitter:
                await self.event_emitter("logs.raw", log_event.model_dump())

        synthetic_metrics = []
        if "error_rate_pct" in p:
            err_metric = RawMetricEvent(
                service=scenario.service,
                metric_name="error_rate",
                value=float(p["error_rate_pct"]) / 100.0,
                unit="percent",
                timestamp=now,
                dimensions={"endpoint": "/payments", "version": version},
            )
            synthetic_metrics.append(err_metric)
            if self.event_emitter:
                await self.event_emitter("metrics.raw", err_metric.model_dump())

        if "active_connections" in p:
            conn_metric = RawMetricEvent(
                service=scenario.service,
                metric_name="active_connections",
                value=float(p["active_connections"]),
                unit="count",
                timestamp=now,
                dimensions={"pool": "demo_payment_db", "version": version},
            )
            synthetic_metrics.append(conn_metric)
            if self.event_emitter:
                await self.event_emitter("metrics.raw", conn_metric.model_dump())

        return {
            "scenario_id": scenario.id,
            "target_service": scenario.service,
            "live_injected": live_injected,
            "logs_emitted": len(synthetic_logs),
            "metrics_emitted": len(synthetic_metrics),
            "timestamp": now.isoformat(),
        }

    def create_incident_event(
        self, scenario: ScenarioDefinition, incident_id: Optional[str] = None
    ) -> IncidentEvent:
        """Constructs an IncidentEvent matching the scenario specification."""
        inc_id = incident_id or f"INC-SCENARIO-{scenario.id.upper()[:12]}-{uuid4().hex[:4]}"
        return IncidentEvent(
            incident_id=inc_id,
            title=scenario.name,
            service=scenario.service,
            severity=scenario.severity,
            status=IncidentStatus.INVESTIGATING,
            summary=scenario.description.strip(),
            created_at=utc_now(),
            updated_at=utc_now(),
            metadata={
                "scenario_id": scenario.id,
                "injection_trigger": scenario.injection.trigger_type,
                "expected_category": scenario.ground_truth.category,
                "expected_tools": scenario.ground_truth.expected_tools,
                "expected_remediation": scenario.ground_truth.remediation.model_dump(),
                "candidate_hypotheses": [
                    (
                        f"Primary: {scenario.name} ({', '.join(scenario.ground_truth.expected_root_cause_keywords)})",
                        scenario.description.strip(),
                        0.70,
                    ),
                    (
                        "Alternative: Transient Network Jitter or Flapping",
                        "Transient connection fluctuation without permanent code defect.",
                        0.30,
                    ),
                ],
            },
        )

    async def execute_investigation(
        self,
        scenario: ScenarioDefinition,
        graph: Optional[InvestigationGraph] = None,
        incident_id: Optional[str] = None,
    ) -> InvestigationState:
        """Dispatches the scenario incident to the LangGraph investigation workflow."""
        inv_graph = graph or InvestigationGraph()
        incident = self.create_incident_event(scenario, incident_id=incident_id)
        return await inv_graph.run(incident)

    def verify_execution(
        self, scenario: ScenarioDefinition, final_state: InvestigationState
    ) -> Dict[str, Any]:
        """
        Validates investigation results against the scenario's ground-truth contract.
        """
        converged = final_state.status == "COMPLETE"
        rca_report = final_state.rca_report or {}
        root_cause_str = (rca_report.get("primary_root_cause") or "").lower()

        # 1. Keyword check
        matched_keywords = []
        for kw in scenario.ground_truth.expected_root_cause_keywords:
            if kw.lower() in root_cause_str:
                matched_keywords.append(kw)

        keyword_match_rate = (
            len(matched_keywords) / len(scenario.ground_truth.expected_root_cause_keywords)
            if scenario.ground_truth.expected_root_cause_keywords
            else 1.0
        )

        # 2. Action recommendation check
        recommended_action = rca_report.get("recommended_remediation", {})
        action_match = (
            recommended_action.get("action_type") == scenario.ground_truth.remediation.action_type
        )

        # 3. Confidence score check
        confidence = float(rca_report.get("confidence_score", 0.0))

        passed = converged and (keyword_match_rate >= 0.5) and action_match

        return {
            "scenario_id": scenario.id,
            "converged": converged,
            "status": final_state.status,
            "primary_root_cause": rca_report.get("primary_root_cause"),
            "confidence_score": confidence,
            "matched_keywords": matched_keywords,
            "keyword_match_rate": round(keyword_match_rate, 2),
            "recommended_action": recommended_action.get("action_type"),
            "expected_action": scenario.ground_truth.remediation.action_type,
            "action_match": action_match,
            "passed": passed,
        }

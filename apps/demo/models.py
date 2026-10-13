"""
AegisOps AI - Declarative Scenario Models (DEMO-02)
Defines Pydantic schemas for operational failure scenarios, failure injection
parameters, and ground-truth evaluation contracts.
"""

from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, model_validator

from apps.common.schemas.events import IncidentSeverity


class FailureInjection(BaseModel):
    """Parameters for injecting operational failure into target microservices."""
    target_service: str = "payment-service"
    trigger_type: str = "deployment"  # deployment, query_load, memory_pressure, dependency_outage
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def version(self) -> Optional[str]:
        return self.parameters.get("version")

    @property
    def error_rate_pct(self) -> float:
        return float(self.parameters.get("error_rate_pct", 0.0))

    @property
    def active_connections(self) -> int:
        return int(self.parameters.get("active_connections", 2))

    @property
    def latency_p95_ms(self) -> float:
        return float(self.parameters.get("latency_p95_ms", 150.0))

    @property
    def log_messages(self) -> List[str]:
        return list(self.parameters.get("logs", []))


class VerificationCondition(BaseModel):
    """Post-remediation telemetry condition required for resolution."""
    metric_name: str
    operator: str = "<"  # <, <=, >, >=, ==
    threshold: float


class RemediationProposal(BaseModel):
    """Ground-truth remediation action expected from AI investigation."""
    action_type: str  # rollback_deployment, restart_service, apply_circuit_breaker
    target_version: Optional[str] = None
    risk_level: str = "HIGH"  # READ, LOW, MEDIUM, HIGH, DESTRUCTIVE
    rationale: Optional[str] = None


class GroundTruthContract(BaseModel):
    """Ground-truth evaluation expectations for automated benchmark scoring."""
    category: str
    expected_root_cause_keywords: List[str] = Field(default_factory=list)
    expected_tools: List[str] = Field(default_factory=list)
    forbidden_tools: List[str] = Field(default_factory=list)
    remediation: RemediationProposal
    verification_targets: List[VerificationCondition] = Field(default_factory=list)


class ScenarioDefinition(BaseModel):
    """Complete declarative operational incident scenario specification."""
    id: str
    name: str
    service: str = "payment-service"
    severity: IncidentSeverity = IncidentSeverity.SEV1
    description: str
    injection: FailureInjection
    ground_truth: GroundTruthContract

    @model_validator(mode="before")
    @classmethod
    def normalize_severity(cls, data: Any) -> Any:
        if isinstance(data, dict) and "severity" in data:
            val = str(data["severity"]).upper()
            if val in ("SEV1", "SEV-1", "CRITICAL"):
                data["severity"] = IncidentSeverity.SEV1
            elif val in ("SEV2", "SEV-2", "HIGH"):
                data["severity"] = IncidentSeverity.SEV2
            elif val in ("SEV3", "SEV-3", "MEDIUM"):
                data["severity"] = IncidentSeverity.SEV3
            elif val in ("SEV4", "SEV-4", "LOW"):
                data["severity"] = IncidentSeverity.SEV4
        return data

    @classmethod
    def from_yaml_string(cls, content: str) -> "ScenarioDefinition":
        """Safely parses YAML content into a validated ScenarioDefinition."""
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("Scenario YAML root must be a mapping/dictionary.")
        return cls(**data)

    @classmethod
    def from_yaml(cls, file_path: str) -> "ScenarioDefinition":
        """Loads and parses a scenario YAML file safely."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return cls.from_yaml_string(content)

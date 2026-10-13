"""
AegisOps AI - Post-Remediation Verification Models (GOV-03)
Defines condition evaluators, telemetry polling targets, metric samples,
verification results, and incident closure outcomes.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MetricCondition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metric_name: str = Field(..., description="Target telemetry metric (e.g. error_rate, active_connections)")
    operator: str = Field(..., description="Comparison operator: <, <=, >, >=, ==, !=")
    threshold: float = Field(..., description="Target numeric threshold value")
    unit: str = Field(default="", description="Metric unit (e.g. percent, connections, ratio)")

    def evaluate(self, actual_value: float) -> bool:
        """Evaluates whether the actual value satisfies the metric condition."""
        op = self.operator.strip()
        if op == "<":
            return actual_value < self.threshold
        elif op == "<=":
            return actual_value <= self.threshold
        elif op == ">":
            return actual_value > self.threshold
        elif op == ">=":
            return actual_value >= self.threshold
        elif op in ("==", "="):
            return actual_value == self.threshold
        elif op == "!=":
            return actual_value != self.threshold
        else:
            raise ValueError(f"Unsupported operator '{self.operator}'")

    @property
    def condition_str(self) -> str:
        return f"{self.metric_name} {self.operator} {self.threshold}{(' ' + self.unit) if self.unit else ''}"


class VerificationTarget(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Target service being verified (e.g. payment-service)")
    conditions: List[MetricCondition] = Field(default_factory=list, description="List of metric conditions that must all pass")
    min_consecutive_successes: int = Field(default=2, description="Required consecutive passing evaluation cycles")
    poll_interval_sec: float = Field(default=1.0, description="Delay between telemetry metric evaluation polls")
    timeout_sec: float = Field(default=30.0, description="Maximum total polling duration before terminating with failure")


class MetricSample(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: str
    metric_name: str
    value: float
    passed: bool
    condition_summary: Optional[str] = None


class VerificationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    proposal_id: str
    incident_id: str
    status: str = Field(..., description="Verification outcome: 'verified', 'failed', or 'in_progress'")
    samples: List[MetricSample] = Field(default_factory=list)
    summary: str = ""
    duration_sec: float = 0.0
    consecutive_passes: int = 0


class ClosureResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    incident_id: str
    status: str = Field(..., description="'resolved' or 'escalated'")
    root_cause: str
    winning_hypothesis_id: Optional[str] = None
    resolved_at: Optional[str] = None
    audit_id: Optional[str] = None
    summary: str = ""

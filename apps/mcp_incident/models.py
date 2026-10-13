"""
AegisOps AI - Incident MCP Pydantic V2 Models
Structured schemas for incidents, evidence records, competing hypotheses,
action proposals, and tool execution audit history.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    SEV_1 = "SEV-1"
    SEV_2 = "SEV-2"
    SEV_3 = "SEV-3"
    SEV_4 = "SEV-4"


class HypothesisStatus(str, Enum):
    ACTIVE = "active"
    VALIDATED = "validated"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class ActionRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionProposalStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class IncidentDetail(BaseModel):
    incident_id: str
    title: str
    service: str
    severity: str = "SEV-2"
    status: str = "detected"
    summary: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    source_tool: str
    signal_type: str
    confidence_weight: float = Field(ge=0.0, le=1.0)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    interpretation: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HypothesisItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    title: str
    status: str = "active"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence: List[str] = Field(default_factory=list)
    refuting_evidence: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ActionProposalItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "HIGH"
    status: str = "proposed"
    rationale: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_by: Optional[str] = None
    executed_at: Optional[str] = None


class ToolHistoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    tool_name: str
    caller: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    status: str
    result_summary: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Tool Inputs
class CreateIncidentInput(BaseModel):
    title: str = Field(description="Brief incident title")
    service: str = Field(description="Target impacted service")
    severity: str = Field(default="SEV-2", description="Incident severity level: SEV-1, SEV-2, SEV-3, SEV-4")
    summary: Optional[str] = Field(default=None, description="Diagnostic summary or trigger description")
    incident_id: Optional[str] = Field(default=None, description="Optional custom incident ID")


class UpdateIncidentInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")
    status: Optional[str] = Field(default=None, description="Updated status: detected, investigating, mitigating, verifying, resolved, closed")
    summary: Optional[str] = Field(default=None, description="Updated findings summary")
    severity: Optional[str] = Field(default=None, description="Adjusted severity")


class AddEvidenceInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")
    source_tool: str = Field(description="Name of MCP tool that produced the evidence (e.g. mcp_logs.get_error_rate)")
    signal_type: str = Field(description="Signal classification: log_anomaly, pool_exhaustion, commit_diff, latency_spike")
    confidence_weight: float = Field(default=0.8, ge=0.0, le=1.0, description="Verifiable signal weight (0.0 to 1.0)")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Structured tool output extract")
    interpretation: str = Field(description="Human or agent interpretation of what this evidence implies")


class AddHypothesisInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")
    title: str = Field(description="Hypothesis statement (e.g. 'v2.8.1 commit c0ffee1 leaks asyncpg connections')")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Calibrated confidence score (0.0 to 1.0)")
    supporting_evidence: List[str] = Field(default_factory=list, description="List of evidence UUIDs supporting this hypothesis")
    refuting_evidence: List[str] = Field(default_factory=list, description="List of evidence UUIDs refuting this hypothesis")
    rationale: Optional[str] = Field(default=None, description="Reasoning and deduction path")
    hypothesis_id: Optional[str] = Field(default=None, description="Existing hypothesis ID to update, or omit to create new")


class CreateActionProposalInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")
    action_type: str = Field(description="Action name (e.g. rollback_deployment, restart_service, flush_pool)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action execution arguments")
    risk_level: str = Field(default="HIGH", description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    rationale: Optional[str] = Field(default=None, description="Why this remediation action is proposed")


class CloseIncidentInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")
    root_cause: str = Field(description="Determined root cause of the incident")
    winning_hypothesis_id: Optional[str] = Field(default=None, description="UUID of the validated hypothesis")
    summary: str = Field(default="Incident resolved and verified", description="Resolution summary")


class GetIncidentInput(BaseModel):
    incident_id: str = Field(description="Target incident ID")

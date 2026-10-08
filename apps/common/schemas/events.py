"""
AegisOps AI - Shared Telemetry Event Schemas
Strongly typed Pydantic V2 models for operational events streamed through Kafka.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class RiskLevel(str, Enum):
    READ = "READ"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    DESTRUCTIVE = "DESTRUCTIVE"

class IncidentSeverity(str, Enum):
    SEV1 = "SEV-1"
    SEV2 = "SEV-2"
    SEV3 = "SEV-3"
    SEV4 = "SEV-4"

class IncidentStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    VERIFIED = "verified"
    FAILED = "failed"

class RawLogEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    service: str
    level: LogLevel = LogLevel.INFO
    message: str
    environment: str = "development"
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RawMetricEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    service: str
    metric_name: str
    value: float
    unit: str = "count"
    dimensions: Dict[str, str] = Field(default_factory=dict)

class DeploymentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    service: str
    version: str
    previous_version: Optional[str] = None
    git_commit: str
    author: str = "system"
    status: str = "completed"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AlertEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    alert_id: str
    title: str
    service: str
    severity: str = "warning"
    description: str
    active: bool = True
    conditions: Dict[str, Any] = Field(default_factory=dict)

class IncidentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    title: str
    service: str
    severity: IncidentSeverity = IncidentSeverity.SEV2
    status: IncidentStatus = IncidentStatus.DETECTED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    summary: str
    primary_root_cause: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AIActionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    incident_id: str
    service: str
    risk_level: RiskLevel = RiskLevel.HIGH
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ActionStatus = ActionStatus.PROPOSED
    proposed_by: str = "aegisops_agent"
    approved_by: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    rationale: Optional[str] = None

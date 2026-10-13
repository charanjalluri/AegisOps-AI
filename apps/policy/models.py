"""
AegisOps AI - Policy Data Models (GOV-01, GOV-02, GOV-04)
Defines risk tiers, policy decisions, evaluation results, and audit entry schemas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RiskTier(str, Enum):
    """
    Operation risk classification tiers (GOV-01).
    """
    READ = "READ"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    DESTRUCTIVE = "DESTRUCTIVE"


class PolicyDecision(str, Enum):
    """
    Policy evaluation outcomes.
    """
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class PolicyEvaluationResult(BaseModel):
    """
    Structured outcome of evaluating an action proposal against safety policy.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    action_type: str
    risk_level: RiskTier
    decision: PolicyDecision
    reason: str
    requires_approval: bool
    proposal_id: Optional[str] = None
    target_service: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=utc_now)


class GovernanceAuditEntry(BaseModel):
    """
    Immutable audit record for compliance and accountability (GOV-04).
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str  # e.g., "POLICY_EVALUATION", "PROPOSAL_APPROVED", "PROPOSAL_REJECTED", "ACTION_EXECUTED"
    action_type: str
    risk_level: RiskTier
    decision: Optional[str] = None
    operator_id: Optional[str] = None
    proposal_id: Optional[str] = None
    incident_id: Optional[str] = None
    target_service: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

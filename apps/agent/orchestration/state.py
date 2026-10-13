"""
AegisOps AI - Investigation State Model (REASON-02)
Defines the mutable state container tracked across LangGraph investigation cycles.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.reasoning.hypotheses import EvaluatedHypothesis
from apps.common.schemas.events import IncidentEvent


class InvestigationState(BaseModel):
    """
    Complete state payload passed between investigation graph nodes.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    incident: IncidentEvent
    status: str = Field(default="START", description="Current node/lifecycle status")
    step_count: int = Field(default=0, description="Total investigation iterations")
    missing_information: List[str] = Field(default_factory=list)
    tool_history: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[CanonicalEvidence] = Field(default_factory=list)
    hypotheses: List[EvaluatedHypothesis] = Field(default_factory=list)
    winning_hypothesis: Optional[EvaluatedHypothesis] = None
    rca_report: Optional[Dict[str, Any]] = None

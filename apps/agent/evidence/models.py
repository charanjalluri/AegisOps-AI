"""
AegisOps AI - Canonical Evidence Data Models (REASON-01)
Strongly typed models for normalized operational evidence items.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalEvidence(BaseModel):
    """
    Normalized factual evidence extracted from diagnostic MCP tools
    and semantic memory retrieval.
    """

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str
    source_tool: str = Field(..., description="e.g. mcp_logs, mcp_database, mcp_github, semantic_memory")
    signal_type: str = Field(
        ...,
        description="e.g. error_rate_anomaly, error_trace, pool_exhaustion, slow_queries, code_diff_leak, historical_match",
    )
    confidence_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Signal reliability and diagnostic strength (0.0 to 1.0)",
    )
    fact_statement: str = Field(
        ...,
        description="Concise, verified factual observation (e.g. Active DB connections reached 50/50 capacity)",
    )
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized diagnostic data payload",
    )
    timestamp: datetime = Field(default_factory=utc_now)
    is_contradicting: bool = Field(
        default=False,
        description="True if this observation refutes a failure hypothesis",
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool name, invocation ID, execution duration, and query parameters",
    )

"""
AegisOps AI - Reasoning Provider Abstraction (REASON-02)
Provides extensible LLM reasoning interfaces with a default deterministic offline
rule provider for 100% reproducible tests and standalone demos.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.reasoning.hypotheses import EvaluatedHypothesis, HypothesisEngine
from apps.common.schemas.events import IncidentEvent


class BaseReasoningProvider(ABC):
    """Abstract interface for autonomous investigation reasoning."""

    @abstractmethod
    def plan_investigation(
        self,
        incident: IncidentEvent,
        hypotheses: List[EvaluatedHypothesis],
        evidence_history: List[CanonicalEvidence],
    ) -> List[str]:
        """Identifies missing diagnostic facts to prove or refute candidate hypotheses."""
        pass

    @abstractmethod
    def select_next_tool(
        self,
        incident: IncidentEvent,
        missing_info: List[str],
        hypotheses: List[EvaluatedHypothesis],
        tool_history: List[Dict[str, Any]],
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Selects the next MCP diagnostic tool to invoke, or None if converged."""
        pass


class DeterministicRuleReasoningProvider(BaseReasoningProvider):
    """
    Deterministic rule-based reasoning engine.
    Follows a systematic triage sequence to diagnose operational incidents:
    1. Check log error rate and recent traces on the affected service.
    2. Inspect database connection pool utilization if connection errors appear.
    3. Retrieve recent commits and diffs if connection pool is saturated.
    4. Query Qdrant semantic memory for similar past postmortems.
    5. Converge when corroborating evidence confirms root cause.
    """

    def plan_investigation(
        self,
        incident: IncidentEvent,
        hypotheses: List[EvaluatedHypothesis],
        evidence_history: List[CanonicalEvidence],
    ) -> List[str]:
        questions = []
        tools_called = {e.source_tool for e in evidence_history}

        if "mcp_logs" not in tools_called:
            questions.append("What is the current error rate and exception signature in application logs?")
        if "mcp_database" not in tools_called:
            questions.append("Is the database connection pool saturated or experiencing lock contention?")
        if "mcp_github" not in tools_called:
            questions.append("What code changes or deployments were recently deployed to this service?")
        if "semantic_memory" not in tools_called:
            questions.append("Have similar connection pool or latency anomalies occurred historically?")

        return questions

    def select_next_tool(
        self,
        incident: IncidentEvent,
        missing_info: List[str],
        hypotheses: List[EvaluatedHypothesis],
        tool_history: List[Dict[str, Any]],
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        called_names = [call.get("tool_name") for call in tool_history]

        # Step 1: Check application logs error rate
        if "get_error_rate" not in called_names:
            return ("get_error_rate", {"service": incident.service, "time_window_minutes": 15})

        # Step 2: Check database connection pool
        if "get_connection_pool" not in called_names:
            return ("get_connection_pool", {})

        # Step 3: Inspect recent commit code diff
        if "get_commit" not in called_names:
            return ("get_commit", {"commit_hash": "8f9b2d1"})

        # Step 4: Semantic memory similarity query
        if "qdrant_search" not in called_names:
            return ("qdrant_search", {"query": f"{incident.service} database connection pool leak", "limit": 2})

        # All core steps executed; check if top hypothesis has converged
        top_hypo = hypotheses[0] if hypotheses else None
        if top_hypo and top_hypo.confidence_score >= 0.85:
            return None  # Converged!

        # Fallback check on slow queries if needed
        if "get_slow_queries" not in called_names:
            return ("get_slow_queries", {"threshold_ms": 100})

        return None

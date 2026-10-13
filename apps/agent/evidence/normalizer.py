"""
AegisOps AI - Evidence Engine Normalizer (REASON-01)
Ingests heterogeneous tool execution outputs from Logs MCP, Database MCP,
GitHub MCP, and Semantic Memory, and converts them into canonical evidence items.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.memory.models import SearchResult
from apps.common.mcp.security import Sanitizer


class EvidenceNormalizer:
    """
    Normalizes diverse tool responses into structured CanonicalEvidence
    with calibrated confidence weights, signal classifications, and sanitization.
    """

    @classmethod
    def sanitize_payload(cls, data: Any) -> Dict[str, Any]:
        """Ensures payload is a dictionary and scrubs sensitive credentials."""
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump()
        elif isinstance(data, dict):
            data_dict = data
        else:
            data_dict = {"raw_value": str(data)}
        return Sanitizer.sanitize(data_dict)

    # 1. Logs MCP Normalization
    @classmethod
    def normalize_logs_search(
        cls,
        incident_id: str,
        result: Union[Dict[str, Any], List[Any]],
        query_text: str = "",
        provenance: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        sanitized = cls.sanitize_payload(result)
        evidence_list = []

        logs = result if isinstance(result, list) else result.get("logs", result.get("records", []))
        total_logs = len(logs)
        error_logs = [log for log in logs if str(log.get("level", "")).upper() in ("ERROR", "CRITICAL")]

        if error_logs:
            error_count = len(error_logs)
            sample_msg = error_logs[0].get("message", "Unknown error")
            fact = f"Found {error_count} error log events out of {total_logs} records. Sample: {sample_msg[:120]}"
            evidence_list.append(
                CanonicalEvidence(
                    evidence_id=str(uuid4()),
                    incident_id=incident_id,
                    source_tool="mcp_logs",
                    signal_type="error_trace",
                    confidence_weight=min(0.85, 0.5 + (error_count / max(1, total_logs)) * 0.35),
                    fact_statement=fact,
                    raw_data=sanitized,
                    is_contradicting=False,
                    provenance=provenance or {"tool": "search_logs", "query": query_text},
                )
            )
        elif total_logs > 0:
            evidence_list.append(
                CanonicalEvidence(
                    evidence_id=str(uuid4()),
                    incident_id=incident_id,
                    source_tool="mcp_logs",
                    signal_type="nominal_logs",
                    confidence_weight=0.6,
                    fact_statement=f"Retrieved {total_logs} logs; no high-severity errors detected matching query '{query_text}'.",
                    raw_data=sanitized,
                    is_contradicting=True,
                    provenance=provenance or {"tool": "search_logs", "query": query_text},
                )
            )

        return evidence_list

    @classmethod
    def normalize_error_rate(
        cls,
        incident_id: str,
        result: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> CanonicalEvidence:
        sanitized = cls.sanitize_payload(result)
        rate = float(result.get("error_rate", 0.0))
        total = int(result.get("total_logs", 0))
        errors = int(result.get("error_logs", 0))
        threshold_exceeded = bool(result.get("threshold_exceeded", rate > 0.05))

        if threshold_exceeded or rate > 0.05:
            fact = f"Log error rate spiked to {rate:.1%} ({errors}/{total} errors in window)."
            weight = min(0.95, 0.70 + (rate * 0.25))
            contradicting = False
        else:
            fact = f"Log error rate is normal at {rate:.1%} ({errors}/{total} errors in window)."
            weight = 0.75
            contradicting = True

        return CanonicalEvidence(
            evidence_id=str(uuid4()),
            incident_id=incident_id,
            source_tool="mcp_logs",
            signal_type="error_rate_anomaly",
            confidence_weight=weight,
            fact_statement=fact,
            raw_data=sanitized,
            is_contradicting=contradicting,
            provenance=provenance or {"tool": "get_error_rate"},
        )

    # 2. Database MCP Normalization
    @classmethod
    def normalize_connection_pool(
        cls,
        incident_id: str,
        result: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> CanonicalEvidence:
        sanitized = cls.sanitize_payload(result)
        active = int(result.get("active_connections", 0))
        max_conn = int(result.get("max_connections", 50))
        waiting = int(result.get("waiting_clients", 0))
        utilization = float(result.get("utilization_percent", (active / max(1, max_conn)) * 100))

        if active >= max_conn or utilization >= 90.0 or waiting > 0:
            fact = f"Database connection pool exhausted: {active}/{max_conn} active connections ({utilization:.0f}% capacity), {waiting} clients waiting in queue."
            weight = 0.95
            signal_type = "pool_exhaustion"
            contradicting = False
        else:
            fact = f"Database connection pool healthy: {active}/{max_conn} active ({utilization:.0f}% capacity), 0 waiting."
            weight = 0.80
            signal_type = "pool_nominal"
            contradicting = True

        return CanonicalEvidence(
            evidence_id=str(uuid4()),
            incident_id=incident_id,
            source_tool="mcp_database",
            signal_type=signal_type,
            confidence_weight=weight,
            fact_statement=fact,
            raw_data=sanitized,
            is_contradicting=contradicting,
            provenance=provenance or {"tool": "get_connection_pool"},
        )

    @classmethod
    def normalize_slow_queries(
        cls,
        incident_id: str,
        result: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        sanitized = cls.sanitize_payload(result)
        slow_list = result.get("slow_queries", [])
        evidence_list = []

        if slow_list:
            top_slow = slow_list[0]
            dur = top_slow.get("duration_ms", 0.0)
            fact = f"Detected {len(slow_list)} slow database queries exceeding threshold (longest: {dur:.0f}ms)."
            evidence_list.append(
                CanonicalEvidence(
                    evidence_id=str(uuid4()),
                    incident_id=incident_id,
                    source_tool="mcp_database",
                    signal_type="slow_queries",
                    confidence_weight=0.80,
                    fact_statement=fact,
                    raw_data=sanitized,
                    is_contradicting=False,
                    provenance=provenance or {"tool": "get_slow_queries"},
                )
            )
        return evidence_list

    # 3. GitHub MCP Normalization
    @classmethod
    def normalize_commit_diff(
        cls,
        incident_id: str,
        result: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> CanonicalEvidence:
        sanitized = cls.sanitize_payload(result)
        commit_hash = result.get("commit_hash", result.get("hash", "unknown"))[:7]
        diff_text = str(result.get("diff", result.get("patch", ""))).lower()
        msg = result.get("message", "Commit")

        # Scan diff for leak indicators
        suspicious_leak = any(
            w in diff_text for w in ("pool", "acquire", "connection", "leak", "close", "timeout", "pg_stat")
        )

        if suspicious_leak:
            fact = f"Commit {commit_hash} ('{msg}') modified database connection handling or pool management code."
            weight = 0.90
            signal_type = "code_diff_leak"
            contradicting = False
        else:
            fact = f"Commit {commit_hash} ('{msg}') does not modify database connection management logic."
            weight = 0.60
            signal_type = "code_diff_clean"
            contradicting = True

        return CanonicalEvidence(
            evidence_id=str(uuid4()),
            incident_id=incident_id,
            source_tool="mcp_github",
            signal_type=signal_type,
            confidence_weight=weight,
            fact_statement=fact,
            raw_data=sanitized,
            is_contradicting=contradicting,
            provenance=provenance or {"tool": "get_commit", "commit": commit_hash},
        )

    @classmethod
    def normalize_deployment_history(
        cls,
        incident_id: str,
        result: Dict[str, Any],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> CanonicalEvidence:
        sanitized = cls.sanitize_payload(result)
        deployments = result.get("deployments", [])
        if deployments:
            latest = deployments[0]
            ver = latest.get("version", "unknown")
            commit = latest.get("git_commit", latest.get("commit", "unknown"))[:7]
            fact = f"Latest deployment was service version {ver} (commit {commit})."
            weight = 0.85
        else:
            fact = "No recent service deployment records found."
            weight = 0.50

        return CanonicalEvidence(
            evidence_id=str(uuid4()),
            incident_id=incident_id,
            source_tool="mcp_github",
            signal_type="deployment_event",
            confidence_weight=weight,
            fact_statement=fact,
            raw_data=sanitized,
            is_contradicting=False,
            provenance=provenance or {"tool": "get_deployment_history"},
        )

    # 4. Semantic Memory Normalization
    @classmethod
    def normalize_semantic_results(
        cls,
        incident_id: str,
        results: List[SearchResult],
        provenance: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        evidence_list = []
        for res in results:
            doc = res.document
            fact = f"Historical incident match: {doc.id} ('{doc.title}') resolved via '{doc.resolution or 'N/A'}' (similarity {res.score:.0%})."
            evidence_list.append(
                CanonicalEvidence(
                    evidence_id=str(uuid4()),
                    incident_id=incident_id,
                    source_tool="semantic_memory",
                    signal_type="historical_match",
                    confidence_weight=min(0.92, max(0.40, res.score)),
                    fact_statement=fact,
                    raw_data=cls.sanitize_payload(doc.model_dump()),
                    is_contradicting=False,
                    provenance=provenance or {"tool": "qdrant_search", "document_id": doc.id, "score": res.score},
                )
            )
        return evidence_list

    # 5. Universal Tool Dispatcher
    @classmethod
    def normalize(
        cls,
        incident_id: str,
        tool_name: str,
        result: Any,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> List[CanonicalEvidence]:
        """Universal dispatcher mapping tool name to specific normalizer."""
        prov = provenance or {"tool": tool_name}

        if tool_name in ("search_logs", "get_service_logs"):
            return cls.normalize_logs_search(incident_id, result, provenance=prov)
        elif tool_name == "get_error_rate":
            return [cls.normalize_error_rate(incident_id, result, provenance=prov)]
        elif tool_name == "get_connection_pool":
            return [cls.normalize_connection_pool(incident_id, result, provenance=prov)]
        elif tool_name == "get_slow_queries":
            return cls.normalize_slow_queries(incident_id, result, provenance=prov)
        elif tool_name in ("get_commit", "get_commit_details"):
            return [cls.normalize_commit_diff(incident_id, result, provenance=prov)]
        elif tool_name == "get_deployment_history":
            return [cls.normalize_deployment_history(incident_id, result, provenance=prov)]
        elif tool_name == "qdrant_search" and isinstance(result, list):
            return cls.normalize_semantic_results(incident_id, result, provenance=prov)
        else:
            # Fallback generic normalizer
            sanitized = cls.sanitize_payload(result)
            return [
                CanonicalEvidence(
                    evidence_id=str(uuid4()),
                    incident_id=incident_id,
                    source_tool=tool_name,
                    signal_type="generic_tool_output",
                    confidence_weight=0.5,
                    fact_statement=f"Observation from {tool_name}: {str(result)[:100]}",
                    raw_data=sanitized,
                    is_contradicting=False,
                    provenance=prov,
                )
            ]

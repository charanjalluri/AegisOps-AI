"""
AegisOps AI - Evidence Normalizer Unit Tests (REASON-01)
Tests conversion of heterogeneous MCP outputs into strongly typed CanonicalEvidence.
"""

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.evidence.normalizer import EvidenceNormalizer
from apps.agent.memory.models import KnowledgeDocument, SearchResult


def test_canonical_evidence_model_and_sanitization():
    raw = {"password": "supersecretpassword", "active": 50, "token": "ghp_1234567890"}
    ev = CanonicalEvidence(
        incident_id="INC-TEST-001",
        source_tool="mcp_database",
        signal_type="pool_exhaustion",
        confidence_weight=0.95,
        fact_statement="Pool exhausted: 50/50 active connections",
        raw_data=EvidenceNormalizer.sanitize_payload(raw),
    )
    assert ev.raw_data["password"] == "[REDACTED]"
    assert ev.raw_data["token"] == "[REDACTED]"
    assert ev.raw_data["active"] == 50
    assert ev.confidence_weight == 0.95


def test_normalize_logs_search_error_and_nominal():
    # Error logs
    raw_error_logs = {
        "logs": [
            {"level": "ERROR", "message": "Connection acquisition timeout after 5000ms"},
            {"level": "INFO", "message": "Handling payment request"},
        ]
    }
    items = EvidenceNormalizer.normalize_logs_search("INC-TEST", raw_error_logs, query_text="timeout")
    assert len(items) == 1
    assert items[0].signal_type == "error_trace"
    assert not items[0].is_contradicting
    assert "timeout" in items[0].fact_statement

    # Nominal logs
    raw_nominal_logs = {
        "logs": [
            {"level": "INFO", "message": "Heartbeat ok"},
            {"level": "INFO", "message": "Payment processed successfully"},
        ]
    }
    items_nom = EvidenceNormalizer.normalize_logs_search("INC-TEST", raw_nominal_logs, query_text="error")
    assert len(items_nom) == 1
    assert items_nom[0].signal_type == "nominal_logs"
    assert items_nom[0].is_contradicting


def test_normalize_error_rate():
    # Spike
    spike_result = {"error_rate": 0.28, "total_logs": 1000, "error_logs": 280, "threshold_exceeded": True}
    ev = EvidenceNormalizer.normalize_error_rate("INC-TEST", spike_result)
    assert ev.signal_type == "error_rate_anomaly"
    assert ev.confidence_weight >= 0.70
    assert not ev.is_contradicting
    assert "28.0%" in ev.fact_statement

    # Nominal
    nom_result = {"error_rate": 0.005, "total_logs": 1000, "error_logs": 5, "threshold_exceeded": False}
    ev_nom = EvidenceNormalizer.normalize_error_rate("INC-TEST", nom_result)
    assert ev_nom.is_contradicting


def test_normalize_connection_pool():
    # Exhausted pool
    exhausted_result = {
        "total_connections": 50,
        "active_connections": 50,
        "idle_connections": 0,
        "waiting_clients": 124,
        "max_connections": 50,
        "utilization_percent": 100.0,
    }
    ev = EvidenceNormalizer.normalize_connection_pool("INC-TEST", exhausted_result)
    assert ev.signal_type == "pool_exhaustion"
    assert ev.confidence_weight == 0.95
    assert not ev.is_contradicting
    assert "50/50" in ev.fact_statement

    # Healthy pool
    healthy_result = {
        "total_connections": 10,
        "active_connections": 8,
        "idle_connections": 2,
        "waiting_clients": 0,
        "max_connections": 50,
        "utilization_percent": 16.0,
    }
    ev_healthy = EvidenceNormalizer.normalize_connection_pool("INC-TEST", healthy_result)
    assert ev_healthy.signal_type == "pool_nominal"
    assert ev_healthy.is_contradicting


def test_normalize_commit_diff_leak_detection():
    # Leaking commit
    leak_commit = {
        "commit_hash": "8f9b2d1c",
        "message": "feat(checkout): optimize payment batching",
        "diff": """
+   conn = pool.acquire()
+   # missing release/close
+   return process(conn)
        """,
    }
    ev = EvidenceNormalizer.normalize_commit_diff("INC-TEST", leak_commit)
    assert ev.signal_type == "code_diff_leak"
    assert ev.confidence_weight == 0.90
    assert not ev.is_contradicting

    # Clean commit
    clean_commit = {
        "commit_hash": "a1b2c3d4",
        "message": "docs: update readme documentation",
        "diff": "+ # Documentation updates",
    }
    ev_clean = EvidenceNormalizer.normalize_commit_diff("INC-TEST", clean_commit)
    assert ev_clean.signal_type == "code_diff_clean"
    assert ev_clean.is_contradicting


def test_normalize_semantic_results():
    doc = KnowledgeDocument(
        id="INC-2025-089",
        service="payment-service",
        title="Payment Service Connection Pool Leak",
        root_cause="Unclosed session in retry loop",
        resolution="Rolled back to v2.7.1",
        text="Historical incident matching connection pool exhaustion.",
    )
    search_res = SearchResult(document=doc, score=0.88)
    ev_list = EvidenceNormalizer.normalize_semantic_results("INC-TEST", [search_res])
    assert len(ev_list) == 1
    assert ev_list[0].signal_type == "historical_match"
    assert ev_list[0].confidence_weight == 0.88
    assert "INC-2025-089" in ev_list[0].fact_statement


def test_universal_normalizer_dispatcher():
    # Dispatch get_connection_pool
    items = EvidenceNormalizer.normalize(
        "INC-TEST",
        "get_connection_pool",
        {"active_connections": 50, "max_connections": 50, "waiting_clients": 10},
    )
    assert len(items) == 1
    assert items[0].signal_type == "pool_exhaustion"

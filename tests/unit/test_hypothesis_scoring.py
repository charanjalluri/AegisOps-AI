"""
AegisOps AI - Multi-Hypothesis Scoring Unit Tests (REASON-03)
Tests competing hypothesis generation, Bayesian calibration, and multi-source corroboration guardrails.
"""

from apps.agent.evidence.models import CanonicalEvidence
from apps.agent.reasoning.hypotheses import HypothesisEngine, HypothesisStatus


def test_hypotheses_initialization():
    engine = HypothesisEngine("INC-TEST-001")
    hypos = engine.get_hypotheses()
    assert len(hypos) == 4
    total_prior = sum(h.confidence_score for h in hypos)
    assert round(total_prior, 2) == 1.00

    titles = [h.title for h in hypos]
    assert any("Connection Pool" in t for t in titles)
    assert any("Infrastructure" in t for t in titles)
    assert any("Traffic Surge" in t for t in titles)
    assert any("Downstream Gateway" in t for t in titles)


def test_single_source_cap_at_70_percent():
    engine = HypothesisEngine("INC-TEST-001")

    # Ingest only logs evidence (1 source tool)
    ev_log = CanonicalEvidence(
        incident_id="INC-TEST-001",
        source_tool="mcp_logs",
        signal_type="error_rate_anomaly",
        confidence_weight=0.95,
        fact_statement="Error rate 35% with database timeout exceptions",
    )
    engine.add_evidence(ev_log)

    winning = engine.get_winning_hypothesis()
    assert winning is not None
    # Because only 1 tool was used, confidence must not exceed 0.70
    assert winning.confidence_score <= 0.70
    assert winning.status == HypothesisStatus.ACTIVE


def test_multi_source_corroboration_exceeds_85_percent():
    engine = HypothesisEngine("INC-TEST-001")

    # 1. Logs evidence
    engine.add_evidence(
        CanonicalEvidence(
            incident_id="INC-TEST-001",
            source_tool="mcp_logs",
            signal_type="error_rate_anomaly",
            confidence_weight=0.90,
            fact_statement="Error rate 28%",
        )
    )

    # 2. Database MCP evidence (2nd independent tool)
    engine.add_evidence(
        CanonicalEvidence(
            incident_id="INC-TEST-001",
            source_tool="mcp_database",
            signal_type="pool_exhaustion",
            confidence_weight=0.95,
            fact_statement="Active connections 50/50, 120 waiting clients",
        )
    )

    # 3. GitHub MCP evidence (3rd independent tool)
    engine.add_evidence(
        CanonicalEvidence(
            incident_id="INC-TEST-001",
            source_tool="mcp_github",
            signal_type="code_diff_leak",
            confidence_weight=0.90,
            fact_statement="Commit 8f9b2d1 introduces unclosed connection checkout",
        )
    )

    winning = engine.get_winning_hypothesis()
    assert winning is not None
    assert "Connection Pool" in winning.title
    assert len(winning.source_tools_used) >= 2
    assert winning.confidence_score >= 0.85
    assert winning.status == HypothesisStatus.VALIDATED

    # Verify probability distribution sums to 1.0
    all_hypos = engine.get_hypotheses()
    total = sum(h.confidence_score for h in all_hypos)
    assert round(total, 2) == 1.00


def test_refuting_evidence_penalizes_hypothesis():
    engine = HypothesisEngine("INC-TEST-001")

    # Ingest evidence refuting connection pool exhaustion
    ev_healthy_pool = CanonicalEvidence(
        incident_id="INC-TEST-001",
        source_tool="mcp_database",
        signal_type="pool_nominal",
        confidence_weight=0.95,
        fact_statement="Connection pool healthy at 5/50 active connections",
        is_contradicting=True,
    )
    engine.add_evidence(ev_healthy_pool)

    hypos = {h.title: h for h in engine.get_hypotheses()}
    pool_hypo = next(h for t, h in hypos.items() if "Connection Pool" in t)
    # Score should drop significantly
    assert pool_hypo.confidence_score < 0.20

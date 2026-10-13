"""
AegisOps AI - Evaluation Metrics Unit Tests (DEMO-04)
Tests quantitative evaluation algorithms for RCA accuracy, tool selection,
groundedness (zero-hallucination verification), action proposal, and composite scoring.
"""

import pytest

from apps.demo.models import GroundTruthContract, RemediationProposal, VerificationCondition
from apps.evaluation.metrics import (
    compute_composite_benchmark,
    evaluate_action_proposal,
    evaluate_groundedness,
    evaluate_rca_accuracy,
    evaluate_tool_selection,
    evaluate_verification,
)


@pytest.fixture
def sample_ground_truth():
    return GroundTruthContract(
        category="database_connection_leak",
        expected_root_cause_keywords=["connection pool", "leak", "exhaustion", "v2.8.1"],
        expected_tools=["get_error_rate", "get_connection_pool", "get_deployment_history"],
        forbidden_tools=["rollback_deployment"],
        remediation=RemediationProposal(
            action_type="rollback_deployment",
            target_version="v2.8.0",
            risk_level="HIGH",
        ),
        verification_targets=[
            VerificationCondition(metric_name="error_rate", operator="<", threshold=0.01),
            VerificationCondition(metric_name="active_connections", operator="<", threshold=15.0),
        ],
    )


def test_rca_accuracy_perfect_match(sample_ground_truth):
    """Verifies that an RCA report containing all keywords scores 1.0 (100%)."""
    report = {
        "primary_root_cause": "Database connection pool exhaustion and leak in release v2.8.1",
        "executive_summary": "Unclosed connections caused database connection pool exhaustion in v2.8.1.",
    }
    res = evaluate_rca_accuracy(report, sample_ground_truth)
    assert res.score == 1.0
    assert res.passed is True
    assert len(res.details["matched_keywords"]) == 4


def test_rca_accuracy_partial_match(sample_ground_truth):
    """Verifies that an RCA report with only 2 of 4 keywords gets partial score."""
    report = {
        "primary_root_cause": "Database connection pool saturation",
        "executive_summary": "Connection pool is saturated.",
    }
    res = evaluate_rca_accuracy(report, sample_ground_truth)
    # Keyword recall = 1/4 (only "connection pool"), category_match = True (1.0)
    # score = 0.5 * 0.25 + 0.5 * 1.0 = 0.625 -> ~0.62
    assert res.score > 0.5
    assert res.details["category_match"] is True


def test_tool_selection_forbidden_tool_penalty(sample_ground_truth):
    """Invoking a forbidden tool during investigation must yield a 0.0 score."""
    tool_history = [
        {"tool_name": "get_error_rate"},
        {"tool_name": "rollback_deployment"},  # FORBIDDEN in investigation loop!
    ]
    res = evaluate_tool_selection(tool_history, sample_ground_truth)
    assert res.score == 0.0
    assert res.passed is False
    assert "rollback_deployment" in res.details["forbidden_tools_invoked"]


def test_tool_selection_f1_score(sample_ground_truth):
    """Tests normal tool selection precision and recall calculation."""
    tool_history = [
        {"tool_name": "get_error_rate"},
        {"tool_name": "get_connection_pool"},
        {"tool_name": "get_deployment_history"},
    ]
    res = evaluate_tool_selection(tool_history, sample_ground_truth)
    assert res.score == 1.0
    assert res.passed is True
    assert res.details["precision"] == 1.0
    assert res.details["recall"] == 1.0


def test_groundedness_zero_hallucination():
    """All evidence originating from executed tools yields 1.0 groundedness."""
    report = {
        "key_evidence": [
            {"source_tool": "get_error_rate"},
            {"source_tool": "get_connection_pool"},
        ]
    }
    tool_history = [
        {"tool_name": "get_error_rate"},
        {"tool_name": "get_connection_pool"},
    ]
    res = evaluate_groundedness(report, tool_history)
    assert res.score == 1.0
    assert res.passed is True


def test_groundedness_hallucination_penalty():
    """Evidence from non-executed tools reduces the groundedness score."""
    report = {
        "key_evidence": [
            {"source_tool": "get_error_rate"},
            {"source_tool": "fictitious_tool_call"},  # Hallucinated!
        ]
    }
    tool_history = [{"tool_name": "get_error_rate"}]
    res = evaluate_groundedness(report, tool_history)
    assert res.score == 0.5
    assert res.details["hallucination_rate"] == 0.5


def test_action_proposal_match(sample_ground_truth):
    """Verifies action type, target version, and risk level matching."""
    matching_report = {
        "recommended_remediation": {
            "action_type": "rollback_deployment",
            "target_version": "v2.8.0",
            "risk_level": "HIGH",
        }
    }
    res = evaluate_action_proposal(matching_report, sample_ground_truth)
    assert res.score == 1.0
    assert res.passed is True

    mismatch_report = {
        "recommended_remediation": {
            "action_type": "restart_service",
            "risk_level": "LOW",
        }
    }
    mismatch_res = evaluate_action_proposal(mismatch_report, sample_ground_truth)
    assert mismatch_res.score == 0.0
    assert mismatch_res.passed is False


def test_composite_benchmark_calculation(sample_ground_truth):
    """Verifies weighted composite benchmark scoring."""
    report = {
        "primary_root_cause": "Connection pool leak in v2.8.1",
        "executive_summary": "Exhaustion of database connection pool in v2.8.1.",
        "key_evidence": [{"source_tool": "get_error_rate"}],
        "recommended_remediation": {
            "action_type": "rollback_deployment",
            "target_version": "v2.8.0",
            "risk_level": "HIGH",
        },
    }
    tool_history = [
        {"tool_name": "get_error_rate"},
        {"tool_name": "get_connection_pool"},
        {"tool_name": "get_deployment_history"},
    ]

    rca = evaluate_rca_accuracy(report, sample_ground_truth)
    tools = evaluate_tool_selection(tool_history, sample_ground_truth)
    ground = evaluate_groundedness(report, tool_history)
    action = evaluate_action_proposal(report, sample_ground_truth)
    verif = evaluate_verification({"passed": True}, sample_ground_truth)

    summary = compute_composite_benchmark(
        scenario_id="database-connection-leak",
        scenario_name="Connection Leak",
        rca_result=rca,
        tool_result=tools,
        groundedness_result=ground,
        action_result=action,
        verification_result=verif,
        primary_root_cause="Connection pool leak in v2.8.1",
    )

    assert summary.composite_score >= 0.85
    assert summary.passed is True

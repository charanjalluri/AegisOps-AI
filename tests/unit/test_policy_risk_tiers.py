"""
AegisOps AI - Action Risk Tiering Unit Tests (GOV-01)
Tests classification of actions into 5 tiers: READ, LOW, MEDIUM, HIGH, and DESTRUCTIVE.
"""

import pytest

from apps.policy.models import PolicyDecision, PolicyEvaluationResult, RiskTier
from apps.policy.risk import RiskClassifier


def test_risk_classifier_read_tools():
    read_tools = [
        "search_logs",
        "get_service_logs",
        "get_error_rate",
        "get_connection_pool",
        "get_slow_queries",
        "get_commit",
        "get_current_version",
        "get_previous_version",
        "qdrant_search",
        "get_incident",
    ]
    for tool in read_tools:
        tier = RiskClassifier.classify(tool)
        assert tier == RiskTier.READ, f"Expected {tool} to be READ, got {tier}"


def test_risk_classifier_low_risk_notifications():
    low_tools = [
        "n8n_notify_slack",
        "n8n_create_jira",
        "send_alert",
        "execute_workflow",
        "notify_channel",
    ]
    for tool in low_tools:
        tier = RiskClassifier.classify(tool)
        assert tier == RiskTier.LOW, f"Expected {tool} to be LOW, got {tier}"


def test_risk_classifier_medium_risk_sandbox_restart():
    # In sandbox or non-prod, restart_service is MEDIUM
    tier_dev = RiskClassifier.classify("restart_service", parameters={"environment": "development"})
    assert tier_dev == RiskTier.MEDIUM

    tier_staging = RiskClassifier.classify("restart_service", environment="staging")
    assert tier_staging == RiskTier.MEDIUM


def test_risk_classifier_high_risk_production_mutations():
    # Rollback is always HIGH
    assert RiskClassifier.classify("rollback_deployment") == RiskTier.HIGH
    assert RiskClassifier.classify("rollback_deployment", {"target_version": "v2.8.0"}) == RiskTier.HIGH

    # Production restart escalates to HIGH
    assert RiskClassifier.classify("restart_service", {"environment": "production"}) == RiskTier.HIGH
    assert RiskClassifier.classify("scale_replicas") == RiskTier.HIGH


def test_risk_classifier_destructive_operations_prohibited():
    destructive_actions = [
        "drop_table",
        "delete_data",
        "truncate_table",
        "delete_database",
        "drop_bucket",
        "drop_schema",
    ]
    for act in destructive_actions:
        tier = RiskClassifier.classify(act)
        assert tier == RiskTier.DESTRUCTIVE, f"Expected {act} to be DESTRUCTIVE, got {tier}"

    # Also detects SQL injection or query parameters containing destructive keywords
    tier_param = RiskClassifier.classify("run_query", parameters={"sql": "DROP TABLE payments;"})
    assert tier_param == RiskTier.DESTRUCTIVE

    tier_del = RiskClassifier.classify("run_query", parameters={"query": "DELETE FROM incidents WHERE 1=1;"})
    assert tier_del == RiskTier.DESTRUCTIVE


def test_policy_models_serialization():
    res = PolicyEvaluationResult(
        action_type="rollback_deployment",
        risk_level=RiskTier.HIGH,
        decision=PolicyDecision.BLOCKED,
        reason="Requires operator approval",
        requires_approval=True,
        proposal_id="PROP-001",
        target_service="payment-service",
    )
    dumped = res.model_dump()
    assert dumped["risk_level"] == "HIGH"
    assert dumped["decision"] == "BLOCKED"
    assert dumped["requires_approval"] is True

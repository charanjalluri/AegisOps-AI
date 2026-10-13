"""
AegisOps AI - Remediation Verifier Unit Tests (GOV-03)
Validates metric condition evaluation, consecutive pass enforcement, and timeout handling.
"""

import pytest

from apps.verification.models import MetricCondition, VerificationResult, VerificationTarget
from apps.verification.verifier import RemediationVerifier


def test_metric_condition_evaluation():
    """Verifies operators <, <=, >, >=, ==, != correctly evaluate boundaries."""
    cond_lt = MetricCondition(metric_name="error_rate", operator="<", threshold=0.01)
    assert cond_lt.evaluate(0.005) is True
    assert cond_lt.evaluate(0.01) is False
    assert cond_lt.evaluate(0.02) is False

    cond_lte = MetricCondition(metric_name="active_connections", operator="<=", threshold=15.0)
    assert cond_lte.evaluate(15.0) is True
    assert cond_lte.evaluate(14.0) is True
    assert cond_lte.evaluate(16.0) is False

    cond_gt = MetricCondition(metric_name="uptime", operator=">", threshold=100.0)
    assert cond_gt.evaluate(105.0) is True
    assert cond_gt.evaluate(100.0) is False

    cond_eq = MetricCondition(metric_name="status_code", operator="==", threshold=200.0)
    assert cond_eq.evaluate(200.0) is True
    assert cond_eq.evaluate(500.0) is False


@pytest.mark.anyio
async def test_remediation_verifier_immediate_recovery():
    """Verifies that when metrics are healthy from cycle 1, verifier confirms recovery quickly."""
    # Collector returning healthy values
    def healthy_collector(service: str, metric_name: str) -> float:
        if metric_name == "error_rate":
            return 0.003  # 0.3% < 1.0%
        if metric_name == "active_connections":
            return 4.0   # 4 < 15
        return 0.0

    verifier = RemediationVerifier(metric_collector=healthy_collector)
    target = VerificationTarget(
        service="payment-service",
        conditions=[
            MetricCondition(metric_name="error_rate", operator="<", threshold=0.01),
            MetricCondition(metric_name="active_connections", operator="<", threshold=15.0),
        ],
        min_consecutive_successes=2,
        poll_interval_sec=0.01,
        timeout_sec=2.0,
    )

    res = await verifier.verify_remediation(target=target, proposal_id="prop-01", incident_id="INC-01")
    assert isinstance(res, VerificationResult)
    assert res.status == "verified"
    assert res.consecutive_passes == 2
    assert len(res.samples) >= 4  # 2 samples per cycle * 2 cycles


@pytest.mark.anyio
async def test_remediation_verifier_delayed_recovery():
    """Verifies that verifier resets streak on failure and succeeds only after consecutive passes."""
    call_counts = {"error_rate": 0}

    def fluctuating_collector(service: str, metric_name: str) -> float:
        if metric_name == "error_rate":
            call_counts["error_rate"] += 1
            # First cycle: fail (1.5%)
            if call_counts["error_rate"] == 1:
                return 0.015
            # Subsequent cycles: pass (0.4%)
            return 0.004
        return 2.0

    verifier = RemediationVerifier(metric_collector=fluctuating_collector)
    target = VerificationTarget(
        service="payment-service",
        conditions=[
            MetricCondition(metric_name="error_rate", operator="<", threshold=0.01),
        ],
        min_consecutive_successes=2,
        poll_interval_sec=0.01,
        timeout_sec=2.0,
    )

    res = await verifier.verify_remediation(target=target, proposal_id="prop-02", incident_id="INC-02")
    assert res.status == "verified"
    assert res.consecutive_passes == 2
    assert call_counts["error_rate"] >= 3  # 1 failure + 2 consecutive passes


@pytest.mark.anyio
async def test_remediation_verifier_timeout_failure():
    """Verifies that persistent degraded metrics trigger bounded timeout failure."""
    def broken_collector(service: str, metric_name: str) -> float:
        return 0.08  # 8.0% error rate, constantly failing

    verifier = RemediationVerifier(metric_collector=broken_collector)
    target = VerificationTarget(
        service="payment-service",
        conditions=[
            MetricCondition(metric_name="error_rate", operator="<", threshold=0.01),
        ],
        min_consecutive_successes=2,
        poll_interval_sec=0.02,
        timeout_sec=0.1,  # Fast timeout for test
    )

    res = await verifier.verify_remediation(target=target, proposal_id="prop-03", incident_id="INC-03")
    assert res.status == "failed"
    assert "timed out" in res.summary
    assert res.consecutive_passes == 0

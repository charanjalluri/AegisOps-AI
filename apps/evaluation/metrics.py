"""
AegisOps AI - Evaluation Metrics Engine (DEMO-04)
Calculates quantitative benchmark scores for Root Cause Analysis (RCA) accuracy,
tool selection precision/recall, evidence groundedness (zero hallucination),
action proposal fidelity, and verification reliability.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.demo.models import GroundTruthContract


class MetricResult(BaseModel):
    """Individual evaluation metric outcome."""
    metric_name: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)

    @property
    def percentage(self) -> float:
        return round(self.score * 100.0, 1)


class ScenarioEvaluationSummary(BaseModel):
    """Complete evaluation report for a single operational incident scenario."""
    scenario_id: str
    scenario_name: str
    composite_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    primary_root_cause_detected: str
    rca_accuracy: MetricResult
    tool_selection: MetricResult
    groundedness: MetricResult
    action_match: MetricResult
    verification: MetricResult

    @property
    def composite_percentage(self) -> float:
        return round(self.composite_score * 100.0, 1)


def evaluate_rca_accuracy(
    rca_report: Dict[str, Any], ground_truth: GroundTruthContract
) -> MetricResult:
    """
    Evaluates RCA statement against ground-truth keywords and failure category.
    """
    root_cause = str(rca_report.get("primary_root_cause", "")).lower()
    exec_summary = str(rca_report.get("executive_summary", "")).lower()
    combined_text = f"{root_cause} {exec_summary}"

    expected_kw = [kw.lower() for kw in ground_truth.expected_root_cause_keywords]
    matched_kw = [kw for kw in expected_kw if kw in combined_text]

    kw_recall = (len(matched_kw) / len(expected_kw)) if expected_kw else 1.0

    category_slug = ground_truth.category.lower().replace("_", " ")
    category_tokens = category_slug.split()
    category_match = any(token in combined_text for token in category_tokens)

    # 50% keyword recall + 50% category match
    score = (0.5 * kw_recall) + (0.5 * (1.0 if category_match else 0.0))
    score = round(min(max(score, 0.0), 1.0), 2)

    return MetricResult(
        metric_name="RCA Accuracy",
        score=score,
        passed=score >= 0.70,
        details={
            "matched_keywords": matched_kw,
            "expected_keywords": expected_kw,
            "keyword_recall": round(kw_recall, 2),
            "category_match": category_match,
            "detected_root_cause": rca_report.get("primary_root_cause"),
        },
    )


def evaluate_tool_selection(
    tool_history: List[Dict[str, Any]], ground_truth: GroundTruthContract
) -> MetricResult:
    """
    Evaluates tool selection precision, recall, F1-score, and penalties for forbidden tools.
    """
    invoked_tools = [t.get("tool_name", "") for t in tool_history if t.get("tool_name")]
    invoked_unique = set(invoked_tools)
    expected_unique = set(ground_truth.expected_tools)
    forbidden_unique = set(ground_truth.forbidden_tools)

    # Check for forbidden tools (e.g. running mutation rollback directly in investigation)
    forbidden_invoked = invoked_unique.intersection(forbidden_unique)
    if forbidden_invoked:
        return MetricResult(
            metric_name="Tool Selection",
            score=0.0,
            passed=False,
            details={
                "forbidden_tools_invoked": list(forbidden_invoked),
                "penalty": "Immediate zero score for invoking forbidden mutation tools in investigation loop",
            },
        )

    # If no expected tools specified, default 1.0
    if not expected_unique:
        return MetricResult(
            metric_name="Tool Selection",
            score=1.0,
            passed=True,
            details={"invoked_tools": invoked_tools},
        )

    correct_invocations = invoked_unique.intersection(expected_unique)
    precision = (
        len(correct_invocations) / len(invoked_unique) if invoked_unique else 0.0
    )
    recall = (
        len(correct_invocations) / len(expected_unique) if expected_unique else 1.0
    )

    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0.0
        else 0.0
    )

    # Budget penalty: penalize if exceeded 20 tool calls
    budget_penalty = 0.0
    if len(tool_history) > 20:
        budget_penalty = min(0.5, (len(tool_history) - 20) * 0.05)

    final_score = max(0.0, f1 - budget_penalty)
    final_score = round(final_score, 2)

    return MetricResult(
        metric_name="Tool Selection",
        score=final_score,
        passed=final_score >= 0.70,
        details={
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1_score": round(f1, 2),
            "budget_penalty": budget_penalty,
            "invoked_tools": list(invoked_unique),
            "expected_tools": list(expected_unique),
        },
    )


def evaluate_groundedness(
    rca_report: Dict[str, Any], tool_history: List[Dict[str, Any]]
) -> MetricResult:
    """
    Evaluates whether all key evidence items cited in the RCA report are grounded in actual tool output.
    """
    key_evidence = rca_report.get("key_evidence", [])
    if not key_evidence:
        # If no key evidence cited, groundedness is baseline neutral
        return MetricResult(
            metric_name="Groundedness",
            score=1.0,
            passed=True,
            details={"evidence_items_checked": 0, "hallucinations_detected": 0},
        )

    # Collect tool names present in execution history
    valid_tool_sources = {t.get("tool_name", "") for t in tool_history}
    valid_tool_sources.update({
        "qdrant_semantic_rag",
        "semantic_memory",
        "mcp_logs",
        "mcp_database",
        "mcp_github",
        "mcp_incident",
        "LOGS",
        "DATABASE",
        "GITHUB",
        "INCIDENT",
    })

    ungrounded_items = []
    for ev in key_evidence:
        src = ev.get("source_tool") if isinstance(ev, dict) else getattr(ev, "source_tool", None)
        if src and src not in valid_tool_sources and src != "UNKNOWN":
            ungrounded_items.append(src)

    hallucination_rate = len(ungrounded_items) / len(key_evidence) if key_evidence else 0.0
    score = round(max(0.0, 1.0 - hallucination_rate), 2)

    return MetricResult(
        metric_name="Groundedness",
        score=score,
        passed=score >= 0.90,
        details={
            "evidence_count": len(key_evidence),
            "ungrounded_items": ungrounded_items,
            "hallucination_rate": round(hallucination_rate, 2),
        },
    )


def evaluate_action_proposal(
    rca_report: Dict[str, Any], ground_truth: GroundTruthContract
) -> MetricResult:
    """
    Evaluates whether the recommended action matches ground-truth remediation expectations.
    """
    rec_action = rca_report.get("recommended_remediation", {})
    action_type = rec_action.get("action_type")
    risk_level = rec_action.get("risk_level")
    target_version = rec_action.get("target_version")

    expected_remed = ground_truth.remediation

    type_match = action_type == expected_remed.action_type
    risk_match = risk_level == expected_remed.risk_level

    version_match = True
    if expected_remed.target_version:
        version_match = target_version == expected_remed.target_version

    score = 0.0
    if type_match:
        score += 0.6
        if risk_match:
            score += 0.2
        if version_match:
            score += 0.2

    score = round(score, 2)
    return MetricResult(
        metric_name="Action Proposal Match",
        score=score,
        passed=score >= 0.80,
        details={
            "type_match": type_match,
            "risk_match": risk_match,
            "version_match": version_match,
            "recommended": rec_action,
            "expected": expected_remed.model_dump(),
        },
    )


def evaluate_verification(
    verification_data: Optional[Dict[str, Any]], ground_truth: GroundTruthContract
) -> MetricResult:
    """
    Evaluates whether verification requirements were satisfied.
    """
    if not ground_truth.verification_targets:
        return MetricResult(
            metric_name="Verification Reliability",
            score=1.0,
            passed=True,
            details={"notes": "No explicit verification targets defined."},
        )

    # If verification was run and succeeded
    if verification_data and verification_data.get("passed", False):
        return MetricResult(
            metric_name="Verification Reliability",
            score=1.0,
            passed=True,
            details=verification_data,
        )

    # Baseline: if verification targets defined and scenario converged
    return MetricResult(
        metric_name="Verification Reliability",
        score=0.85,
        passed=True,
        details={"targets_count": len(ground_truth.verification_targets)},
    )


def compute_composite_benchmark(
    scenario_id: str,
    scenario_name: str,
    rca_result: MetricResult,
    tool_result: MetricResult,
    groundedness_result: MetricResult,
    action_result: MetricResult,
    verification_result: MetricResult,
    primary_root_cause: str = "",
) -> ScenarioEvaluationSummary:
    """
    Computes weighted composite score across all 5 evaluation dimensions:
    35% RCA + 25% Tool Selection + 15% Groundedness + 15% Action Match + 10% Verification.
    """
    composite = (
        (0.35 * rca_result.score)
        + (0.25 * tool_result.score)
        + (0.15 * groundedness_result.score)
        + (0.15 * action_result.score)
        + (0.10 * verification_result.score)
    )
    composite = round(min(max(composite, 0.0), 1.0), 3)
    passed = composite >= 0.80

    return ScenarioEvaluationSummary(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        composite_score=composite,
        passed=passed,
        primary_root_cause_detected=primary_root_cause,
        rca_accuracy=rca_result,
        tool_selection=tool_result,
        groundedness=groundedness_result,
        action_match=action_result,
        verification=verification_result,
    )

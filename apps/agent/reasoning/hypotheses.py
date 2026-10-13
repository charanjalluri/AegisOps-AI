"""
AegisOps AI - Multi-Hypothesis Confidence Scoring Engine (REASON-03)
Formulates competing diagnostic hypotheses, distinguishes facts/hypotheses/assumptions,
calculates Bayesian calibrated confidence scores, and prevents single-source overconfidence.
"""

from enum import Enum
import math
from typing import Dict, List, Optional, Set
from uuid import uuid4
from pydantic import BaseModel, Field

from apps.agent.evidence.models import CanonicalEvidence


class HypothesisStatus(str, Enum):
    ACTIVE = "active"
    VALIDATED = "validated"
    REFUTED = "refuted"


class EvaluatedHypothesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    prior_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.25, ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    refuting_evidence_ids: List[str] = Field(default_factory=list)
    source_tools_used: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None


class HypothesisEngine:
    """
    Manages competing hypotheses and calibrated confidence scoring.
    Enforces Bayesian normalization and multi-source corroboration constraints.
    """

    DEFAULT_HYPOTHESES = [
        (
            "H1: Database Connection Pool Exhaustion (Code Release / Leak)",
            "Recent service deployment introduced an unclosed database connection leak exhausting connection pool capacity.",
            0.40,
        ),
        (
            "H2: Database Infrastructure Degradation or Resource Starvation",
            "Underlying database server hardware, disk I/O, or OS lock contention degraded query processing throughput.",
            0.25,
        ),
        (
            "H3: Organic High Traffic Surge / Transaction Volume Spike",
            "An unexpected burst in legitimate user traffic saturated nominal capacity without software defect.",
            0.20,
        ),
        (
            "H4: Downstream Gateway / Third-Party Payment Provider Outage",
            "External payment gateway timeouts or rate limits caused request queues to back up locally.",
            0.15,
        ),
    ]

    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        self.hypotheses: Dict[str, EvaluatedHypothesis] = {}
        self.evidence_history: List[CanonicalEvidence] = []
        self.assumptions: List[str] = [
            "Network connectivity between microservices is functional unless gateway errors prove otherwise.",
            "Database server is operational unless connection refused errors are detected.",
        ]
        self._initialize_default_hypotheses()

    def _initialize_default_hypotheses(self):
        for title, rationale, prior in self.DEFAULT_HYPOTHESES:
            hypo_id = str(uuid4())
            self.hypotheses[hypo_id] = EvaluatedHypothesis(
                id=hypo_id,
                title=title,
                status=HypothesisStatus.ACTIVE,
                prior_probability=prior,
                confidence_score=prior,
                rationale=rationale,
            )

    def get_hypotheses(self) -> List[EvaluatedHypothesis]:
        # Return sorted descending by confidence score
        return sorted(self.hypotheses.values(), key=lambda h: h.confidence_score, reverse=True)

    def get_winning_hypothesis(self) -> Optional[EvaluatedHypothesis]:
        hypos = self.get_hypotheses()
        return hypos[0] if hypos else None

    def add_evidence(self, evidence: CanonicalEvidence):
        """
        Ingests a CanonicalEvidence item, maps signals to candidate hypotheses,
        updates likelihoods, and normalizes confidence distribution.
        """
        self.evidence_history.append(evidence)
        ev_id = evidence.evidence_id
        sig = evidence.signal_type
        weight = evidence.confidence_weight
        src_tool = evidence.source_tool

        for h in self.hypotheses.values():
            if h.status == HypothesisStatus.REFUTED:
                continue

            is_supporting = False
            is_refuting = False

            # Signal matching logic
            if "Connection Pool Exhaustion" in h.title:
                if sig in ("pool_exhaustion", "code_diff_leak", "error_rate_anomaly"):
                    is_supporting = True
                elif sig in ("pool_nominal", "nominal_logs"):
                    is_refuting = True
                elif sig == "historical_match" and "pool" in evidence.fact_statement.lower():
                    is_supporting = True

            elif "Infrastructure Degradation" in h.title:
                if sig in ("slow_queries", "cpu_saturation"):
                    is_supporting = True
                elif sig in ("pool_exhaustion", "code_diff_leak"):
                    # Contradicts purely infra degradation because code leak specifically explains it
                    is_refuting = True

            elif "Traffic Surge" in h.title:
                if sig == "traffic_spike":
                    is_supporting = True
                elif sig in ("pool_exhaustion", "code_diff_leak"):
                    is_refuting = True

            elif "Downstream Gateway" in h.title:
                if sig in ("gateway_timeout", "upstream_429"):
                    is_supporting = True
                elif sig in ("pool_exhaustion", "code_diff_leak"):
                    is_refuting = True

            # Register evidence link
            if is_supporting and ev_id not in h.supporting_evidence_ids:
                h.supporting_evidence_ids.append(ev_id)
                if src_tool not in h.source_tools_used:
                    h.source_tools_used.append(src_tool)
            elif is_refuting and ev_id not in h.refuting_evidence_ids:
                h.refuting_evidence_ids.append(ev_id)

        # Recalculate and calibrate scores
        self._recalculate_confidence_scores()

    def _recalculate_confidence_scores(self):
        """
        Bayesian updating with overconfidence prevention guardrails:
        1. Posterior proportional to prior * prod(likelihoods)
        2. Normalize active hypotheses sum to 1.0
        3. Single-source ceiling: max 0.70 confidence if only 1 source tool corroborates.
        4. Corroboration requirement: requires >= 2 distinct source tools to exceed 0.85 confidence.
        """
        unnormalized: Dict[str, float] = {}

        for h_id, h in self.hypotheses.items():
            if h.status == HypothesisStatus.REFUTED:
                unnormalized[h_id] = 0.01
                continue

            score = h.prior_probability

            # Positive evidence boost
            for ev_id in h.supporting_evidence_ids:
                ev = next((e for e in self.evidence_history if e.evidence_id == ev_id), None)
                if ev:
                    # Multiplicative likelihood factor > 1
                    score *= 1.0 + (ev.confidence_weight * 2.5)

            # Refuting evidence penalty
            for ev_id in h.refuting_evidence_ids:
                ev = next((e for e in self.evidence_history if e.evidence_id == ev_id), None)
                if ev:
                    # Strong dampening factor
                    score *= max(0.05, 1.0 - (ev.confidence_weight * 0.9))

            unnormalized[h_id] = score

        # Normalize sum of active hypotheses
        total_score = sum(unnormalized.values())
        if total_score > 0:
            for h_id in unnormalized:
                unnormalized[h_id] /= total_score

        # Apply calibration guardrails
        for h_id, h in self.hypotheses.items():
            norm_score = unnormalized[h_id]
            tools_count = len(h.source_tools_used)

            # Guardrail 1: Single source cap at 0.70
            if tools_count <= 1 and norm_score > 0.70:
                norm_score = 0.70

            # Guardrail 2: Multi-source corroboration required for > 0.85
            if tools_count < 2 and norm_score > 0.85:
                norm_score = 0.80

            # Transition status
            if norm_score >= 0.85 and tools_count >= 2:
                h.status = HypothesisStatus.VALIDATED
            elif norm_score <= 0.05 and h.refuting_evidence_ids:
                h.status = HypothesisStatus.REFUTED
            else:
                h.status = HypothesisStatus.ACTIVE

            h.confidence_score = round(norm_score, 4)

        # Final re-normalization to guarantee sum is approximately 1.0
        final_total = sum(h.confidence_score for h in self.hypotheses.values())
        if final_total > 0:
            for h in self.hypotheses.values():
                h.confidence_score = round(h.confidence_score / final_total, 4)

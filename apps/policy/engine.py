"""
AegisOps AI - Policy Evaluation Engine (GOV-01, GOV-02)
Evaluates operational actions against risk classification, enforces mandatory HITL approval
for HIGH-risk mutations, and completely rejects DESTRUCTIVE commands.
"""

from typing import Any, Dict, List, Optional
from apps.mcp_incident.models import ActionProposalItem
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.models import PolicyDecision, PolicyEvaluationResult, RiskTier
from apps.policy.risk import RiskClassifier


class PolicyEngine:
    """
    Central safety policy enforcement gate.
    """

    def __init__(self, storage: Optional[InvestigationStorage] = None):
        self.storage = storage or InvestigationStorage()

    async def evaluate_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        proposal_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        environment: str = "production",
    ) -> PolicyEvaluationResult:
        """
        Evaluates whether an action is permitted, blocked pending approval, or rejected.
        """
        params = parameters or {}
        risk_level = RiskClassifier.classify(action_type, parameters=params, environment=environment)
        target_service = params.get("service")

        # 1. DESTRUCTIVE: Permanent rejection
        if risk_level == RiskTier.DESTRUCTIVE:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.DESTRUCTIVE,
                decision=PolicyDecision.REJECTED,
                reason="Operation is permanently prohibited by safety policy.",
                requires_approval=False,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # 2. READ: Automatic permission
        if risk_level == RiskTier.READ:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.READ,
                decision=PolicyDecision.ALLOWED,
                reason="Read-only diagnostic inspection is automatically permitted.",
                requires_approval=False,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # 3. LOW: Automatic permission with audit logging
        if risk_level == RiskTier.LOW:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.LOW,
                decision=PolicyDecision.ALLOWED,
                reason="Low-risk external notification or trigger is automatically permitted.",
                requires_approval=False,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # 4. MEDIUM: Permitted in non-production environments
        if risk_level == RiskTier.MEDIUM:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.MEDIUM,
                decision=PolicyDecision.ALLOWED,
                reason="Medium-risk operation permitted with audit tracking.",
                requires_approval=False,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # 5. HIGH: Strict Human-in-the-Loop approval gate (GOV-02)
        if not proposal_id:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.HIGH,
                decision=PolicyDecision.BLOCKED,
                reason="HIGH-risk action requires a formal action proposal and verified operator approval.",
                requires_approval=True,
                proposal_id=None,
                target_service=target_service,
                parameters=params,
            )

        # Locate proposal in storage
        proposal = await self._find_proposal(proposal_id=proposal_id, incident_id=incident_id)
        if not proposal:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.HIGH,
                decision=PolicyDecision.BLOCKED,
                reason=f"Action proposal '{proposal_id}' was not found in short-term storage.",
                requires_approval=True,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # Check approval state and operator credentials
        if proposal.status != "approved" or not proposal.approved_by:
            return PolicyEvaluationResult(
                action_type=action_type,
                risk_level=RiskTier.HIGH,
                decision=PolicyDecision.BLOCKED,
                reason="Action requires verified human approval before execution.",
                requires_approval=True,
                proposal_id=proposal_id,
                target_service=target_service,
                parameters=params,
            )

        # Proposal is verified and approved!
        return PolicyEvaluationResult(
            action_type=action_type,
            risk_level=RiskTier.HIGH,
            decision=PolicyDecision.ALLOWED,
            reason=f"Action approved by operator '{proposal.approved_by}'.",
            requires_approval=False,
            proposal_id=proposal_id,
            target_service=target_service,
            parameters=params,
        )

    async def validate_execution_allowed(
        self,
        proposal_id: str,
        incident_id: Optional[str] = None,
        action_type: str = "rollback_deployment",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Validates that proposal is authorized to execute.
        Raises ValueError (with POLICY_VIOLATION details) if not allowed.
        """
        result = await self.evaluate_action(
            action_type=action_type,
            parameters=parameters,
            proposal_id=proposal_id,
            incident_id=incident_id,
        )
        if result.decision != PolicyDecision.ALLOWED:
            raise ValueError(f"Policy violation: action rejected. {result.reason}")
        return True

    async def _find_proposal(
        self, proposal_id: str, incident_id: Optional[str] = None
    ) -> Optional[ActionProposalItem]:
        """Looks up proposal in storage across incident proposals."""
        if incident_id:
            props = await self.storage.get_action_proposals(incident_id)
            for p in props:
                if str(p.id) == str(proposal_id):
                    return p
            return None

        # If incident_id not provided, search in-memory or database
        if not self.storage.pool:
            for inc_id, props in self.storage._proposals.items():
                for p in props:
                    if str(p.id) == str(proposal_id):
                        return p
            return None

        async with self.storage.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id::text, incident_id, action_type, parameters,
                       risk_level, status, rationale, created_at::text,
                       approved_by, executed_at::text
                FROM action_proposals
                WHERE id = $1;
                """,
                proposal_id,
            )
            if not row:
                return None
            import json
            return ActionProposalItem(
                id=row["id"],
                incident_id=row["incident_id"],
                action_type=row["action_type"],
                parameters=json.loads(row["parameters"]) if isinstance(row["parameters"], str) else row["parameters"],
                risk_level=row["risk_level"],
                status=row["status"],
                rationale=row["rationale"],
                created_at=row["created_at"],
                approved_by=row["approved_by"],
                executed_at=row["executed_at"],
            )

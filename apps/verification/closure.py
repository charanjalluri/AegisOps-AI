"""
AegisOps AI - Incident Closure Pipeline (GOV-03, GOV-04)
Orchestrates closed-loop verification, proposal lifecycle transitions, incident closure,
audit trail logging, and n8n notification dispatch.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from apps.mcp_incident.storage import InvestigationStorage
from apps.mcp_n8n.tools import N8nTools
from apps.policy.approval import ApprovalManager
from apps.policy.audit import GovernanceAuditLogger
from apps.policy.models import RiskTier
from apps.verification.models import ClosureResult, VerificationTarget
from apps.verification.verifier import RemediationVerifier

logger = logging.getLogger("aegisops.verification.closure")


class IncidentClosurePipeline:
    """
    Automated governance pipeline that executes closed-loop metric verification
    prior to safely marking an operational incident resolved.
    """

    def __init__(
        self,
        verifier: Optional[RemediationVerifier] = None,
        storage: Optional[InvestigationStorage] = None,
        approval_manager: Optional[ApprovalManager] = None,
        audit_logger: Optional[GovernanceAuditLogger] = None,
        n8n_tools: Optional[N8nTools] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.verifier = verifier or RemediationVerifier()
        self.storage = storage or InvestigationStorage()
        self.approval_manager = approval_manager or ApprovalManager(
            storage=self.storage, event_emitter=event_emitter
        )
        self.audit = audit_logger or GovernanceAuditLogger(storage=self.storage)
        self.n8n_tools = n8n_tools or N8nTools(force_mock=True)
        self.event_emitter = event_emitter

    async def execute_verification_and_close(
        self,
        incident_id: str,
        proposal_id: str,
        root_cause: str,
        winning_hypothesis_id: Optional[str] = None,
        target: Optional[VerificationTarget] = None,
    ) -> ClosureResult:
        """
        Executes telemetry verification loop and transitions incident to resolved (or escalated).
        """
        # 1. Run closed-loop telemetry polling
        verif_result = await self.verifier.verify_remediation(
            target=target,
            proposal_id=proposal_id,
            incident_id=incident_id,
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        # 2. Happy Path: Verification Successful
        if verif_result.status == "verified":
            # Transition proposal to 'verified'
            try:
                await self.approval_manager.mark_proposal_verified(
                    proposal_id=proposal_id,
                    incident_id=incident_id,
                    details={"verification_summary": verif_result.summary},
                )
            except Exception as e:
                logger.warning(f"Failed to update proposal verification state: {e}")

            # Close incident in storage
            inc_detail = await self.storage.close_incident(
                incident_id=incident_id,
                root_cause=root_cause,
                winning_hypothesis_id=winning_hypothesis_id,
                summary=verif_result.summary,
            )

            # Record durable governance audit entry
            audit_entry = await self.audit.log_event(
                event_type="INCIDENT_CLOSED_VERIFIED",
                action_type="close_incident",
                risk_level=RiskTier.LOW,
                decision="RESOLVED",
                operator_id="system-verifier",
                proposal_id=proposal_id,
                incident_id=incident_id,
                details={
                    "root_cause": root_cause,
                    "winning_hypothesis_id": winning_hypothesis_id,
                    "summary": verif_result.summary,
                    "duration_sec": verif_result.duration_sec,
                },
            )

            # Emit Kafka incidents.updated event
            if self.event_emitter:
                evt = {
                    "event_id": str(uuid4()),
                    "incident_id": incident_id,
                    "status": "resolved",
                    "root_cause": root_cause,
                    "winning_hypothesis_id": winning_hypothesis_id,
                    "summary": verif_result.summary,
                    "resolved_at": inc_detail.resolved_at or now_iso,
                }
                res = self.event_emitter("incidents.updated", evt)
                if hasattr(res, "__await__"):
                    await res

            # Dispatch external notification via n8n
            await self.n8n_tools.execute_workflow(
                workflow_name="incident-resolution-alert",
                payload={
                    "incident_id": incident_id,
                    "status": "resolved",
                    "root_cause": root_cause,
                    "winning_hypothesis_id": winning_hypothesis_id,
                    "verification_summary": verif_result.summary,
                },
            )

            return ClosureResult(
                incident_id=incident_id,
                status="resolved",
                root_cause=root_cause,
                winning_hypothesis_id=winning_hypothesis_id,
                resolved_at=inc_detail.resolved_at or now_iso,
                audit_id=audit_entry.audit_id,
                summary=verif_result.summary,
            )

        # 3. Failure Path: Verification Timed Out or Metrics Remained Degraded
        else:
            # Transition proposal to 'failed'
            try:
                await self.approval_manager.mark_proposal_failed(
                    proposal_id=proposal_id,
                    incident_id=incident_id,
                    details={"failure_summary": verif_result.summary},
                )
            except Exception as e:
                logger.warning(f"Failed to update proposal failed state: {e}")

            # Escalate incident in storage
            await self.storage.update_incident(
                incident_id=incident_id,
                status="escalated",
                summary=f"Remediation verification failed: {verif_result.summary}",
            )

            # Record durable governance audit entry
            audit_entry = await self.audit.log_event(
                event_type="REMEDIATION_VERIFICATION_FAILED",
                action_type="escalate_incident",
                risk_level=RiskTier.HIGH,
                decision="ESCALATED",
                operator_id="system-verifier",
                proposal_id=proposal_id,
                incident_id=incident_id,
                details={
                    "root_cause": root_cause,
                    "summary": verif_result.summary,
                    "duration_sec": verif_result.duration_sec,
                },
            )

            # Emit Kafka incidents.updated event
            if self.event_emitter:
                evt = {
                    "event_id": str(uuid4()),
                    "incident_id": incident_id,
                    "status": "escalated",
                    "summary": verif_result.summary,
                    "timestamp": now_iso,
                }
                res = self.event_emitter("incidents.updated", evt)
                if hasattr(res, "__await__"):
                    await res

            # Dispatch external escalation notification via n8n
            await self.n8n_tools.execute_workflow(
                workflow_name="incident-escalation-alert",
                payload={
                    "incident_id": incident_id,
                    "status": "escalated",
                    "reason": verif_result.summary,
                },
            )

            return ClosureResult(
                incident_id=incident_id,
                status="escalated",
                root_cause=root_cause,
                winning_hypothesis_id=winning_hypothesis_id,
                resolved_at=None,
                audit_id=audit_entry.audit_id,
                summary=verif_result.summary,
            )

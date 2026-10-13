"""
AegisOps AI - Human-in-the-Loop Approval Manager (GOV-02)
Manages the lifecycle state machine for action proposals, verifies human operator authorization,
emits ai.actions Kafka events, and invokes governance audit logging.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from apps.mcp_incident.models import ActionProposalItem
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.audit import GovernanceAuditLogger
from apps.policy.models import RiskTier


class ApprovalManager:
    """
    Manages operator review, approval, and rejection of action proposals.
    """

    def __init__(
        self,
        storage: Optional[InvestigationStorage] = None,
        audit_logger: Optional[GovernanceAuditLogger] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.storage = storage or InvestigationStorage()
        self.audit = audit_logger or GovernanceAuditLogger(storage=self.storage)
        self.event_emitter = event_emitter

    async def approve_proposal(
        self,
        proposal_id: str,
        operator_id: str,
        comment: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> ActionProposalItem:
        """
        Approves an action proposal, transitioning it from 'proposed' to 'approved'.
        Mandates non-empty operator_id.
        """
        if not operator_id or not operator_id.strip():
            raise ValueError("Operator ID must be a non-empty string for accountability.")

        proposal = await self._find_proposal(proposal_id, incident_id=incident_id)
        if not proposal:
            raise ValueError(f"Action proposal '{proposal_id}' does not exist.")

        if proposal.status != "proposed":
            raise ValueError(
                f"Cannot approve proposal '{proposal_id}' with status '{proposal.status}'. Must be 'proposed'."
            )

        # Update in-memory / storage proposal
        proposal.status = "approved"
        proposal.approved_by = operator_id.strip()

        # Update PostgreSQL if connected
        if self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE action_proposals
                    SET status = 'approved', approved_by = $2
                    WHERE id = $1;
                    """,
                    proposal_id,
                    operator_id.strip(),
                )

        # Audit log entry
        await self.audit.log_event(
            event_type="PROPOSAL_APPROVED",
            action_type=proposal.action_type,
            risk_level=RiskTier(proposal.risk_level),
            decision="APPROVED",
            operator_id=operator_id.strip(),
            proposal_id=proposal_id,
            incident_id=proposal.incident_id,
            target_service=proposal.parameters.get("service"),
            details={"comment": comment, "parameters": proposal.parameters},
        )

        # Emit Kafka ai.actions event
        if self.event_emitter:
            event_payload = {
                "event_id": str(uuid4()),
                "incident_id": proposal.incident_id,
                "proposal_id": proposal_id,
                "action_type": proposal.action_type,
                "risk_level": proposal.risk_level,
                "status": "approved",
                "operator_id": operator_id.strip(),
                "comment": comment,
            }
            res = self.event_emitter("ai.actions", event_payload)
            if hasattr(res, "__await__"):
                await res

        return proposal

    async def reject_proposal(
        self,
        proposal_id: str,
        operator_id: str,
        reason: str,
        incident_id: Optional[str] = None,
    ) -> ActionProposalItem:
        """
        Rejects an action proposal with mandatory explanation.
        """
        if not operator_id or not operator_id.strip():
            raise ValueError("Operator ID must be a non-empty string.")
        if not reason or not reason.strip():
            raise ValueError("Rejection reason must be provided.")

        proposal = await self._find_proposal(proposal_id, incident_id=incident_id)
        if not proposal:
            raise ValueError(f"Action proposal '{proposal_id}' does not exist.")

        if proposal.status != "proposed":
            raise ValueError(
                f"Cannot reject proposal '{proposal_id}' with status '{proposal.status}'. Must be 'proposed'."
            )

        proposal.status = "rejected"

        if self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE action_proposals
                    SET status = 'rejected'
                    WHERE id = $1;
                    """,
                    proposal_id,
                )

        await self.audit.log_event(
            event_type="PROPOSAL_REJECTED",
            action_type=proposal.action_type,
            risk_level=RiskTier(proposal.risk_level),
            decision="REJECTED",
            operator_id=operator_id.strip(),
            proposal_id=proposal_id,
            incident_id=proposal.incident_id,
            target_service=proposal.parameters.get("service"),
            details={"reason": reason},
        )

        if self.event_emitter:
            event_payload = {
                "event_id": str(uuid4()),
                "incident_id": proposal.incident_id,
                "proposal_id": proposal_id,
                "action_type": proposal.action_type,
                "risk_level": proposal.risk_level,
                "status": "rejected",
                "operator_id": operator_id.strip(),
                "reason": reason,
            }
            res = self.event_emitter("ai.actions", event_payload)
            if hasattr(res, "__await__"):
                await res

        return proposal

    async def mark_proposal_executed(
        self,
        proposal_id: str,
        incident_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ActionProposalItem:
        """
        Marks an approved proposal as 'executed', records timestamp and audit entry,
        and emits an 'ai.actions' Kafka event.
        """
        proposal = await self._find_proposal(proposal_id, incident_id=incident_id)
        if not proposal:
            raise ValueError(f"Action proposal '{proposal_id}' does not exist.")

        now_iso = datetime.now(timezone.utc).isoformat()
        proposal.status = "executed"
        proposal.executed_at = now_iso

        if self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE action_proposals
                    SET status = 'executed', executed_at = NOW()
                    WHERE id = $1;
                    """,
                    proposal_id,
                )

        await self.audit.log_event(
            event_type="PROPOSAL_EXECUTED",
            action_type=proposal.action_type,
            risk_level=RiskTier(proposal.risk_level),
            decision="EXECUTED",
            operator_id=operator_id or proposal.approved_by or "system",
            proposal_id=proposal_id,
            incident_id=proposal.incident_id,
            target_service=proposal.parameters.get("service"),
            details=details or {},
        )

        if self.event_emitter:
            event_payload = {
                "event_id": str(uuid4()),
                "incident_id": proposal.incident_id,
                "proposal_id": proposal_id,
                "action_type": proposal.action_type,
                "risk_level": proposal.risk_level,
                "status": "executed",
                "operator_id": operator_id or proposal.approved_by,
                "executed_at": now_iso,
            }
            res = self.event_emitter("ai.actions", event_payload)
            if hasattr(res, "__await__"):
                await res

        return proposal

    async def mark_proposal_verified(
        self,
        proposal_id: str,
        incident_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ActionProposalItem:
        """
        Marks an executed proposal as 'verified' after post-remediation telemetry confirms recovery.
        """
        proposal = await self._find_proposal(proposal_id, incident_id=incident_id)
        if not proposal:
            raise ValueError(f"Action proposal '{proposal_id}' does not exist.")

        proposal.status = "verified"

        if self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE action_proposals
                    SET status = 'verified'
                    WHERE id = $1;
                    """,
                    proposal_id,
                )

        await self.audit.log_event(
            event_type="PROPOSAL_VERIFIED",
            action_type=proposal.action_type,
            risk_level=RiskTier(proposal.risk_level),
            decision="VERIFIED",
            operator_id=proposal.approved_by or "system",
            proposal_id=proposal_id,
            incident_id=proposal.incident_id,
            target_service=proposal.parameters.get("service"),
            details=details or {},
        )

        return proposal

    async def mark_proposal_failed(
        self,
        proposal_id: str,
        incident_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> ActionProposalItem:
        """
        Marks an executed proposal as 'failed' if post-remediation verification times out or metrics fail.
        """
        proposal = await self._find_proposal(proposal_id, incident_id=incident_id)
        if not proposal:
            raise ValueError(f"Action proposal '{proposal_id}' does not exist.")

        proposal.status = "failed"

        if self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE action_proposals
                    SET status = 'failed'
                    WHERE id = $1;
                    """,
                    proposal_id,
                )

        await self.audit.log_event(
            event_type="PROPOSAL_FAILED",
            action_type=proposal.action_type,
            risk_level=RiskTier(proposal.risk_level),
            decision="FAILED",
            operator_id=proposal.approved_by or "system",
            proposal_id=proposal_id,
            incident_id=proposal.incident_id,
            target_service=proposal.parameters.get("service"),
            details=details or {},
        )

        return proposal

    async def list_pending_proposals(
        self, incident_id: Optional[str] = None
    ) -> List[ActionProposalItem]:
        """Lists all pending proposals requiring human review."""
        proposals: List[ActionProposalItem] = []
        if incident_id:
            props = await self.storage.get_action_proposals(incident_id)
            proposals.extend(props)
        else:
            if not self.storage.pool:
                for props in self.storage._proposals.values():
                    proposals.extend(props)
            else:
                async with self.storage.pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id::text, incident_id, action_type, parameters,
                               risk_level, status, rationale, created_at::text,
                               approved_by, executed_at::text
                        FROM action_proposals
                        WHERE status = 'proposed'
                        ORDER BY created_at ASC;
                        """
                    )
                    import json
                    for r in rows:
                        proposals.append(
                            ActionProposalItem(
                                id=r["id"],
                                incident_id=r["incident_id"],
                                action_type=r["action_type"],
                                parameters=json.loads(r["parameters"]) if isinstance(r["parameters"], str) else r["parameters"],
                                risk_level=r["risk_level"],
                                status=r["status"],
                                rationale=r["rationale"],
                                created_at=r["created_at"],
                                approved_by=r["approved_by"],
                                executed_at=r["executed_at"],
                            )
                        )

        return [p for p in proposals if p.status == "proposed"]

    async def _find_proposal(
        self, proposal_id: str, incident_id: Optional[str] = None
    ) -> Optional[ActionProposalItem]:
        if incident_id:
            props = await self.storage.get_action_proposals(incident_id)
            for p in props:
                if str(p.id) == str(proposal_id):
                    return p
            return None

        if not self.storage.pool:
            for props in self.storage._proposals.values():
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

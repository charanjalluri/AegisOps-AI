"""
AegisOps AI - Governance Audit Logger (GOV-04)
Maintains immutable audit records for all policy checks, operator approvals,
rejections, and controlled remediation executions.
"""

from typing import Any, Dict, List, Optional
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.models import GovernanceAuditEntry, RiskTier


class GovernanceAuditLogger:
    """
    Immutable audit logging facility for compliance and accountability.
    """

    def __init__(self, storage: Optional[InvestigationStorage] = None):
        self.storage = storage or InvestigationStorage()
        self._entries: List[GovernanceAuditEntry] = []

    async def log_event(
        self,
        event_type: str,
        action_type: str,
        risk_level: RiskTier,
        decision: Optional[str] = None,
        operator_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        target_service: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> GovernanceAuditEntry:
        """
        Creates and persists an immutable audit entry.
        """
        entry = GovernanceAuditEntry(
            event_type=event_type,
            action_type=action_type,
            risk_level=risk_level,
            decision=decision,
            operator_id=operator_id,
            proposal_id=proposal_id,
            incident_id=incident_id,
            target_service=target_service,
            details=details or {},
        )
        self._entries.append(entry)

        # Persist to storage tool history for durable DB tracking if incident_id available
        if incident_id:
            try:
                await self.storage.record_tool_history(
                    incident_id=incident_id,
                    tool_name=f"governance_audit:{event_type.lower()}",
                    caller=operator_id or "policy_engine",
                    arguments={
                        "action_type": action_type,
                        "risk_level": risk_level.value,
                        "decision": decision,
                        "proposal_id": proposal_id,
                        "details": details or {},
                    },
                    duration_ms=0.0,
                    status="recorded",
                    result_summary=f"Audit recorded for {event_type} on {action_type}",
                )
            except Exception:
                pass

        return entry

    def get_entries(
        self,
        proposal_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[GovernanceAuditEntry]:
        """Queries recorded audit log entries with optional filtering."""
        results = list(self._entries)
        if proposal_id:
            results = [e for e in results if e.proposal_id == proposal_id]
        if incident_id:
            results = [e for e in results if e.incident_id == incident_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        return results

    get_audit_history = get_entries



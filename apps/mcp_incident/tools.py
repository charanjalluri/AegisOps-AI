"""
AegisOps AI - Incident Management Tools
Implements transactional lifecycle operations, evidence recording, hypothesis calibration,
and action proposals with secret sanitization and event broadcasting.
"""

from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from apps.common.mcp.security import Sanitizer
from apps.mcp_incident.models import (
    AddEvidenceInput,
    AddHypothesisInput,
    CloseIncidentInput,
    CreateActionProposalInput,
    CreateIncidentInput,
    GetIncidentInput,
    IncidentSeverity,
    IncidentStatus,
    UpdateIncidentInput,
)
from apps.mcp_incident.storage import InvestigationStorage


class IncidentTools:
    """
    Transactional tool interface for active incident investigations.
    Manages incidents, evidence items, competing hypotheses, and remediation proposals.
    """

    def __init__(
        self,
        storage: Optional[InvestigationStorage] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.storage = storage or InvestigationStorage()
        self.event_emitter = event_emitter

    async def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        if self.event_emitter:
            try:
                res = self.event_emitter(event_type, payload)
                if hasattr(res, "__await__"):
                    await res
            except Exception:
                pass

    # 1. Create Incident
    async def create_incident(self, input_data: CreateIncidentInput) -> Dict[str, Any]:
        incident_id = input_data.incident_id or f"inc-{uuid4().hex[:8]}"

        # Validate severity
        valid_sevs = {s.value for s in IncidentSeverity}
        if input_data.severity not in valid_sevs:
            raise ValueError(f"Invalid severity '{input_data.severity}'. Must be one of {valid_sevs}")

        incident = await self.storage.create_incident(
            incident_id=incident_id,
            title=input_data.title,
            service=input_data.service,
            severity=input_data.severity,
            summary=input_data.summary,
        )

        res = incident.model_dump()
        await self._emit_event("incidents.created", res)
        return res

    # 2. Update Incident
    async def update_incident(self, input_data: UpdateIncidentInput) -> Dict[str, Any]:
        existing = await self.storage.get_incident(input_data.incident_id)
        if not existing:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")

        if input_data.status:
            valid_statuses = {s.value for s in IncidentStatus}
            if input_data.status not in valid_statuses:
                raise ValueError(f"Invalid status '{input_data.status}'. Must be one of {valid_statuses}")

        if input_data.severity:
            valid_sevs = {s.value for s in IncidentSeverity}
            if input_data.severity not in valid_sevs:
                raise ValueError(f"Invalid severity '{input_data.severity}'. Must be one of {valid_sevs}")

        updated = await self.storage.update_incident(
            incident_id=input_data.incident_id,
            status=input_data.status,
            summary=input_data.summary,
            severity=input_data.severity,
        )
        if not updated:
            raise ValueError(f"Failed to update incident '{input_data.incident_id}'")

        res = updated.model_dump()
        await self._emit_event("incidents.updated", res)
        return res

    # 3. Add Evidence
    async def add_evidence(self, input_data: AddEvidenceInput) -> Dict[str, Any]:
        existing = await self.storage.get_incident(input_data.incident_id)
        if not existing:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")

        # Sanitize sensitive keys / tokens from raw tool output before storage
        sanitized_raw = Sanitizer.sanitize(input_data.raw_data)
        sanitized_interpretation = Sanitizer.sanitize(input_data.interpretation)

        evidence = await self.storage.add_evidence(
            incident_id=input_data.incident_id,
            source_tool=input_data.source_tool,
            signal_type=input_data.signal_type,
            confidence_weight=input_data.confidence_weight,
            raw_data=sanitized_raw,
            interpretation=sanitized_interpretation,
        )
        return evidence.model_dump()

    # 4. Add Hypothesis
    async def add_hypothesis(self, input_data: AddHypothesisInput) -> Dict[str, Any]:
        existing = await self.storage.get_incident(input_data.incident_id)
        if not existing:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")

        hypothesis = await self.storage.add_or_update_hypothesis(
            incident_id=input_data.incident_id,
            title=input_data.title,
            confidence_score=input_data.confidence_score,
            supporting_evidence=input_data.supporting_evidence,
            refuting_evidence=input_data.refuting_evidence,
            rationale=input_data.rationale,
            hypothesis_id=input_data.hypothesis_id,
        )

        res = hypothesis.model_dump()
        await self._emit_event("ai.analysis", res)
        return res

    # 5. Create Action Proposal
    async def create_action_proposal(self, input_data: CreateActionProposalInput) -> Dict[str, Any]:
        existing = await self.storage.get_incident(input_data.incident_id)
        if not existing:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")

        valid_risks = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if input_data.risk_level.upper() not in valid_risks:
            raise ValueError(f"Invalid risk level '{input_data.risk_level}'. Must be one of {valid_risks}")

        sanitized_params = Sanitizer.sanitize(input_data.parameters)

        proposal = await self.storage.create_action_proposal(
            incident_id=input_data.incident_id,
            action_type=input_data.action_type,
            parameters=sanitized_params,
            risk_level=input_data.risk_level.upper(),
            rationale=input_data.rationale,
        )

        res = proposal.model_dump()
        await self._emit_event("ai.actions.proposed", res)
        return res

    # 6. Close Incident
    async def close_incident(self, input_data: CloseIncidentInput) -> Dict[str, Any]:
        existing = await self.storage.get_incident(input_data.incident_id)
        if not existing:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")

        resolved = await self.storage.close_incident(
            incident_id=input_data.incident_id,
            root_cause=input_data.root_cause,
            winning_hypothesis_id=input_data.winning_hypothesis_id,
            summary=input_data.summary,
        )

        res = resolved.model_dump()
        await self._emit_event("incidents.updated", res)
        return res

    # 7. Query Methods
    async def get_incident(self, input_data: GetIncidentInput) -> Dict[str, Any]:
        inc = await self.storage.get_incident(input_data.incident_id)
        if not inc:
            raise ValueError(f"Incident '{input_data.incident_id}' not found")
        evidence = await self.storage.get_evidence(input_data.incident_id)
        hypotheses = await self.storage.get_hypotheses(input_data.incident_id)
        proposals = await self.storage.get_action_proposals(input_data.incident_id)

        data = inc.model_dump()
        data["evidence"] = [e.model_dump() for e in evidence]
        data["hypotheses"] = [h.model_dump() for h in hypotheses]
        data["action_proposals"] = [p.model_dump() for p in proposals]
        return data

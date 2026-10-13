"""
AegisOps AI - Incidents REST Router (UI-01, UI-02, UI-03)
Exposes active and historical incidents, canonical evidence items,
calibrated diagnostic hypotheses, and MCP tool call history.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.api.dependencies import get_storage
from apps.mcp_incident.models import (
    EvidenceItem,
    HypothesisItem,
    IncidentDetail,
    ToolHistoryItem,
)
from apps.mcp_incident.storage import InvestigationStorage

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=List[IncidentDetail])
async def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. detected, investigating, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. SEV-1, SEV-2, CRITICAL, HIGH)"),
    limit: int = Query(50, ge=1, le=100, description="Max number of items to return"),
    storage: InvestigationStorage = Depends(get_storage),
) -> List[IncidentDetail]:
    """
    Returns list of incidents ordered by creation time descending.
    Enforces a maximum limit of 100 items.
    """
    return await storage.list_incidents(status=status_filter, severity=severity, limit=limit)


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: str,
    storage: InvestigationStorage = Depends(get_storage),
) -> IncidentDetail:
    """Returns single incident detail by ID or raises 404."""
    incident = await storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return incident


@router.get("/{incident_id}/evidence", response_model=List[EvidenceItem])
async def get_incident_evidence(
    incident_id: str,
    storage: InvestigationStorage = Depends(get_storage),
) -> List[EvidenceItem]:
    """Returns all normalized evidence items associated with the incident."""
    incident = await storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return await storage.get_evidence(incident_id)


@router.get("/{incident_id}/hypotheses", response_model=List[HypothesisItem])
async def get_incident_hypotheses(
    incident_id: str,
    storage: InvestigationStorage = Depends(get_storage),
) -> List[HypothesisItem]:
    """Returns competing diagnostic hypotheses sorted descending by confidence score."""
    incident = await storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    hypos = await storage.get_hypotheses(incident_id)
    hypos.sort(key=lambda h: h.confidence_score, reverse=True)
    return hypos


@router.get("/{incident_id}/tools", response_model=List[ToolHistoryItem])
async def get_incident_tools(
    incident_id: str,
    storage: InvestigationStorage = Depends(get_storage),
) -> List[ToolHistoryItem]:
    """Returns chronological MCP tool executions recorded for the incident."""
    incident = await storage.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return await storage.get_tool_history(incident_id)

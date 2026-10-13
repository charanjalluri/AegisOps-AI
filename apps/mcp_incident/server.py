"""
AegisOps AI - Incident MCP Server Factory
Registers all transactional incident lifecycle and short-term memory tools on BaseMCPServer.
"""

from typing import Any, Callable, Dict, Optional

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_incident.models import (
    AddEvidenceInput,
    AddHypothesisInput,
    CloseIncidentInput,
    CreateActionProposalInput,
    CreateIncidentInput,
    GetIncidentInput,
    UpdateIncidentInput,
)
from apps.mcp_incident.storage import InvestigationStorage
from apps.mcp_incident.tools import IncidentTools


def create_incident_mcp_server(
    storage: Optional[InvestigationStorage] = None,
    event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
) -> BaseMCPServer:
    """Creates and configures the Incident MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-incident-mcp",
        version="0.1.0",
        description="Transactional incident lifecycle, evidence chaining, hypotheses calibration, and action proposal MCP server",
    )
    tools = IncidentTools(storage=storage, event_emitter=event_emitter)

    @server.tool(
        name="create_incident",
        description="Create a new operational incident with initial severity and diagnostic summary",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=CreateIncidentInput,
    )
    async def create_incident(input_data: CreateIncidentInput):
        return await tools.create_incident(input_data)

    @server.tool(
        name="update_incident",
        description="Update incident lifecycle state, severity, or active investigation summary",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=UpdateIncidentInput,
    )
    async def update_incident(input_data: UpdateIncidentInput):
        return await tools.update_incident(input_data)

    @server.tool(
        name="add_evidence",
        description="Record a verified piece of evidence from diagnostic tools into the short-term memory chain",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=AddEvidenceInput,
    )
    async def add_evidence(input_data: AddEvidenceInput):
        return await tools.add_evidence(input_data)

    @server.tool(
        name="add_hypothesis",
        description="Formulate or update a competing incident hypothesis with calibrated confidence score and evidence links",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=AddHypothesisInput,
    )
    async def add_hypothesis(input_data: AddHypothesisInput):
        return await tools.add_hypothesis(input_data)

    @server.tool(
        name="create_action_proposal",
        description="Propose a controlled remediation action with parameters and risk level for approval evaluation",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=CreateActionProposalInput,
    )
    async def create_action_proposal(input_data: CreateActionProposalInput):
        return await tools.create_action_proposal(input_data)

    @server.tool(
        name="close_incident",
        description="Resolve and close an incident recording root cause and validating the winning hypothesis",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=CloseIncidentInput,
    )
    async def close_incident(input_data: CloseIncidentInput):
        return await tools.close_incident(input_data)

    @server.tool(
        name="get_incident",
        description="Retrieve full consolidated incident details including evidence chain, hypotheses, and action proposals",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetIncidentInput,
    )
    async def get_incident(input_data: GetIncidentInput):
        return await tools.get_incident(input_data)

    return server

"""
AegisOps AI - Deployment MCP Server Factory (MCP-06)
Registers deployment inspection and policy-gated rollback tools on BaseMCPServer.
"""

from typing import Any, Callable, Dict, Optional

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_deployment.models import (
    GetDeploymentHistoryInput,
    GetServiceVersionInput,
    RestartRequest,
    RollbackRequest,
)
from apps.mcp_deployment.tools import DeploymentTools
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.engine import PolicyEngine


def create_deployment_mcp_server(
    storage: Optional[InvestigationStorage] = None,
    policy_engine: Optional[PolicyEngine] = None,
    approval_manager: Optional[ApprovalManager] = None,
    event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    tools_instance: Optional[DeploymentTools] = None,
) -> BaseMCPServer:
    """Creates and configures the Deployment MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-deployment-mcp",
        version="0.1.0",
        description="Controlled deployment inspection and policy-gated rollback MCP server",
    )
    tools = tools_instance or DeploymentTools(
        storage=storage,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        event_emitter=event_emitter,
    )

    @server.tool(
        name="get_current_version",
        description="Query the currently active deployment release and commit for a service",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetServiceVersionInput,
    )
    async def get_current_version(input_data: GetServiceVersionInput):
        res = await tools.get_current_version(input_data.service)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_previous_version",
        description="Query the previous stable release version for a service prior to the current deployment",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetServiceVersionInput,
    )
    async def get_previous_version(input_data: GetServiceVersionInput):
        res = await tools.get_previous_version(input_data.service)
        return res.model_dump(mode="json")

    @server.tool(
        name="get_deployment_history",
        description="Retrieve chronological deployment history for a service",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetDeploymentHistoryInput,
    )
    async def get_deployment_history(input_data: GetDeploymentHistoryInput):
        res = await tools.get_deployment_history(input_data.service, limit=input_data.limit)
        return [r.model_dump(mode="json") for r in res]

    @server.tool(
        name="rollback_deployment",
        description="Roll back a service to a previous version; strictly requires an approved proposal_id",
        timeout_seconds=30.0,
        rate_limit_rpm=30,
        is_mutation=True,
        pydantic_model=RollbackRequest,
    )
    async def rollback_deployment(input_data: RollbackRequest):
        res = await tools.rollback_deployment(
            service=input_data.service,
            target_version=input_data.target_version,
            proposal_id=input_data.proposal_id,
        )
        return res.model_dump(mode="json")

    @server.tool(
        name="restart_service",
        description="Restart a service process",
        timeout_seconds=20.0,
        rate_limit_rpm=60,
        is_mutation=True,
        pydantic_model=RestartRequest,
    )
    async def restart_service(input_data: RestartRequest):
        res = await tools.restart_service(
            service=input_data.service,
            proposal_id=input_data.proposal_id,
        )
        return res.model_dump(mode="json")

    return server

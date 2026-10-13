"""
AegisOps AI - n8n MCP Server Factory (MCP-07)
Registers workflow execution and status introspection tools on BaseMCPServer.
"""

from typing import Optional

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_n8n.models import (
    WorkflowExecutionInput,
    WorkflowStatusInput,
)
from apps.mcp_n8n.tools import N8nTools


def create_n8n_mcp_server(
    tools_instance: Optional[N8nTools] = None,
    base_webhook_url: Optional[str] = None,
) -> BaseMCPServer:
    """Creates and configures the n8n MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-n8n-mcp",
        version="0.1.0",
        description="External workflow automation and operator alerting MCP server",
    )
    tools = tools_instance or N8nTools(base_webhook_url=base_webhook_url)

    @server.tool(
        name="execute_workflow",
        description="Execute an n8n automation workflow (e.g. incident-alert-slack, jira-ticket-creation) with offline fallback",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=WorkflowExecutionInput,
    )
    async def execute_workflow(input_data: WorkflowExecutionInput):
        res = await tools.execute_workflow(
            workflow_name=input_data.workflow_name,
            payload=input_data.payload,
        )
        return res.model_dump(mode="json")

    @server.tool(
        name="get_execution_status",
        description="Query the execution status and output of a previously triggered workflow",
        timeout_seconds=10.0,
        rate_limit_rpm=120,
        pydantic_model=WorkflowStatusInput,
    )
    async def get_execution_status(input_data: WorkflowStatusInput):
        res = await tools.get_execution_status(input_data.execution_id)
        return res.model_dump(mode="json")

    return server

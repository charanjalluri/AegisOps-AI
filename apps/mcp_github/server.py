"""
AegisOps AI - GitHub MCP Server Factory
Registers all 5 GitHub code change introspection tools on BaseMCPServer.
"""

from typing import Optional

from apps.common.mcp.server import BaseMCPServer
from apps.mcp_github.models import (
    ChangedFilesInput,
    DeploymentHistoryInput,
    GetCommitInput,
    PullRequestsInput,
    RecentCommitsInput,
)
from apps.mcp_github.provider import BaseGitProvider
from apps.mcp_github.tools import GitHubTools


def create_github_mcp_server(
    provider: Optional[BaseGitProvider] = None,
) -> BaseMCPServer:
    """Creates and configures the GitHub MCP server instance."""
    server = BaseMCPServer(
        name="aegisops-github-mcp",
        version="0.1.0",
        description="Read-only GitHub commit tracking, PR inspection, diff analysis, and release history MCP server",
    )
    tools = GitHubTools(provider=provider)

    @server.tool(
        name="get_recent_commits",
        description="Retrieve recent git commit history for a service repository",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=RecentCommitsInput,
    )
    async def get_recent_commits(input_data: RecentCommitsInput):
        return await tools.get_recent_commits(input_data)

    @server.tool(
        name="get_commit",
        description="Retrieve detailed commit metadata and unified code diff with token budget limits",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=GetCommitInput,
    )
    async def get_commit(input_data: GetCommitInput):
        return await tools.get_commit(input_data)

    @server.tool(
        name="get_pull_requests",
        description="List pull requests filtered by state (open, merged, closed, all)",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=PullRequestsInput,
    )
    async def get_pull_requests(input_data: PullRequestsInput):
        return await tools.get_pull_requests(input_data)

    @server.tool(
        name="get_changed_files",
        description="Inspect files changed, lines added/deleted, and patch snippets for a commit or PR",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=ChangedFilesInput,
    )
    async def get_changed_files(input_data: ChangedFilesInput):
        return await tools.get_changed_files(input_data)

    @server.tool(
        name="get_deployment_history",
        description="List release version tags, deployment timestamps, and correlated commit hashes",
        timeout_seconds=15.0,
        rate_limit_rpm=120,
        pydantic_model=DeploymentHistoryInput,
    )
    async def get_deployment_history(input_data: DeploymentHistoryInput):
        return await tools.get_deployment_history(input_data)

    return server

"""
AegisOps AI - GitHub Inspection Tools
Implements commit history tracking, commit diff inspection, pull request listing,
changed file analysis, and deployment release history with token budgeting.
"""

from typing import Any, Dict, List, Optional

from apps.common.mcp.budget import TokenBudgetGuard
from apps.mcp_github.models import (
    ChangedFilesInput,
    CommitDetail,
    DeploymentHistoryInput,
    GetCommitInput,
    PullRequestsInput,
    RecentCommitsInput,
)
from apps.mcp_github.provider import BaseGitProvider, LocalMockGitProvider


class GitHubTools:
    """
    Read-only GitHub telemetry tools for inspecting source code changes,
    pull requests, and deployment versions correlated with incidents.
    """

    def __init__(self, provider: Optional[BaseGitProvider] = None):
        self.provider = provider or LocalMockGitProvider()

    async def get_recent_commits(self, input_data: RecentCommitsInput) -> Dict[str, Any]:
        """Lists recent git commits on a branch for the target service."""
        commits = await self.provider.get_recent_commits(
            service=input_data.service,
            limit=input_data.limit,
            branch=input_data.branch,
        )
        return {
            "service": input_data.service,
            "branch": input_data.branch,
            "count": len(commits),
            "commits": [c.model_dump() for c in commits],
        }

    async def get_commit(self, input_data: GetCommitInput) -> Dict[str, Any]:
        """Retrieves commit metadata and unified diff with token budget enforcement."""
        commit = await self.provider.get_commit(
            service=input_data.service,
            commit_sha=input_data.commit_sha,
        )
        if not commit:
            raise ValueError(
                f"Commit '{input_data.commit_sha}' not found in repository for service '{input_data.service}'"
            )

        # Apply token budget guard on diff
        diff_text = commit.diff
        token_count = TokenBudgetGuard.estimate_tokens(diff_text)
        truncated = False
        max_diff_tokens = 3000

        if token_count > max_diff_tokens:
            truncated = True
            # Keep first 3000 tokens * 4 chars = 12000 chars
            diff_text = diff_text[: max_diff_tokens * TokenBudgetGuard.CHARS_PER_TOKEN] + "\n\n[... DIFF TRUNCATED BY TOKEN BUDGET ...]"
            token_count = TokenBudgetGuard.estimate_tokens(diff_text)

        commit.diff = diff_text
        commit.token_count = token_count
        commit.truncated = truncated
        return commit.model_dump()

    async def get_pull_requests(self, input_data: PullRequestsInput) -> Dict[str, Any]:
        """Lists pull requests filtered by state (open, closed, merged, all)."""
        prs = await self.provider.get_pull_requests(
            service=input_data.service,
            state=input_data.state,
            limit=input_data.limit,
        )
        return {
            "service": input_data.service,
            "state_filter": input_data.state,
            "count": len(prs),
            "pull_requests": [pr.model_dump() for pr in prs],
        }

    async def get_changed_files(self, input_data: ChangedFilesInput) -> Dict[str, Any]:
        """Inspects filenames, line changes, and patch snippets for a commit or PR."""
        files = await self.provider.get_changed_files(
            service=input_data.service,
            identifier=input_data.commit_sha_or_pr,
        )
        return {
            "service": input_data.service,
            "identifier": input_data.commit_sha_or_pr,
            "count": len(files),
            "files": [f.model_dump() for f in files],
        }

    async def get_deployment_history(self, input_data: DeploymentHistoryInput) -> Dict[str, Any]:
        """Lists deployment release tags correlated with commit hashes."""
        deps = await self.provider.get_deployment_history(
            service=input_data.service,
            limit=input_data.limit,
        )
        return {
            "service": input_data.service,
            "count": len(deps),
            "deployments": [d.model_dump() for d in deps],
        }

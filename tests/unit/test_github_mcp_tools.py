"""
Unit tests for GitHub inspection tools (apps.mcp_github.tools).
Tests commit tracking, leak diff inspection, PR listing, changed files,
deployment history, and token budget diff truncation offline.
"""

from unittest.mock import AsyncMock
import pytest

from apps.mcp_github.models import (
    ChangedFilesInput,
    CommitDetail,
    DeploymentHistoryInput,
    GetCommitInput,
    PullRequestsInput,
    RecentCommitsInput,
)
from apps.mcp_github.provider import LocalMockGitProvider
from apps.mcp_github.tools import GitHubTools


@pytest.mark.anyio
async def test_github_tools_get_recent_commits():
    tools = GitHubTools()
    res = await tools.get_recent_commits(RecentCommitsInput(service="payment-service", limit=5))
    assert res["service"] == "payment-service"
    assert res["count"] == 2
    assert res["commits"][0]["short_sha"] == "c0ffee1"


@pytest.mark.anyio
async def test_github_tools_get_commit_leak():
    tools = GitHubTools()
    res = await tools.get_commit(GetCommitInput(service="payment-service", commit_sha="c0ffee1"))
    assert res["short_sha"] == "c0ffee1"
    assert "Temporary pool bypass" in res["diff"]
    assert "conn.close() omitted" in res["diff"]
    assert res["token_count"] > 0
    assert not res["truncated"]


@pytest.mark.anyio
async def test_github_tools_get_commit_not_found():
    tools = GitHubTools()
    with pytest.raises(ValueError, match="not found in repository"):
        await tools.get_commit(GetCommitInput(service="payment-service", commit_sha="badsha123"))


@pytest.mark.anyio
async def test_github_tools_diff_token_budget_truncation():
    mock_provider = LocalMockGitProvider()
    massive_diff = "diff --git a/foo b/foo\n" + ("+ leak_line_long_code_statement_here();\n" * 800)
    mock_commit = CommitDetail(
        sha="bigdiff123456789",
        short_sha="bigdiff",
        author="dev@example.com",
        date="2026-10-10T10:00:00Z",
        message="feat: massive diff",
        service="payment-service",
        files_changed_count=1,
        insertions=800,
        deletions=0,
        diff=massive_diff,
    )
    mock_provider.get_commit = AsyncMock(return_value=mock_commit)

    tools = GitHubTools(provider=mock_provider)
    res = await tools.get_commit(GetCommitInput(service="payment-service", commit_sha="bigdiff"))
    assert res["truncated"] is True
    assert "[... DIFF TRUNCATED BY TOKEN BUDGET ...]" in res["diff"]


@pytest.mark.anyio
async def test_github_tools_get_pull_requests():
    tools = GitHubTools()
    res = await tools.get_pull_requests(PullRequestsInput(service="payment-service", state="merged"))
    assert res["count"] == 2
    assert res["pull_requests"][0]["number"] == 42


@pytest.mark.anyio
async def test_github_tools_get_changed_files():
    tools = GitHubTools()
    res = await tools.get_changed_files(ChangedFilesInput(service="payment-service", commit_sha_or_pr="42"))
    assert res["count"] == 1
    assert res["files"][0]["filename"] == "apps/payment_service/database.py"


@pytest.mark.anyio
async def test_github_tools_get_deployment_history():
    tools = GitHubTools()
    res = await tools.get_deployment_history(DeploymentHistoryInput(service="payment-service"))
    assert res["count"] == 2
    assert res["deployments"][0]["release_tag"] == "v2.8.1"
    assert res["deployments"][1]["release_tag"] == "v2.8.0"

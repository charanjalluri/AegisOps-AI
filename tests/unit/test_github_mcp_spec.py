"""
Unit specification tests for Git models and LocalMockGitProvider (apps.mcp_github.provider).
Verifies deterministic offline git history, leak diffs, PR linkage, and release tags.
"""

import pytest
from apps.mcp_github.provider import LocalMockGitProvider


@pytest.mark.anyio
async def test_mock_git_provider_recent_commits():
    provider = LocalMockGitProvider()
    commits = await provider.get_recent_commits("payment-service", limit=10)
    assert len(commits) == 2
    # Verify newest first: c0ffee1 before a1b2c3d
    assert commits[0].short_sha == "c0ffee1"
    assert commits[1].short_sha == "a1b2c3d"
    assert "bob" in commits[0].author
    assert "alice" in commits[1].author


@pytest.mark.anyio
async def test_mock_git_provider_get_commit_full_and_short_sha():
    provider = LocalMockGitProvider()
    # Test short SHA
    commit_short = await provider.get_commit("payment-service", "c0ffee1")
    assert commit_short is not None
    assert commit_short.sha.startswith("c0ffee1")
    assert "Temporary pool bypass" in commit_short.diff
    assert "conn.close() omitted" in commit_short.diff

    # Test full SHA
    commit_full = await provider.get_commit(
        "payment-service", "c0ffee123456789abcdef0123456789abcdef012"
    )
    assert commit_full is not None
    assert commit_full.sha == commit_short.sha

    # Test non-existent SHA
    missing = await provider.get_commit("payment-service", "deadbeef")
    assert missing is None


@pytest.mark.anyio
async def test_mock_git_provider_pull_requests():
    provider = LocalMockGitProvider()
    prs = await provider.get_pull_requests("payment-service", state="all")
    assert len(prs) == 2
    pr_42 = next(p for p in prs if p.number == 42)
    assert pr_42.state == "merged"
    assert pr_42.merge_commit_sha.startswith("c0ffee1")
    assert "retries" in pr_42.title

    # Filter state
    merged = await provider.get_pull_requests("payment-service", state="merged")
    assert len(merged) == 2
    open_prs = await provider.get_pull_requests("payment-service", state="open")
    assert len(open_prs) == 0


@pytest.mark.anyio
async def test_mock_git_provider_changed_files():
    provider = LocalMockGitProvider()
    # By commit SHA
    files_commit = await provider.get_changed_files("payment-service", "c0ffee1")
    assert len(files_commit) == 1
    assert files_commit[0].filename == "apps/payment_service/database.py"
    assert files_commit[0].status == "modified"
    assert files_commit[0].additions == 2

    # By PR number
    files_pr = await provider.get_changed_files("payment-service", "42")
    assert len(files_pr) == 1
    assert files_pr[0].filename == "apps/payment_service/database.py"


@pytest.mark.anyio
async def test_mock_git_provider_deployment_history():
    provider = LocalMockGitProvider()
    deployments = await provider.get_deployment_history("payment-service", limit=5)
    assert len(deployments) == 2
    assert deployments[0].release_tag == "v2.8.1"
    assert deployments[0].commit_sha.startswith("c0ffee1")
    assert deployments[1].release_tag == "v2.8.0"
    assert deployments[1].commit_sha.startswith("a1b2c3d")

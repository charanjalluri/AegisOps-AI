"""
Integration tests for GitHub MCP server against the live GitHub REST API.
Decorated with @pytest.mark.integration so they are explicitly opt-in and do not run in offline test passes.
Requires GITHUB_TOKEN loaded securely from the environment. Never prints, logs, or exposes tokens.
Configurable via GITHUB_OWNER and GITHUB_REPO environment variables.
"""

import os
import pytest

from apps.common.env import load_env_file
from apps.mcp_github.main import get_git_provider
from apps.mcp_github.provider import (
    GitHubAPIError,
    GitHubAPIProvider,
    GitHubAuthError,
    GitHubNotFoundError,
    LocalMockGitProvider,
)
from apps.mcp_github.server import create_github_mcp_server


def get_configured_github_settings():
    load_env_file()
    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER", "charanjalluri")
    repo = os.getenv("GITHUB_REPO", "AegisOps-AI")
    return token, owner, repo


@pytest.fixture(autouse=True)
def check_github_token_available():
    token, _, _ = get_configured_github_settings()
    if not token or token.startswith("ghp_your_") or not token.strip():
        pytest.skip("Valid GITHUB_TOKEN not configured in environment or .env; skipping live integration tests")


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_provider_selected_over_mock():
    """Confirms live provider is selected when token is present, and does not fall back to mock."""
    provider = get_git_provider()
    assert isinstance(provider, GitHubAPIProvider), "Expected GitHubAPIProvider when GITHUB_TOKEN is set"
    assert not isinstance(provider, LocalMockGitProvider), "Provider must not be LocalMockGitProvider"


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_auth_and_user_access():
    """Validates authenticated GitHub API access against /user without exposing tokens."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)

    creds = await provider.validate_credentials()
    assert creds["authenticated_user"], "Authenticated user login must not be empty"
    assert creds["rate_limit_remaining"] > 0, "Rate limit remaining must be > 0"
    assert creds["configured_owner"] == owner
    assert creds["configured_repo"] == repo

    # Ensure token does NOT appear anywhere in the result
    assert token not in str(creds)
    assert "Bearer" not in str(creds)


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_recent_commits():
    """Retrieves recent commits from the configured live repository with bounded pagination."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)

    commits = await provider.get_recent_commits(service="payment-service", limit=5, branch="main")
    assert isinstance(commits, list)
    assert len(commits) > 0, f"Expected at least 1 commit in {owner}/{repo}"
    assert len(commits) <= 5, "Pagination limit must be bounded"

    top_commit = commits[0]
    assert len(top_commit.sha) == 40, "Commit SHA must be a 40-character hex string"
    assert len(top_commit.short_sha) == 7, "Short SHA must be 7 characters"
    assert top_commit.author, "Author name must not be empty"
    assert top_commit.message, "Commit message must not be empty"
    assert top_commit.date, "Commit date must not be empty"
    assert token not in str(top_commit)


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_commit_and_changed_files():
    """Inspects detailed commit diff and changed files for a real commit in the live repository."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)

    commits = await provider.get_recent_commits(service="payment-service", limit=1, branch="main")
    assert len(commits) > 0
    target_sha = commits[0].sha

    # Fetch detailed commit
    detail = await provider.get_commit(service="payment-service", commit_sha=target_sha)
    assert detail is not None
    assert detail.sha == target_sha
    assert detail.files_changed_count >= 1
    assert token not in str(detail)

    # Fetch changed files
    files = await provider.get_changed_files(service="payment-service", identifier=target_sha)
    assert isinstance(files, list)
    assert len(files) >= 1
    assert files[0].filename, "Changed file filename must not be empty"
    assert files[0].status in {"added", "modified", "removed", "renamed"}
    assert token not in str(files)


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_pull_requests():
    """Retrieves pull requests from the live repository and ensures structured schema validation."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)

    prs = await provider.get_pull_requests(service="payment-service", state="all", limit=5)
    assert isinstance(prs, list)
    assert len(prs) <= 5
    for pr in prs:
        assert pr.number > 0
        assert pr.title
        assert pr.author
        assert pr.state in {"open", "closed", "merged"}
        assert token not in str(pr)


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_invalid_credentials_error_handling():
    """Verifies that invalid credentials raise GitHubAuthError (HTTP 401) without leaking tokens."""
    _, owner, repo = get_configured_github_settings()
    fake_token = "invalid_dummy_test_token_99999"
    provider = GitHubAPIProvider(token=fake_token, repo_owner=owner, repo_name=repo)

    with pytest.raises(GitHubAuthError) as exc_info:
        await provider.validate_credentials()

    err_str = str(exc_info.value)
    assert "401" in err_str or "authentication failed" in err_str.lower()
    # Critical security check: token must NEVER appear in the error message
    assert fake_token not in err_str
    assert "Bearer" not in err_str


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_nonexistent_repo_error_handling():
    """Verifies that nonexistent repository raises GitHubNotFoundError (HTTP 404) distinguishing missing repo."""
    token, owner, _ = get_configured_github_settings()
    nonexistent_repo = "definitely-nonexistent-repo-aegisops-xyz-12345"
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=nonexistent_repo)

    with pytest.raises(GitHubNotFoundError) as exc_info:
        await provider.get_recent_commits(service="test", limit=5)

    err_str = str(exc_info.value)
    assert "404" in err_str or "not found" in err_str.lower()
    assert nonexistent_repo in err_str
    # Critical security check: token must NEVER appear in error
    assert token not in err_str
    assert "Bearer" not in err_str


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_network_timeout_enforcement():
    """Verifies that timeouts are enforced strictly without leaking credentials."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo, timeout_seconds=0.000001)

    with pytest.raises(GitHubAPIError) as exc_info:
        await provider.get_recent_commits(service="test", limit=5)

    err_str = str(exc_info.value)
    assert "timed out" in err_str.lower() or "timeout" in err_str.lower()
    assert token not in err_str


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_github_mcp_server_jsonrpc_dispatch():
    """Verifies full MCP JSON-RPC 2.0 dispatch through server against the live GitHub provider."""
    token, owner, repo = get_configured_github_settings()
    provider = GitHubAPIProvider(token=token, repo_owner=owner, repo_name=repo)
    server = create_github_mcp_server(provider=provider)

    req = {
        "jsonrpc": "2.0",
        "id": "live-rpc-gh",
        "method": "tools/call",
        "params": {
            "name": "get_recent_commits",
            "arguments": {"service": "payment-service", "limit": 2, "branch": "main"},
        },
    }
    resp = await server.handle_jsonrpc(req)
    assert resp.error is None
    assert resp.result["is_error"] is False
    data = resp.result["content"][0]["data"]
    assert data["service"] == "payment-service"
    assert data["count"] > 0
    assert len(data["commits"]) <= 2
    assert token not in str(resp.model_dump())

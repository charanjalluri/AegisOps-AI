"""
AegisOps AI - Git Data Providers
Provides offline deterministic git telemetry via LocalMockGitProvider
and authenticated real GitHub REST API integration via GitHubAPIProvider.
"""

from abc import ABC, abstractmethod
import os
from typing import Any, Dict, List, Optional
import httpx

from apps.common.env import load_env_file
from apps.common.mcp.security import Sanitizer
from apps.mcp_github.models import (
    ChangedFileItem,
    CommitDetail,
    CommitItem,
    DeploymentReleaseItem,
    PullRequestItem,
)


class BaseGitProvider(ABC):
    """Abstract interface for Git telemetry providers."""

    @abstractmethod
    async def get_recent_commits(
        self, service: str, limit: int = 10, branch: str = "main"
    ) -> List[CommitItem]:
        pass

    @abstractmethod
    async def get_commit(
        self, service: str, commit_sha: str
    ) -> Optional[CommitDetail]:
        pass

    @abstractmethod
    async def get_pull_requests(
        self, service: str, state: str = "all", limit: int = 10
    ) -> List[PullRequestItem]:
        pass

    @abstractmethod
    async def get_changed_files(
        self, service: str, identifier: str
    ) -> List[ChangedFileItem]:
        pass

    @abstractmethod
    async def get_deployment_history(
        self, service: str, limit: int = 10
    ) -> List[DeploymentReleaseItem]:
        pass


class LocalMockGitProvider(BaseGitProvider):
    """
    100% offline, reproducible mock git repository provider pre-seeded
    with payment-service v2.8.0 baseline and v2.8.1 connection leak commit diffs.
    """

    def __init__(self):
        self._commits: Dict[str, Dict[str, Any]] = {
            "c0ffee123456789abcdef0123456789abcdef012": {
                "sha": "c0ffee123456789abcdef0123456789abcdef012",
                "short_sha": "c0ffee1",
                "author": "bob <bob@example.com>",
                "date": "2026-10-10T10:15:00Z",
                "message": "feat: enable aggressive retry and pool timeout overrides",
                "service": "payment-service",
                "files_changed_count": 1,
                "insertions": 2,
                "deletions": 0,
                "diff": (
                    "--- a/apps/payment_service/database.py\n"
                    "+++ b/apps/payment_service/database.py\n"
                    "@@ -45,3 +45,5 @@ async def acquire_connection(self):\n"
                    "+    # FIXME: Temporary pool bypass for rapid retries\n"
                    "+    conn = await asyncpg.connect(self.db_url)\n"
                    "+    # conn.close() omitted causing connection leak\n"
                ),
                "changed_files": [
                    {
                        "filename": "apps/payment_service/database.py",
                        "status": "modified",
                        "additions": 2,
                        "deletions": 0,
                        "patch": (
                            "@@ -45,3 +45,5 @@ async def acquire_connection(self):\n"
                            "+    # FIXME: Temporary pool bypass for rapid retries\n"
                            "+    conn = await asyncpg.connect(self.db_url)\n"
                            "+    # conn.close() omitted causing connection leak\n"
                        ),
                    }
                ],
            },
            "a1b2c3d4e5f67890123456789abcdef012345678": {
                "sha": "a1b2c3d4e5f67890123456789abcdef012345678",
                "short_sha": "a1b2c3d",
                "author": "alice <alice@example.com>",
                "date": "2026-10-09T18:00:00Z",
                "message": "fix: stabilize connection pooling and retry defaults",
                "service": "payment-service",
                "files_changed_count": 2,
                "insertions": 15,
                "deletions": 4,
                "diff": (
                    "--- a/apps/payment_service/pool.py\n"
                    "+++ b/apps/payment_service/pool.py\n"
                    "@@ -10,4 +10,4 @@\n"
                    "-POOL_MAX = 20\n"
                    "+POOL_MAX = 50\n"
                ),
                "changed_files": [
                    {
                        "filename": "apps/payment_service/pool.py",
                        "status": "modified",
                        "additions": 1,
                        "deletions": 1,
                        "patch": "@@ -10,4 +10,4 @@\n-POOL_MAX = 20\n+POOL_MAX = 50\n",
                    }
                ],
            },
        }

        self._pull_requests: List[Dict[str, Any]] = [
            {
                "number": 42,
                "title": "feat: aggressive payment retries and timeout tuning",
                "author": "bob <bob@example.com>",
                "state": "merged",
                "created_at": "2026-10-10T09:30:00Z",
                "merged_at": "2026-10-10T10:20:00Z",
                "merge_commit_sha": "c0ffee123456789abcdef0123456789abcdef012",
                "description": "Increases payment retry aggression and overrides connection acquisition timeout.",
                "service": "payment-service",
            },
            {
                "number": 41,
                "title": "fix: pool size increase for high-throughput gateway",
                "author": "alice <alice@example.com>",
                "state": "merged",
                "created_at": "2026-10-09T16:00:00Z",
                "merged_at": "2026-10-09T18:05:00Z",
                "merge_commit_sha": "a1b2c3d4e5f67890123456789abcdef012345678",
                "description": "Enlarges pool size to 50 connections to prevent latency spikes.",
                "service": "payment-service",
            },
        ]

        self._deployments: List[Dict[str, Any]] = [
            {
                "release_tag": "v2.8.1",
                "service": "payment-service",
                "commit_sha": "c0ffee123456789abcdef0123456789abcdef012",
                "deployed_at": "2026-10-10T10:30:00Z",
                "environment": "staging",
                "changelog_summary": "Release v2.8.1: Aggressive retry behavior (introduced connection exhaustion bug)",
            },
            {
                "release_tag": "v2.8.0",
                "service": "payment-service",
                "commit_sha": "a1b2c3d4e5f67890123456789abcdef012345678",
                "deployed_at": "2026-10-09T19:00:00Z",
                "environment": "staging",
                "changelog_summary": "Release v2.8.0: Stable baseline release with 50 connection pool",
            },
        ]

    async def get_recent_commits(
        self, service: str, limit: int = 10, branch: str = "main"
    ) -> List[CommitItem]:
        commits = [
            CommitItem(
                sha=c["sha"],
                short_sha=c["short_sha"],
                author=c["author"],
                date=c["date"],
                message=c["message"],
                service=c.get("service", service),
            )
            for c in self._commits.values()
            if c.get("service") == service or service == "payment-service"
        ]
        commits.sort(key=lambda x: x.date, reverse=True)
        return commits[:limit]

    async def get_commit(
        self, service: str, commit_sha: str
    ) -> Optional[CommitDetail]:
        match = None
        sha_lower = commit_sha.lower()
        for k, c in self._commits.items():
            if k.lower() == sha_lower or c["short_sha"].lower() == sha_lower:
                match = c
                break

        if not match:
            return None

        return CommitDetail(
            sha=match["sha"],
            short_sha=match["short_sha"],
            author=match["author"],
            date=match["date"],
            message=match["message"],
            service=match.get("service", service),
            files_changed_count=match["files_changed_count"],
            insertions=match["insertions"],
            deletions=match["deletions"],
            diff=match["diff"],
        )

    async def get_pull_requests(
        self, service: str, state: str = "all", limit: int = 10
    ) -> List[PullRequestItem]:
        prs = [
            PullRequestItem(**pr)
            for pr in self._pull_requests
            if (pr.get("service") == service or service == "payment-service")
            and (state == "all" or pr["state"] == state)
        ]
        prs.sort(key=lambda x: x.created_at, reverse=True)
        return prs[:limit]

    async def get_changed_files(
        self, service: str, identifier: str
    ) -> List[ChangedFileItem]:
        if identifier.isdigit() or identifier.startswith("#"):
            pr_num = int(identifier.lstrip("#"))
            pr = next((p for p in self._pull_requests if p["number"] == pr_num), None)
            if pr and pr.get("merge_commit_sha"):
                identifier = pr["merge_commit_sha"]

        commit = await self.get_commit(service, identifier)
        if not commit:
            return []

        c_data = next(
            (c for c in self._commits.values() if c["sha"] == commit.sha), None
        )
        if not c_data or "changed_files" not in c_data:
            return []

        return [ChangedFileItem(**cf) for cf in c_data["changed_files"]]

    async def get_deployment_history(
        self, service: str, limit: int = 10
    ) -> List[DeploymentReleaseItem]:
        deps = [
            DeploymentReleaseItem(**d)
            for d in self._deployments
            if d.get("service") == service or service == "payment-service"
        ]
        deps.sort(key=lambda x: x.deployed_at, reverse=True)
        return deps[:limit]


# Explicit GitHub API Error Classes
class GitHubAPIError(Exception):
    """Base exception for GitHub API errors with sanitized messages."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GitHubAuthError(GitHubAPIError):
    """Authentication failure (e.g. 401 Unauthorized or bad token)."""
    pass


class GitHubPermissionError(GitHubAPIError):
    """Permission failure (e.g. 403 Forbidden / insufficient scopes)."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """Rate limit exceeded (e.g. 403/429 rate limit)."""
    pass


class GitHubNotFoundError(GitHubAPIError):
    """Resource not found (e.g. 404 repository, commit, or branch not found)."""
    pass


class GitHubAPIProvider(BaseGitProvider):
    """
    Live GitHub REST API provider using personal access token (GITHUB_TOKEN).
    Connects to configured GITHUB_OWNER and GITHUB_REPO.
    Does NOT silently fall back to mock data on API errors.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        timeout_seconds: float = 10.0,
        base_url: str = "https://api.github.com",
    ):
        load_env_file()
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token or not self.token.strip():
            raise ValueError("GitHubAPIProvider requires a valid non-empty GITHUB_TOKEN")

        self.repo_owner = repo_owner or os.getenv("GITHUB_OWNER", "charanjalluri")
        self.repo_name = repo_name or os.getenv("GITHUB_REPO", "AegisOps-AI")
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AegisOps-AI",
        }

    def _handle_response_error(self, response: httpx.Response, action_description: str):
        status = response.status_code
        err_msg = f"GitHub API error during {action_description}: HTTP {status}"
        try:
            body = response.json()
            api_msg = body.get("message", "")
            if api_msg:
                sanitized_msg = Sanitizer.sanitize(api_msg)
                err_msg += f" - {sanitized_msg}"
        except Exception:
            pass

        if status == 401:
            raise GitHubAuthError(
                f"GitHub authentication failed (HTTP 401): invalid or expired token during {action_description}",
                status_code=status,
            )
        elif status == 403:
            if "rate limit" in err_msg.lower():
                raise GitHubRateLimitError(
                    f"GitHub API rate limit exceeded during {action_description}",
                    status_code=status,
                )
            raise GitHubPermissionError(
                f"GitHub access forbidden (HTTP 403): insufficient scopes/permissions for {self.repo_owner}/{self.repo_name} during {action_description}",
                status_code=status,
            )
        elif status == 404:
            raise GitHubNotFoundError(
                f"GitHub repository or resource not found (HTTP 404): {self.repo_owner}/{self.repo_name} during {action_description}",
                status_code=status,
            )
        elif status == 429:
            raise GitHubRateLimitError(
                f"GitHub API rate limit exceeded (HTTP 429) during {action_description}",
                status_code=status,
            )
        else:
            raise GitHubAPIError(err_msg, status_code=status)

    async def validate_credentials(self) -> Dict[str, Any]:
        """Validates token authentication and retrieves authenticated account metadata."""
        url = f"{self.base_url}/user"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.get(url, headers=self._get_headers())
                if r.status_code != 200:
                    self._handle_response_error(r, "credential validation")
                data = r.json()
                return {
                    "authenticated_user": data.get("login"),
                    "configured_owner": self.repo_owner,
                    "configured_repo": self.repo_name,
                    "scopes": r.headers.get("x-oauth-scopes", ""),
                    "rate_limit_remaining": int(r.headers.get("x-ratelimit-remaining", 0)),
                }
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during credential validation")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network connection error during credential validation: {Sanitizer.sanitize(str(e))}")

    async def get_recent_commits(
        self, service: str, limit: int = 10, branch: str = "main"
    ) -> List[CommitItem]:
        clamped_limit = min(max(1, limit), 50)
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/commits"
        params = {"per_page": clamped_limit}
        if branch:
            params["sha"] = branch

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.get(url, headers=self._get_headers(), params=params)
                if r.status_code != 200:
                    self._handle_response_error(r, f"fetching recent commits for {self.repo_owner}/{self.repo_name}")
                data = r.json()
                if not isinstance(data, list):
                    raise GitHubAPIError(f"Unexpected GitHub API response format: expected list of commits, got {type(data)}")

                commits = []
                for c in data:
                    commit_obj = c.get("commit", {})
                    author_obj = commit_obj.get("author", {})
                    author_name = author_obj.get("name") or "unknown"
                    commit_date = author_obj.get("date") or ""
                    message = commit_obj.get("message") or ""
                    sha = c.get("sha", "")
                    commits.append(
                        CommitItem(
                            sha=sha,
                            short_sha=sha[:7] if sha else "",
                            author=author_name,
                            date=commit_date,
                            message=message,
                            service=service,
                        )
                    )
                return commits
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during get_recent_commits")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network error during get_recent_commits: {Sanitizer.sanitize(str(e))}")

    async def get_commit(
        self, service: str, commit_sha: str
    ) -> Optional[CommitDetail]:
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.get(url, headers=self._get_headers())
                if r.status_code == 404:
                    return None
                if r.status_code != 200:
                    self._handle_response_error(r, f"fetching commit {commit_sha}")
                c = r.json()
                commit_obj = c.get("commit", {})
                author_obj = commit_obj.get("author", {})
                files = c.get("files", [])
                stats = c.get("stats", {})
                diff_patch = "\n".join([f.get("patch", "") for f in files if "patch" in f])

                sha = c.get("sha", commit_sha)
                return CommitDetail(
                    sha=sha,
                    short_sha=sha[:7] if sha else "",
                    author=author_obj.get("name") or "unknown",
                    date=author_obj.get("date") or "",
                    message=commit_obj.get("message") or "",
                    service=service,
                    files_changed_count=len(files),
                    insertions=stats.get("additions", 0),
                    deletions=stats.get("deletions", 0),
                    diff=diff_patch,
                )
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during get_commit")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network error during get_commit: {Sanitizer.sanitize(str(e))}")

    async def get_pull_requests(
        self, service: str, state: str = "all", limit: int = 10
    ) -> List[PullRequestItem]:
        clamped_limit = min(max(1, limit), 50)
        # GitHub API accepts state: open, closed, all
        gh_state = state if state in {"open", "closed", "all"} else "all"
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params = {"state": gh_state, "per_page": clamped_limit}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.get(url, headers=self._get_headers(), params=params)
                if r.status_code != 200:
                    self._handle_response_error(r, f"fetching pull requests for {self.repo_owner}/{self.repo_name}")
                data = r.json()
                if not isinstance(data, list):
                    raise GitHubAPIError(f"Unexpected GitHub API response format: expected list of PRs, got {type(data)}")

                prs = []
                for item in data:
                    user_obj = item.get("user", {})
                    author_name = user_obj.get("login", "unknown")
                    pr_state = item.get("state", "open")
                    if item.get("merged_at"):
                        pr_state = "merged"

                    prs.append(
                        PullRequestItem(
                            number=item.get("number", 0),
                            title=item.get("title", ""),
                            author=author_name,
                            state=pr_state,
                            created_at=item.get("created_at", ""),
                            merged_at=item.get("merged_at"),
                            merge_commit_sha=item.get("merge_commit_sha"),
                            description=item.get("body") or "",
                            service=service,
                        )
                    )
                return prs
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during get_pull_requests")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network error during get_pull_requests: {Sanitizer.sanitize(str(e))}")

    async def get_changed_files(
        self, service: str, identifier: str
    ) -> List[ChangedFileItem]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if identifier.isdigit() or identifier.startswith("#"):
                    pr_num = int(identifier.lstrip("#"))
                    url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_num}/files"
                    r = await client.get(url, headers=self._get_headers(), params={"per_page": 50})
                    if r.status_code != 200:
                        self._handle_response_error(r, f"fetching changed files for PR #{pr_num}")
                    files_data = r.json()
                else:
                    url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/commits/{identifier}"
                    r = await client.get(url, headers=self._get_headers())
                    if r.status_code != 200:
                        self._handle_response_error(r, f"fetching changed files for commit {identifier}")
                    files_data = r.json().get("files", [])

                return [
                    ChangedFileItem(
                        filename=f.get("filename", ""),
                        status=f.get("status", "modified"),
                        additions=f.get("additions", 0),
                        deletions=f.get("deletions", 0),
                        patch=f.get("patch"),
                    )
                    for f in files_data
                ]
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during get_changed_files")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network error during get_changed_files: {Sanitizer.sanitize(str(e))}")

    async def get_deployment_history(
        self, service: str, limit: int = 10
    ) -> List[DeploymentReleaseItem]:
        clamped_limit = min(max(1, limit), 50)
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/releases"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.get(url, headers=self._get_headers(), params={"per_page": clamped_limit})
                if r.status_code != 200:
                    self._handle_response_error(r, f"fetching releases for {self.repo_owner}/{self.repo_name}")
                releases = r.json()
                if not isinstance(releases, list):
                    return []

                return [
                    DeploymentReleaseItem(
                        release_tag=rel.get("tag_name", ""),
                        service=service,
                        commit_sha=rel.get("target_commitish", ""),
                        deployed_at=rel.get("published_at") or rel.get("created_at", ""),
                        environment="production" if not rel.get("prerelease") else "staging",
                        changelog_summary=rel.get("name") or rel.get("body") or "",
                    )
                    for rel in releases
                ]
        except httpx.TimeoutException:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout_seconds}s during get_deployment_history")
        except httpx.RequestError as e:
            raise GitHubAPIError(f"GitHub network error during get_deployment_history: {Sanitizer.sanitize(str(e))}")

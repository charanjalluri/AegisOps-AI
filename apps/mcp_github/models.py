"""
AegisOps AI - GitHub MCP Pydantic V2 Models
Structured schemas for commits, pull requests, file diffs, changed files, and deployment releases.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CommitItem(BaseModel):
    sha: str
    short_sha: str
    author: str
    date: str
    message: str
    service: str = "payment-service"


class CommitDetail(BaseModel):
    sha: str
    short_sha: str
    author: str
    date: str
    message: str
    service: str = "payment-service"
    files_changed_count: int
    insertions: int
    deletions: int
    diff: str
    token_count: int = 0
    truncated: bool = False


class PullRequestItem(BaseModel):
    number: int
    title: str
    author: str
    state: str  # "open", "merged", "closed"
    created_at: str
    merged_at: Optional[str] = None
    merge_commit_sha: Optional[str] = None
    description: str
    service: str = "payment-service"


class ChangedFileItem(BaseModel):
    filename: str
    status: str  # "modified", "added", "removed"
    additions: int
    deletions: int
    patch: Optional[str] = None


class DeploymentReleaseItem(BaseModel):
    release_tag: str
    service: str = "payment-service"
    commit_sha: str
    deployed_at: str
    environment: str = "staging"
    changelog_summary: str


class RecentCommitsInput(BaseModel):
    service: str = Field(default="payment-service", description="Target microservice name")
    limit: int = Field(default=10, ge=1, le=50, description="Max commits to return")
    branch: str = Field(default="main", description="Branch name")


class GetCommitInput(BaseModel):
    service: str = Field(default="payment-service", description="Target microservice name")
    commit_sha: str = Field(description="Full or short git commit SHA")


class PullRequestsInput(BaseModel):
    service: str = Field(default="payment-service", description="Target microservice name")
    state: str = Field(default="all", description="PR state: all, open, closed, or merged")
    limit: int = Field(default=10, ge=1, le=50, description="Max PRs to return")


class ChangedFilesInput(BaseModel):
    service: str = Field(default="payment-service", description="Target microservice name")
    commit_sha_or_pr: str = Field(description="Commit SHA or PR number (e.g. '42' or 'c0ffee1')")


class DeploymentHistoryInput(BaseModel):
    service: str = Field(default="payment-service", description="Target microservice name")
    limit: int = Field(default=10, ge=1, le=50, description="Max release records to return")

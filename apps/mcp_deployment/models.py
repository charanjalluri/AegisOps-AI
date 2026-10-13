"""
AegisOps AI - Deployment MCP Data Models (MCP-06)
Defines Pydantic V2 models for service versions, rollback requests/results,
and process restarts.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DeploymentInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Service identifier (e.g. payment-service)")
    version: str = Field(..., description="Application version tag (e.g. v2.8.1)")
    git_commit: str = Field(..., description="Git commit SHA associated with the deployment")
    deployed_at: str = Field(..., description="ISO-8601 deployment timestamp")
    status: str = Field(default="active", description="Deployment status (active, retired, failed)")
    is_current: bool = Field(default=True, description="Whether this is the currently active version")
    image_tag: Optional[str] = Field(default=None, description="Container image tag")
    environment: str = Field(default="production", description="Target environment")


class GetServiceVersionInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Service identifier (e.g. payment-service)")


class GetDeploymentHistoryInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Service identifier (e.g. payment-service)")
    limit: int = Field(default=5, description="Maximum number of historical records to return")


class RollbackRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Target service to roll back")
    target_version: str = Field(..., description="Version tag to roll back to (e.g. v2.8.0)")
    proposal_id: str = Field(..., description="Approved action proposal UUID from policy engine")
    reason: Optional[str] = Field(default=None, description="Optional operator rationale")


class RollbackResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str
    previous_version: str
    current_version: str
    status: str = "success"
    proposal_id: str
    executed_at: str
    message: str
    reverted_commit: Optional[str] = None


class RestartRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str = Field(..., description="Target service to restart")
    proposal_id: Optional[str] = Field(default=None, description="Optional action proposal ID")
    reason: Optional[str] = Field(default=None, description="Optional rationale")


class RestartResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    service: str
    status: str = "success"
    restarted_at: str
    message: str

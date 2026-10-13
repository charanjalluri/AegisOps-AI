"""
AegisOps AI - n8n MCP Data Models (MCP-07)
Defines Pydantic V2 models for workflow execution, status introspection,
and external notification payloads.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkflowExecutionInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_name: str = Field(..., description="Target workflow name or webhook path (e.g. incident-alert-slack)")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Workflow input parameters / payload data")


class WorkflowExecutionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_name: str
    execution_id: str
    status: str = "success"
    response: Dict[str, Any] = Field(default_factory=dict)
    executed_at: str
    is_mock: bool = False
    message: Optional[str] = None


class WorkflowStatusInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    execution_id: str = Field(..., description="Workflow execution ID")


class WorkflowStatusResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    execution_id: str
    status: str = "success"
    started_at: str
    finished_at: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

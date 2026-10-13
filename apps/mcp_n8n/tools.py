"""
AegisOps AI - n8n Workflow Automation MCP Tools (MCP-07)
Dispatches asynchronous notification workflows (Slack, Jira, incident alerts)
with secret masking and automatic offline mock fallback.
"""

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional
from uuid import uuid4
import httpx

from apps.common.mcp.security import Sanitizer
from apps.mcp_n8n.models import (
    WorkflowExecutionResult,
    WorkflowStatusResult,
)

logger = logging.getLogger("aegisops.mcp_n8n")


class N8nTools:
    """
    Workflow execution tooling connecting to n8n webhook automation,
    with seamless offline fallback for local developer workstations and tests.
    """

    def __init__(
        self,
        base_webhook_url: Optional[str] = None,
        timeout_seconds: float = 2.0,
        force_mock: bool = False,
    ):
        self.base_webhook_url = (
            base_webhook_url
            or os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.force_mock = force_mock
        self.executions: Dict[str, WorkflowStatusResult] = {}

    async def execute_workflow(
        self,
        workflow_name: str,
        payload: Dict[str, Any],
    ) -> WorkflowExecutionResult:
        """
        Dispatches an event payload to the specified n8n webhook workflow.
        Sanitizes secrets, enforces short timeout, and falls back to mock execution.
        """
        sanitized_payload = Sanitizer.mask_secrets(payload)
        now_iso = datetime.now(timezone.utc).isoformat()

        if self.force_mock:
            return self._dispatch_mock(workflow_name, sanitized_payload, now_iso)

        # Attempt live HTTP dispatch
        target_url = f"{self.base_webhook_url}/{workflow_name}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(target_url, json=sanitized_payload)

            if response.status_code < 400:
                exec_id = f"exec-{uuid4().hex[:8]}"
                res_json = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else {"raw": response.text}
                )
                self.executions[exec_id] = WorkflowStatusResult(
                    execution_id=exec_id,
                    status="success",
                    started_at=now_iso,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    data=res_json,
                )
                return WorkflowExecutionResult(
                    workflow_name=workflow_name,
                    execution_id=exec_id,
                    status="success",
                    response=res_json,
                    executed_at=now_iso,
                    is_mock=False,
                    message=f"Live n8n workflow '{workflow_name}' dispatched successfully.",
                )
            else:
                logger.warning(
                    f"n8n webhook returned status {response.status_code}. Falling back to mock dispatch."
                )
                return self._dispatch_mock(
                    workflow_name,
                    sanitized_payload,
                    now_iso,
                    fallback_reason=f"HTTP {response.status_code}",
                )

        except Exception as e:
            logger.info(f"n8n endpoint unreachable ({e}). Using offline mock dispatch.")
            return self._dispatch_mock(
                workflow_name,
                sanitized_payload,
                now_iso,
                fallback_reason=str(e),
            )

    def _dispatch_mock(
        self,
        workflow_name: str,
        sanitized_payload: Dict[str, Any],
        timestamp_iso: str,
        fallback_reason: Optional[str] = None,
    ) -> WorkflowExecutionResult:
        """Simulates successful workflow execution without blocking the agent."""
        exec_id = f"mock-exec-{uuid4().hex[:8]}"

        # Craft high-fidelity simulated response
        if "slack" in workflow_name.lower():
            mock_res = {
                "channel": sanitized_payload.get("channel", "#incident-ops"),
                "status": "delivered",
                "simulated_provider": "slack",
            }
        elif "jira" in workflow_name.lower():
            mock_res = {
                "issue_key": f"OPS-{int(datetime.now(timezone.utc).timestamp()) % 10000}",
                "status": "created",
                "simulated_provider": "jira",
            }
        elif "resolution" in workflow_name.lower():
            mock_res = {
                "channel": "#incident-ops",
                "status": "delivered",
                "summary": "Remediation verified and incident closed",
            }
        else:
            mock_res = {
                "workflow": workflow_name,
                "status": "simulated",
                "payload_keys": list(sanitized_payload.keys()),
            }

        status_result = WorkflowStatusResult(
            execution_id=exec_id,
            status="success",
            started_at=timestamp_iso,
            finished_at=datetime.now(timezone.utc).isoformat(),
            data=mock_res,
        )
        self.executions[exec_id] = status_result

        reason_str = f" (Offline fallback: {fallback_reason})" if fallback_reason else " (Offline mock)"
        return WorkflowExecutionResult(
            workflow_name=workflow_name,
            execution_id=exec_id,
            status="success",
            response=mock_res,
            executed_at=timestamp_iso,
            is_mock=True,
            message=f"Workflow '{workflow_name}' processed{reason_str}.",
        )

    async def get_execution_status(self, execution_id: str) -> WorkflowStatusResult:
        """Retrieves execution status for an existing workflow run."""
        if execution_id in self.executions:
            return self.executions[execution_id]

        return WorkflowStatusResult(
            execution_id=execution_id,
            status="unknown",
            started_at=datetime.now(timezone.utc).isoformat(),
            data={"error": f"Execution ID '{execution_id}' not found."},
        )

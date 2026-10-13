"""
AegisOps AI - Deployment MCP Tools (MCP-06)
Provides inspection of service deployment versions and policy-gated rollback execution.
Rollbacks are strictly rejected with PolicyViolationError (-32003) unless authorized
via an approved action proposal in the policy engine.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from apps.common.mcp.protocol import PolicyViolationError
from apps.mcp_deployment.models import (
    DeploymentInfo,
    RestartRequest,
    RestartResult,
    RollbackRequest,
    RollbackResult,
)
from apps.mcp_incident.storage import InvestigationStorage
from apps.policy.approval import ApprovalManager
from apps.policy.engine import PolicyEngine


class DeploymentTools:
    """
    Controlled deployment management tooling with strict policy gating.
    """

    def __init__(
        self,
        storage: Optional[InvestigationStorage] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_manager: Optional[ApprovalManager] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        custom_deployments: Optional[Dict[str, List[DeploymentInfo]]] = None,
        database_tools: Optional[Any] = None,
    ):
        self.storage = storage or InvestigationStorage()
        self.policy_engine = policy_engine or PolicyEngine(storage=self.storage)
        self.approval_manager = approval_manager or ApprovalManager(
            storage=self.storage, event_emitter=event_emitter
        )
        self.event_emitter = event_emitter
        self.database_tools = database_tools
        self.deployments: Dict[str, List[DeploymentInfo]] = (
            custom_deployments if custom_deployments is not None else self._default_deployments()
        )

    def _default_deployments(self) -> Dict[str, List[DeploymentInfo]]:
        """Default realistic deployment history for target services."""
        return {
            "payment-service": [
                DeploymentInfo(
                    service="payment-service",
                    version="v2.8.1",
                    git_commit="c4a1b2c",
                    deployed_at="2026-10-12T14:30:00Z",
                    status="active",
                    is_current=True,
                    image_tag="payment-service:v2.8.1",
                    environment="production",
                ),
                DeploymentInfo(
                    service="payment-service",
                    version="v2.8.0",
                    git_commit="9b8a7c6",
                    deployed_at="2026-10-10T10:00:00Z",
                    status="retired",
                    is_current=False,
                    image_tag="payment-service:v2.8.0",
                    environment="production",
                ),
                DeploymentInfo(
                    service="payment-service",
                    version="v2.7.9",
                    git_commit="1a2b3c4",
                    deployed_at="2026-10-01T09:00:00Z",
                    status="retired",
                    is_current=False,
                    image_tag="payment-service:v2.7.9",
                    environment="production",
                ),
            ]
        }

    async def get_current_version(self, service: str) -> DeploymentInfo:
        """Returns the currently active deployment for the specified service."""
        history = self.deployments.get(service)
        if not history:
            raise ValueError(f"Service '{service}' not found in deployment inventory.")

        for dep in history:
            if dep.is_current and dep.status == "active":
                return dep

        # Fallback to first deployment
        return history[0]

    async def get_previous_version(self, service: str) -> DeploymentInfo:
        """Returns the previous stable deployment version prior to the current active release."""
        history = self.deployments.get(service)
        if not history:
            raise ValueError(f"Service '{service}' not found in deployment inventory.")

        # Find first retired deployment
        for dep in history:
            if not dep.is_current and dep.status == "retired":
                return dep

        if len(history) > 1:
            return history[1]
        return history[0]

    async def get_deployment_history(
        self, service: str, limit: int = 5
    ) -> List[DeploymentInfo]:
        """Returns the chronological deployment history for the specified service."""
        history = self.deployments.get(service, [])
        return history[:limit]

    async def rollback_deployment(
        self,
        service: str,
        target_version: str,
        proposal_id: str,
    ) -> RollbackResult:
        """
        Rolls back the target service to a target version.
        MANDATORY: Requires an approved action proposal ID verified through PolicyEngine.
        Raises PolicyViolationError (-32003) if proposal is missing, unapproved, or rejected.
        """
        # 1. Strictly validate through PolicyEngine
        try:
            await self.policy_engine.validate_execution_allowed(
                proposal_id=proposal_id,
                action_type="rollback_deployment",
                parameters={"service": service, "target_version": target_version},
            )
        except Exception as e:
            raise PolicyViolationError(
                f"Policy violation: action rejected. Proposal must be approved by an authorized operator. Details: {str(e)}"
            )

        # 2. Locate service history
        history = self.deployments.get(service)
        if not history:
            raise ValueError(f"Service '{service}' not found in deployment inventory.")

        # Identify current version and target version
        current_dep: Optional[DeploymentInfo] = None
        target_dep: Optional[DeploymentInfo] = None

        for dep in history:
            if dep.is_current:
                current_dep = dep
            if dep.version == target_version:
                target_dep = dep

        previous_version_str = current_dep.version if current_dep else "unknown"

        # Update deployment state
        if current_dep:
            current_dep.is_current = False
            current_dep.status = "retired"

        if target_dep:
            target_dep.is_current = True
            target_dep.status = "active"
            reverted_commit = target_dep.git_commit
        else:
            # Create entry for target version if absent
            target_dep = DeploymentInfo(
                service=service,
                version=target_version,
                git_commit="reverted-sha",
                deployed_at=datetime.now(timezone.utc).isoformat(),
                status="active",
                is_current=True,
                environment="production",
            )
            history.insert(0, target_dep)
            reverted_commit = target_dep.git_commit

        # 3. Reset connection pool leak in simulator if connected
        if self.database_tools and hasattr(self.database_tools, "mock_data"):
            pool_data = self.database_tools.mock_data.get("pool", {})
            pool_data["active_connections"] = 2
            pool_data["total_connections"] = 8
            pool_data["waiting_connections"] = 0

        # 4. Mark proposal executed in storage and audit log
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            await self.approval_manager.mark_proposal_executed(
                proposal_id=proposal_id,
                details={
                    "service": service,
                    "target_version": target_version,
                    "previous_version": previous_version_str,
                },
            )
        except Exception:
            pass

        # 5. Emit deployment event
        if self.event_emitter:
            dep_event = {
                "event_id": str(uuid4()),
                "service": service,
                "event_type": "DEPLOYMENT_ROLLBACK",
                "previous_version": previous_version_str,
                "current_version": target_version,
                "proposal_id": proposal_id,
                "timestamp": now_iso,
            }
            res = self.event_emitter("deployments.events", dep_event)
            if hasattr(res, "__await__"):
                await res

        return RollbackResult(
            service=service,
            previous_version=previous_version_str,
            current_version=target_version,
            status="success",
            proposal_id=proposal_id,
            executed_at=now_iso,
            message=f"Service '{service}' successfully rolled back from {previous_version_str} to {target_version}.",
            reverted_commit=reverted_commit,
        )

    async def restart_service(
        self,
        service: str,
        proposal_id: Optional[str] = None,
    ) -> RestartResult:
        """Restarts the simulated service process."""
        history = self.deployments.get(service)
        if not history:
            raise ValueError(f"Service '{service}' not found in deployment inventory.")

        now_iso = datetime.now(timezone.utc).isoformat()

        if proposal_id:
            try:
                await self.approval_manager.mark_proposal_executed(
                    proposal_id=proposal_id,
                    details={"service": service, "action": "restart_service"},
                )
            except Exception:
                pass

        return RestartResult(
            service=service,
            status="success",
            restarted_at=now_iso,
            message=f"Service '{service}' restarted successfully.",
        )

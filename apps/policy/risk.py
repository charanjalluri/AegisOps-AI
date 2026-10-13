"""
AegisOps AI - Action Risk Classifier (GOV-01)
Categorizes operational actions and tools into 5 risk tiers:
READ, LOW, MEDIUM, HIGH, and DESTRUCTIVE.
"""

from typing import Any, Dict, Optional, Set
from apps.policy.models import RiskTier


class RiskClassifier:
    """
    Evaluates action types and parameters to classify operational risk level.
    """

    DESTRUCTIVE_KEYWORDS: Set[str] = {
        "drop_table",
        "drop table",
        "delete_data",
        "delete from",
        "delete_from",
        "truncate_table",
        "truncate",
        "delete_database",
        "drop_database",
        "drop database",
        "drop_schema",
        "drop schema",
        "drop_bucket",
        "drop bucket",
        "destroy",
        "rm -rf",
    }

    READ_TOOLS: Set[str] = {
        "search_logs",
        "get_service_logs",
        "get_error_rate",
        "get_correlated_errors",
        "get_logs_around_event",
        "get_database_health",
        "get_connection_pool",
        "get_slow_queries",
        "get_active_connections",
        "run_readonly_query",
        "get_recent_commits",
        "get_commit",
        "get_pull_requests",
        "get_changed_files",
        "get_deployment_history",
        "get_current_version",
        "get_previous_version",
        "qdrant_search",
        "get_document",
        "get_incident",
        "list_incidents",
        "get_execution_status",
    }

    LOW_RISK_TOOLS: Set[str] = {
        "n8n_notify_slack",
        "n8n_create_jira",
        "send_alert",
        "execute_workflow",
        "send_email",
        "notify_channel",
        "annotate_metric",
    }

    MEDIUM_RISK_TOOLS: Set[str] = {
        "restart_service",
        "reload_configuration",
        "clear_cache",
    }

    HIGH_RISK_TOOLS: Set[str] = {
        "rollback_deployment",
        "scale_replicas",
        "apply_migration",
        "failover_database",
    }

    @classmethod
    def classify(
        cls,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        environment: str = "production",
    ) -> RiskTier:
        """
        Classifies action risk level based on action name, parameters, and environment.
        """
        norm_name = action_type.strip().lower()
        params = parameters or {}

        # 1. Destructive check (absolute prohibition)
        for kw in cls.DESTRUCTIVE_KEYWORDS:
            if kw in norm_name:
                return RiskTier.DESTRUCTIVE

        # Check raw query strings or statements if passed
        query = str(params.get("query", "")).lower()
        sql = str(params.get("sql", "")).lower()
        cmd = str(params.get("command", "")).lower()
        for kw in cls.DESTRUCTIVE_KEYWORDS:
            if kw in query or kw in sql or kw in cmd:
                return RiskTier.DESTRUCTIVE

        # 2. Known READ tools
        if norm_name in cls.READ_TOOLS or norm_name.startswith(("get_", "search_", "list_", "read_")):
            return RiskTier.READ

        # 3. Known LOW risk tools
        if norm_name in cls.LOW_RISK_TOOLS or "notify" in norm_name or "alert" in norm_name:
            return RiskTier.LOW

        # 4. Rollback and high-impact actions
        if norm_name in cls.HIGH_RISK_TOOLS or "rollback" in norm_name or "scale" in norm_name:
            return RiskTier.HIGH

        # 5. Medium risk actions (e.g. restart service in non-production)
        if norm_name in cls.MEDIUM_RISK_TOOLS or "restart" in norm_name or "reload" in norm_name:
            # If target environment is explicitly production, escalate restart to HIGH
            env = str(params.get("environment", environment)).lower()
            if env in ("prod", "production"):
                return RiskTier.HIGH
            return RiskTier.MEDIUM

        # Default fallback: safe default to HIGH for any unknown mutating action
        if any(prefix in norm_name for prefix in ("delete", "drop", "truncate", "destroy")):
            return RiskTier.DESTRUCTIVE

        return RiskTier.HIGH

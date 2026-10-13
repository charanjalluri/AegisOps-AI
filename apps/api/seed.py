"""
AegisOps AI — Demo Data Seeder for Development & Dashboard Visualization
Populates initial rich incidents, evidence, hypotheses, action proposals, and audit events.
"""

from datetime import datetime, timezone
from apps.api.dependencies import get_storage


async def seed_demo_incidents():
    """Seeds rich demo incidents into platform storage if storage is currently empty."""
    storage = get_storage()
    existing = await storage.list_incidents(limit=1)
    if existing:
        return

    now_iso = datetime.now(timezone.utc).isoformat()

    # -------------------------------------------------------------------------
    # Incident 1: Flagship Connection Pool Leak (SEV-1, Investigating / Action Proposed)
    # -------------------------------------------------------------------------
    inc1 = await storage.create_incident(
        incident_id="INC-2026-0891",
        title="Payment Service Database Connection Pool Saturation",
        service="payment-service",
        severity="SEV-1",
        summary="Release v2.8.1 introduced an unclosed connection leak in /payments endpoint causing 100% pool saturation (50/50 connections) and 28.4% 500 error rate.",
    )
    await storage.update_incident(inc1.incident_id, status="investigating")

    # Evidence for Inc 1
    await storage.add_evidence(
        incident_id=inc1.incident_id,
        source_tool="mcp_logs",
        signal_type="log_error",
        confidence_weight=0.95,
        raw_data={
            "error": "asyncpg.exceptions.TooManyConnectionsError",
            "message": "remaining connection slots are reserved for non-replication superuser connections",
            "endpoint": "/payments",
            "service": "payment-service",
            "version": "v2.8.1",
            "sample_count": 84,
        },
        interpretation="High volume of connection exhaustion errors from payment-service /payments handler.",
    )

    await storage.add_evidence(
        incident_id=inc1.incident_id,
        source_tool="mcp_database",
        signal_type="metric_anomaly",
        confidence_weight=0.98,
        raw_data={
            "metric": "active_connections",
            "current_value": 50,
            "max_capacity": 50,
            "utilization_pct": 100.0,
            "blocked_queries": 32,
            "p95_checkout_latency_ms": 1850.0,
        },
        interpretation="Database pool reached maximum capacity (50/50), blocking transaction queries.",
    )

    await storage.add_evidence(
        incident_id=inc1.incident_id,
        source_tool="mcp_github",
        signal_type="git_commit",
        confidence_weight=0.90,
        raw_data={
            "commit_sha": "9b8a7c6",
            "author": "dev@aegisops.ai",
            "message": "Release v2.8.1: optimize checkout flow with connection caching",
            "changed_files": ["apps/payment_service/main.py"],
            "suspicious_diff": "+ conn = await pool.acquire() # missing release",
        },
        interpretation="Recent deployment commit 9b8a7c6 modified DB connection handling without releasing connection on error.",
    )

    await storage.add_evidence(
        incident_id=inc1.incident_id,
        source_tool="semantic_memory",
        signal_type="knowledge_rag",
        confidence_weight=0.92,
        raw_data={
            "matched_incident": "INC-2025-1102",
            "title": "PostgreSQL pool exhaustion after v2.4 upgrade",
            "similarity_score": 0.94,
            "verified_resolution": "Rollback to prior version v2.3.9 immediately restored connection pool baseline",
        },
        interpretation="Vector similarity matched historical incident INC-2025-1102 with 94% confidence.",
    )

    # Hypotheses for Inc 1
    await storage.add_or_update_hypothesis(
        incident_id=inc1.incident_id,
        title="Unclosed database connection leak introduced in release v2.8.1",
        confidence_score=0.92,
        status="validated",
        rationale="Strongly supported by commit 9b8a7c6 diff, 100% active connection saturation, and 94% similarity to past postmortem INC-2025-1102.",
        supporting_evidence=["mcp_logs:TooManyConnectionsError", "mcp_database:50/50 connections", "mcp_github:9b8a7c6", "semantic_memory:INC-2025-1102"],
        refuting_evidence=[],
    )

    await storage.add_or_update_hypothesis(
        incident_id=inc1.incident_id,
        title="External payment gateway DDOS traffic spike",
        confidence_score=0.25,
        status="refuted",
        rationale="Request volume is nominal (120 req/s, +2% vs 7-day average); error rate is localized strictly to database checkout timeout.",
        supporting_evidence=[],
        refuting_evidence=["mcp_logs:nominal_traffic_rate"],
    )

    await storage.add_or_update_hypothesis(
        incident_id=inc1.incident_id,
        title="PostgreSQL server hardware exhaustion or CPU starvation",
        confidence_score=0.15,
        status="refuted",
        rationale="Database host CPU utilization is at 14% and memory utilization is nominal.",
        supporting_evidence=[],
        refuting_evidence=["mcp_database:cpu_nominal_14%"],
    )

    # Tool execution history for Inc 1
    for tool_name, dur in [
        ("qdrant_search", 32.0),
        ("get_error_rate", 18.0),
        ("get_connection_pool", 24.0),
        ("get_deployment_history", 15.0),
        ("get_recent_commits", 21.0),
    ]:
        await storage.record_tool_history(
            incident_id=inc1.incident_id,
            tool_name=tool_name,
            caller="agent_investigation_graph",
            arguments={"service": "payment-service", "window_minutes": 15},
            duration_ms=dur,
            status="success",
            result_summary="Returned diagnostic telemetry and corroborating evidence",
        )

    # Action Proposal for Inc 1
    await storage.create_action_proposal(
        incident_id=inc1.incident_id,
        action_type="rollback_deployment",
        parameters={"service": "payment-service", "target_version": "v2.8.0"},
        risk_level="HIGH",
        rationale="High-risk production rollback: revert payment-service from leaking v2.8.1 to proven v2.8.0 to immediately release exhausted connections.",
        proposal_id="prop-demo-001",
    )

    # -------------------------------------------------------------------------
    # Incident 2: Gateway Latency Spike (SEV-2, Mitigating)
    # -------------------------------------------------------------------------
    inc2 = await storage.create_incident(
        incident_id="INC-2026-0885",
        title="Order Gateway P95 Latency Degradation",
        service="order-gateway",
        severity="SEV-2",
        summary="Upstream dependency timeout causing order checkout latency to spike to 2150ms.",
    )
    await storage.update_incident(inc2.incident_id, status="mitigating")

    await storage.add_or_update_hypothesis(
        incident_id=inc2.incident_id,
        title="Fraud inspection microservice timeout causing cascade delay",
        confidence_score=0.84,
        status="validated",
        rationale="Corroborated by upstream 504 Gateway Timeout logs on the fraud-detection hook.",
    )

    # -------------------------------------------------------------------------
    # Incident 3: Notification Worker Lag (SEV-3, Resolved)
    # -------------------------------------------------------------------------
    inc3 = await storage.create_incident(
        incident_id="INC-2026-0870",
        title="Notification Dispatch Worker Queue Lag",
        service="notification-worker",
        severity="SEV-3",
        summary="Redis queue consumer lag exceeded 5,000 pending messages during promotional blast.",
    )
    await storage.close_incident(
        incident_id=inc3.incident_id,
        root_cause="Redis consumer lag during promotional notification surge",
        summary="Auto-scaler increased consumer replicas from 2 to 8. Queue cleared in 3.2 minutes.",
    )

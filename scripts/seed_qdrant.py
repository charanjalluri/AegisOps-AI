"""
AegisOps AI - Qdrant Semantic Memory Seeder (MEM-03)
Prepopulates Qdrant vector database with realistic historical incidents,
postmortems, and operational troubleshooting runbooks.
"""

import argparse
import asyncio
import os
import sys
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.agent.memory.models import CollectionConfig, DocumentType, KnowledgeDocument
from apps.agent.memory.qdrant import QdrantMemoryClient


HISTORICAL_DOCUMENTS: List[KnowledgeDocument] = [
    # 1. Database Connection Pool Leaks
    KnowledgeDocument(
        id="INC-2025-089",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Payment Service Connection Pool Leak in v2.7.2",
        root_cause="Unclosed database connection session in new refund retry endpoint introduced in PR #214.",
        symptoms=[
            "HTTP 500 Internal Server Error spike to 35%",
            "Active connections reached max_connections (50/50)",
            "Waiting connection queue exceeded 120 clients",
            "Latency p99 spiked from 45ms to 12,000ms",
        ],
        resolution="Rolled back deployment from v2.7.2 to v2.7.1; patched session context manager with try/finally.",
        tags=["database", "connection-pool", "leak", "postgres", "payment-service", "rollback"],
        text="On 2025-08-14, payment-service v2.7.2 deployment triggered severe pool exhaustion. The refund retry logic failed to release PostgreSQL connections back to the Hikari pool, leading to connection starvation and cascading 500 errors within 8 minutes of release.",
    ),
    KnowledgeDocument(
        id="PM-2025-089",
        document_type=DocumentType.POSTMORTEM,
        service="payment-service",
        title="Postmortem: Connection Pool Starvation Incident INC-2025-089",
        root_cause="Database connection leak caused by omission of async with pool.acquire() in error handling block.",
        symptoms=["Pool exhaustion", "500 error spike", "Latency spike", "Connection timeout"],
        resolution="Emergency rollback to v2.7.1 followed by static analysis lint rule enforcing context managers for database queries.",
        tags=["postmortem", "connection-pool", "payment-service", "governance"],
        text="Comprehensive postmortem detailing the 22-minute downtime caused by payment-service v2.7.2 connection pool leak. Key learning: all database connection checkouts must be wrapped in strictly bounded timeouts and context managers.",
    ),
    KnowledgeDocument(
        id="INC-2026-002",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="PostgreSQL Max Connections Reached on Payment DB",
        root_cause="Background transaction cleanup worker spawned unbounded parallel client connections.",
        symptoms=["FATAL: remaining connection slots are reserved for non-replication superuser connections", "500 errors across all payment endpoints"],
        resolution="Terminated rogue worker pids via pg_terminate_backend and capped worker concurrency to 5.",
        tags=["postgres", "max-connections", "deadlock", "payment-service"],
        text="Transaction cleanup cron job spawned 200 concurrent tasks on demo_payment_db, rapidly exhausting available PostgreSQL connection slots and locking out user requests.",
    ),
    KnowledgeDocument(
        id="INC-2026-042",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Payment Service Database Timeout Spike in v2.8.1",
        root_cause="PR #42 in commit 8f9b2d1 omitted connection release in process_payment database transaction block.",
        symptoms=[
            "Active connections reached 50/50 maximum capacity",
            "Error rate rose to 28% with PostgreSQL connection acquisition timeout",
            "Latency p99 exceeded 8,000ms",
        ],
        resolution="Immediate controlled rollback to v2.8.0 restored connection pool health immediately.",
        tags=["database", "connection-leak", "v2.8.1", "payment-service", "rollback"],
        text="Deployment of payment-service v2.8.1 introduced a connection pool leak in the core checkout pathway. Connections were acquired but never returned to the pool on client timeout, resulting in full pool saturation.",
    ),

    # 2. Memory Leaks and OOM
    KnowledgeDocument(
        id="INC-2025-104",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Worker Container OOMKilled Following Memory Leak",
        root_cause="Unbounded in-memory queue retaining completed payment event payloads for auditing.",
        symptoms=["Container restarted with exit code 137 (OOMKilled)", "Memory usage climbed steadily to 2GB limit"],
        resolution="Replaced in-memory payload buffer with disk-backed streaming queue.",
        tags=["memory", "oom", "leak", "containers"],
        text="Payment service container crashed repeatedly under moderate load due to unbounded heap growth in the in-memory audit listener.",
    ),
    KnowledgeDocument(
        id="INC-2026-018",
        document_type=DocumentType.INCIDENT,
        service="notification-service",
        title="Notification Dispatcher Memory Exhaustion",
        root_cause="Circular references in async callback closures preventing garbage collection.",
        symptoms=["RSS memory growth > 50MB/min", "Worker process killed by system OOM daemon"],
        resolution="Refactored callbacks to use weak references and explicit cleanup handlers.",
        tags=["memory", "gc", "async", "notification-service"],
        text="Notification dispatcher experienced progressive memory creep over 6 hours, culminating in OOM termination during peak transaction periods.",
    ),

    # 3. Bad Deployments & Configuration Regressions
    KnowledgeDocument(
        id="INC-2026-012",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Missing DB_POOL_TIMEOUT Environment Variable in v2.7.4",
        root_cause="Helm chart update renamed POOL_TIMEOUT_MS to DB_POOL_TIMEOUT, causing fallback to infinite timeout.",
        symptoms=["Threads blocked indefinitely waiting for database pool slots", "Zero errors logged but zero HTTP responses returned"],
        resolution="Updated environment variables to supply DB_POOL_TIMEOUT=5000 and restarted pods.",
        tags=["configuration", "deployment", "timeout", "helm"],
        text="Configuration mismatch led to indefinite thread blocking when connection pool was exhausted, completely hanging the payment service without explicit error logs.",
    ),
    KnowledgeDocument(
        id="INC-2025-055",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Write Operations Directed to Read-Only Database Replica",
        root_cause="Database URL pointed to replica endpoint after terraform variable override.",
        symptoms=["ERROR: cannot execute INSERT in a read-only transaction", "100% failure rate on payment creation"],
        resolution="Corrected DATABASE_URL environment variable to primary database writer endpoint.",
        tags=["configuration", "database", "read-only", "replica"],
        text="Payment service was misconfigured to connect to a read replica instead of primary PostgreSQL writer, breaking all transaction inserts immediately upon boot.",
    ),
    KnowledgeDocument(
        id="INC-2026-029",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Synchronous Remote Call Added to Request Middleware",
        root_cause="v2.7.6 release added synchronous HTTP auth check to every incoming request without connection timeout.",
        symptoms=["Latency increased from 20ms to 4,500ms", "Connection backlog filled up"],
        resolution="Rolled back v2.7.6 release and converted auth check to asynchronous token verification.",
        tags=["deployment", "middleware", "latency", "rollback"],
        text="Blocking synchronous HTTP call introduced in v2.7.6 middleware caused thread starvation under high request concurrency.",
    ),

    # 4. Slow Queries and Missing Indexes
    KnowledgeDocument(
        id="INC-2025-045",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Unindexed Query on payments Table Causing Full Table Scan",
        root_cause="New dashboard filter query executed SELECT * FROM payments WHERE customer_id = ... without index on customer_id.",
        symptoms=["CPU utilization on Postgres reached 98%", "Queries taking > 6,000ms", "504 Gateway Timeouts"],
        resolution="Created index CONCURRENTLY idx_payments_customer_id ON payments (customer_id).",
        tags=["postgres", "slow-query", "index", "cpu"],
        text="A missing index on customer_id caused PostgreSQL to execute sequential table scans over 4 million payment records, saturating CPU and delaying all queries.",
    ),
    KnowledgeDocument(
        id="INC-2026-008",
        document_type=DocumentType.INCIDENT,
        service="order-service",
        title="N+1 Query Regression in Transaction History API",
        root_cause="ORM lazy-loading triggered 100 individual database queries per list request.",
        symptoms=["Postgres transaction rate spiked 50x", "Database pool latency increased 800%"],
        resolution="Added eager join fetching to order queries in repository layer.",
        tags=["database", "orm", "slow-query", "n-plus-one"],
        text="List orders endpoint triggered hundreds of sub-queries per request, overloading the database connection pool with short-lived queries.",
    ),

    # 5. Upstream Service & Gateway Failures
    KnowledgeDocument(
        id="INC-2026-033",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Third-Party Banking Gateway 429 Rate Limiting",
        root_cause="External payment processor enforced unannounced rate limit of 100 req/sec during marketing campaign.",
        symptoms=["HTTP 429 Too Many Requests received from upstream", "Outbound retry storm amplified load"],
        resolution="Enabled exponential backoff with jitter and circuit breaker on upstream client.",
        tags=["upstream", "rate-limit", "circuit-breaker", "gateway"],
        text="External gateway rate limiting caused payment-service retry loop, consuming local worker threads and causing secondary failures.",
    ),
    KnowledgeDocument(
        id="INC-2025-062",
        document_type=DocumentType.INCIDENT,
        service="event-ingestion",
        title="Kafka Consumer Group Rebalance Storm",
        root_cause="Heartbeat timeout exceeded by consumer processing large batch messages.",
        symptoms=["Consumer lag grew to 500,000 messages", "Continuous partition rebalancing logged"],
        resolution="Decreased max.poll.records to 100 and increased max.poll.interval.ms to 300,000ms.",
        tags=["kafka", "consumer-lag", "rebalance", "streaming"],
        text="Event ingestion pipeline stalled as consumers were repeatedly kicked from consumer group due to long message processing durations.",
    ),

    # 6. Operational Runbooks
    KnowledgeDocument(
        id="RB-PAY-01",
        document_type=DocumentType.RUNBOOK,
        service="payment-service",
        title="Payment Service DB Pool Recovery Runbook",
        root_cause="Operational procedure for database connection pool exhaustion",
        symptoms=[
            "Active connections >= 45/50",
            "Waiting connection queue > 20",
            "500 error rate > 5%",
        ],
        resolution="""1. Check pg_stat_activity in demo_payment_db to verify if queries are stuck or connections leaked.
2. If queries are idle in transaction, check recent deployments for unreleased connections.
3. If new version was deployed within last 30 minutes, execute emergency rollback:
   - Run Deployment MCP rollback_deployment(service='payment-service', target_version='previous').
4. Verify active connections drop below 15 and 500 error rate returns to 0%.
5. Notify on-call channel in Slack with incident ticket.""",
        tags=["runbook", "database", "connection-pool", "payment-service", "recovery"],
        text="Step-by-step procedure for diagnosing and recovering from database connection pool starvation in payment-service. Covers pg_stat_activity inspection, deployment correlation, and safe rollback triggers.",
    ),
    KnowledgeDocument(
        id="RB-PAY-02",
        document_type=DocumentType.RUNBOOK,
        service="payment-service",
        title="Payment Service Emergency Rollback Procedure",
        root_cause="Standard operating procedure for fast release rollback",
        symptoms=["Critical error spike following deployment", "Unresolved SEV-1 or SEV-2 anomaly"],
        resolution="""1. Confirm target rollback version from GitHub MCP deployment history.
2. Obtain approval for HIGH-risk rollback action.
3. Execute rollback via deployment controller to previous stable git tag.
4. Monitor telemetry for 3 minutes: error rate < 1%, latency p99 < 100ms.
5. Create follow-up investigation ticket.""",
        tags=["runbook", "rollback", "deployment", "payment-service", "procedure"],
        text="Operational guide for executing safe rollbacks of payment-service. Details verification checklist before and after rolling back container versions.",
    ),
    KnowledgeDocument(
        id="RB-DB-01",
        document_type=DocumentType.RUNBOOK,
        service="database",
        title="PostgreSQL Connection Starvation & Lock Mitigation",
        root_cause="Operational procedure for database server connection limits",
        symptoms=["FATAL: too many connections", "Locks in pg_locks table", "Transaction pileups"],
        resolution="""1. Run Database MCP get_active_connections to find longest running queries.
2. Identify blocking lock pids via pg_blocking_pids.
3. Terminate blocking backend if non-critical.
4. Scale connection pooler (pgBouncer/Hikari) if legitimate traffic spike.
5. Review slow query log via Database MCP get_slow_queries.""",
        tags=["runbook", "postgres", "locks", "database"],
        text="Guide for database administrators to clear connection starvation, unlock frozen tables, and terminate hanging client sessions safely.",
    ),
    KnowledgeDocument(
        id="RB-KAFKA-01",
        document_type=DocumentType.RUNBOOK,
        service="event-backbone",
        title="Kafka Consumer Lag & Rebalance Troubleshooting",
        root_cause="Operational procedure for streaming pipeline backlog",
        symptoms=["Consumer lag rising continuously", "Topic throughput dropping"],
        resolution="""1. Check consumer container health and CPU utilization.
2. Inspect Kafka UI at :8080 to identify lagging partitions.
3. Verify database write latency downstream.
4. Increase consumer replicas if partition count allows.
5. Restart stuck consumer pods sequentially.""",
        tags=["runbook", "kafka", "lag", "streaming"],
        text="Troubleshooting guide for diagnosing high consumer lag, resolving partition assignment deadlocks, and restoring stream processing throughput.",
    ),
    KnowledgeDocument(
        id="RB-MEM-01",
        document_type=DocumentType.RUNBOOK,
        service="payment-service",
        title="High Memory Usage & Container OOM Mitigation",
        root_cause="Operational procedure for container memory leaks",
        symptoms=["Memory usage > 85%", "Pod restart count > 2 in 10 minutes"],
        resolution="""1. Take heap dump or memory profile if diagnostics enabled.
2. Restart container to relieve immediate customer impact.
3. Check memory trend over last 6 hours to differentiate leak from traffic surge.
4. If leak followed recent commit, prepare rollback or hotfix.
5. Adjust container memory limits temporarily if traffic related.""",
        tags=["runbook", "memory", "oom", "containers"],
        text="Standard operating procedure for handling memory leaks, container restart loops, and heap allocation anomalies across microservices.",
    ),
    KnowledgeDocument(
        id="INC-2026-051",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Stale Read Replica Replication Lag Triggering Payment Verification Failures",
        root_cause="Secondary PostgreSQL replica replication lag exceeded 45 seconds due to heavy table autovacuum, serving stale idempotency keys.",
        symptoms=[
            "Duplicate transaction attempt rejections",
            "Replication lag metric > 40s",
            "Elevated 409 Conflict responses on /checkout",
        ],
        resolution="Configured critical idempotency verification checks to route exclusively to primary database master; tuned autovacuum cost limit.",
        tags=["database", "replication-lag", "postgres", "payment-service", "idempotency"],
        text="On 2026-06-12, payment-service experienced false duplicate charge rejections when read queries hit a delayed replica. Replication lag had spiked to 45 seconds during table maintenance, causing recent authorization tokens to appear missing.",
    ),
    KnowledgeDocument(
        id="PM-2026-051",
        document_type=DocumentType.POSTMORTEM,
        service="payment-service",
        title="Postmortem: Replication Lag & Stale Read Inconsistency INC-2026-051",
        root_cause="Read-after-write consistency was not enforced for authorization state checks, exposing transactions to replication delays.",
        symptoms=["409 Conflict spikes", "Customer retry storms", "Replication lag alert trigger"],
        resolution="Added session-level sticky routing to primary database for 60 seconds following any state mutation; established automated alert on pg_stat_replication lag.",
        tags=["postmortem", "replication-lag", "consistency", "payment-service"],
        text="Postmortem analyzing checkout authorization failures caused by database replication delays. Implemented sticky primary routing for write-followed-by-read flows and added circuit breakers for stale replica read fallback.",
    ),
]


async def seed_qdrant(
    url: str = "http://localhost:6333",
    collection_name: str = "aegisops_knowledge",
    force: bool = False,
    dry_run: bool = False,
    offline_mode: bool = False,
) -> int:
    """Seeds Qdrant vector database with operational knowledge dataset."""
    print(f"[Seed] Preparing to seed {len(HISTORICAL_DOCUMENTS)} operational documents...")

    if dry_run:
        print(f"[Seed] DRY RUN: Would seed {len(HISTORICAL_DOCUMENTS)} documents into '{collection_name}' at {url}.")
        for doc in HISTORICAL_DOCUMENTS:
            print(f"  - [{doc.document_type.value.upper()}] {doc.id}: {doc.title} ({doc.service})")
        return len(HISTORICAL_DOCUMENTS)

    client = QdrantMemoryClient(url=url, offline_mode=offline_mode, timeout=1.0)
    await client.ensure_collection(CollectionConfig(collection_name=collection_name))

    count = await client.upsert_documents(HISTORICAL_DOCUMENTS, collection_name=collection_name)
    print(f"[Seed] Successfully seeded {count} operational documents into collection '{collection_name}'.")

    # Verify search
    probe = await client.search("connection pool exhausted", limit=1, collection_name=collection_name)
    if probe:
        print(f"[Seed] Verification query verified: Top match is '{probe[0].document.title}' (score: {probe[0].score})")

    return count


def main():
    parser = argparse.ArgumentParser(description="AegisOps AI Qdrant Semantic Memory Seeder")
    parser.add_argument("--url", default=os.getenv("QDRANT_URL", "http://localhost:6333"), help="Qdrant server URL")
    parser.add_argument("--collection", default="aegisops_knowledge", help="Collection name")
    parser.add_argument("--force", action="store_true", help="Force recreate collection")
    parser.add_argument("--dry-run", action="store_true", help="Print documents without making network calls")

    args = parser.parse_args()

    count = asyncio.run(
        seed_qdrant(
            url=args.url,
            collection_name=args.collection,
            force=args.force,
            dry_run=args.dry_run,
        )
    )
    print(f"[Seed] Completed successfully. Total records: {count}")


if __name__ == "__main__":
    main()

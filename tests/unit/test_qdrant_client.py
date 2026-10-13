"""
AegisOps AI - Qdrant Memory Client & Embedder Unit Tests (MEM-02)
Tests vector math, document schemas, semantic similarity search, and offline mock fallback.
"""

import pytest

from apps.agent.memory.embedder import DeterministicEmbedder
from apps.agent.memory.models import (
    CollectionConfig,
    DocumentType,
    KnowledgeDocument,
    SearchResult,
)
from apps.agent.memory.qdrant import QdrantMemoryClient


def test_embedder_dimension_and_normalization():
    embedder = DeterministicEmbedder()
    vec = embedder.embed_text("Database connection pool exhausted in payment-service")
    assert len(vec) == 384
    norm = sum(v * v for v in vec)
    assert pytest.approx(norm, 0.001) == 1.0


def test_embedder_empty_string():
    embedder = DeterministicEmbedder()
    vec = embedder.embed_text("")
    assert len(vec) == 384
    assert all(v == 0.0 for v in vec)


def test_embedder_semantic_similarity_properties():
    embedder = DeterministicEmbedder()

    # Two phrases describing the same operational issue
    v1 = embedder.embed_text("Database connection pool exhausted with waiting clients")
    v2 = embedder.embed_text("Hikari pool leak causing active connection saturation")
    sim_related = DeterministicEmbedder.cosine_similarity(v1, v2)

    # Completely unrelated phrase
    v3 = embedder.embed_text("Frontend button color gradient styling with css flexbox")
    sim_unrelated = DeterministicEmbedder.cosine_similarity(v1, v3)

    assert sim_related > 0.4
    assert sim_related > sim_unrelated


def test_knowledge_document_model():
    doc = KnowledgeDocument(
        id="INC-2025-001",
        document_type=DocumentType.INCIDENT,
        service="payment-service",
        title="Connection Pool Starvation",
        root_cause="Unclosed DB session in refund endpoint",
        symptoms=["500 Internal Server Error", "HikariPool-1 timeout"],
        resolution="Added try/finally close block in refund_handler.py",
        tags=["database", "connection-pool", "payments"],
        text="Incident report for payment-service connection pool starvation.",
    )
    assert doc.id == "INC-2025-001"
    assert doc.document_type == DocumentType.INCIDENT
    assert "database" in doc.tags


@pytest.mark.anyio
async def test_qdrant_offline_mock_lifecycle():
    client = QdrantMemoryClient(offline_mode=True)
    await client.ensure_collection(CollectionConfig())

    docs = [
        KnowledgeDocument(
            id="INC-POOL-01",
            document_type=DocumentType.INCIDENT,
            service="payment-service",
            title="Database Connection Pool Saturation",
            root_cause="Connection leak in v2.7.2",
            symptoms=["500 Internal Server Error", "active connections 50/50"],
            resolution="Reverted to v2.7.1 and patched pool size",
            tags=["postgres", "pool"],
            text="Payment service experienced complete outage due to PostgreSQL connection pool exhaustion.",
            metadata={"secret_key": "supersecretpassword123", "region": "us-east-1"},
        ),
        KnowledgeDocument(
            id="INC-OOM-02",
            document_type=DocumentType.INCIDENT,
            service="order-service",
            title="JVM Heap OutOfMemoryError",
            root_cause="Unbounded caching of orders in memory",
            symptoms=["Pod restarted", "OOMKilled"],
            resolution="Configured caffeine cache max size",
            tags=["memory", "oom"],
            text="Order service pods killed by Kubernetes OOMKilled due to JVM heap memory leak.",
        ),
        KnowledgeDocument(
            id="RB-POOL-01",
            document_type=DocumentType.RUNBOOK,
            service="payment-service",
            title="Payment Service DB Pool Recovery Runbook",
            root_cause="Operational procedure",
            symptoms=["Pool timeout alerts"],
            resolution="1. Check active connections in pg_stat_activity 2. Restart or rollback service",
            tags=["runbook", "database"],
            text="Step by step runbook for resolving database connection pool timeouts on payment service.",
        ),
    ]

    count_inserted = await client.upsert_documents(docs)
    assert count_inserted == 3
    assert await client.count() == 3

    # Query matching connection pool
    results = await client.search(
        query="database connection pool timeout leak",
        limit=5,
        score_threshold=0.3,
    )
    assert len(results) >= 1
    # Top result should be pool related
    top_doc = results[0].document
    assert "Pool" in top_doc.title or "pool" in top_doc.text.lower()
    assert results[0].score > 0.3

    # Filter by service
    order_results = await client.search(
        query="memory leak oom crash",
        service="order-service",
        limit=5,
        score_threshold=0.2,
    )
    assert len(order_results) == 1
    assert order_results[0].document.id == "INC-OOM-02"

    # Filter by document_type
    runbook_results = await client.search(
        query="recovery steps restart database",
        document_type="runbook",
        limit=5,
        score_threshold=0.2,
    )
    assert len(runbook_results) == 1
    assert runbook_results[0].document.id == "RB-POOL-01"

    # Verify Sanitizer redacted sensitive metadata
    fetched = await client.get_document("INC-POOL-01")
    assert fetched is not None
    assert fetched.metadata["secret_key"] == "[REDACTED]"
    assert fetched.metadata["region"] == "us-east-1"

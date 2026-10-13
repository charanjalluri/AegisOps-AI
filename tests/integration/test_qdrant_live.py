"""
AegisOps AI - Qdrant Vector Integration Tests
Requires running Docker container `docker compose up -d qdrant`.
"""

import pytest
from apps.agent.memory.models import CollectionConfig, KnowledgeDocument
from apps.agent.memory.qdrant import QdrantMemoryClient


@pytest.mark.integration
@pytest.mark.anyio
async def test_live_qdrant_container_upsert_and_search():
    client = QdrantMemoryClient(url="http://localhost:6333", offline_mode=False)
    # Check if live container is reachable
    is_live = await client._is_live_reachable()
    if not is_live:
        pytest.skip("Live Qdrant container is not reachable on http://localhost:6333")

    col_name = "test_live_integration"
    await client.ensure_collection(CollectionConfig(collection_name=col_name))

    doc = KnowledgeDocument(
        id="INT-TEST-001",
        service="payment-service",
        title="Live Container Integration Test Document",
        text="Testing live vector similarity and point retrieval in Qdrant container.",
        tags=["test", "integration"],
    )

    inserted = await client.upsert_documents([doc], collection_name=col_name)
    assert inserted == 1

    results = await client.search("vector similarity retrieval", limit=1, collection_name=col_name)
    assert len(results) == 1
    assert results[0].document.id == "INT-TEST-001"

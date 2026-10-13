"""
AegisOps AI - Qdrant Seeder Unit Tests (MEM-03)
Tests dataset schema validity, document uniqueness, and CLI seeder execution offline.
"""

import pytest

from apps.agent.memory.models import DocumentType, KnowledgeDocument
from scripts.seed_qdrant import HISTORICAL_DOCUMENTS, seed_qdrant


def test_dataset_size_and_diversity():
    # Verify dataset satisfies MEM-03 documented minimum (>= 20 operational documents)
    assert len(HISTORICAL_DOCUMENTS) >= 20
    doc_types = {d.document_type for d in HISTORICAL_DOCUMENTS}
    assert DocumentType.INCIDENT in doc_types
    assert DocumentType.POSTMORTEM in doc_types
    assert DocumentType.RUNBOOK in doc_types


def test_dataset_unique_ids_and_required_fields():
    seen_ids = set()
    for doc in HISTORICAL_DOCUMENTS:
        assert doc.id not in seen_ids, f"Duplicate ID: {doc.id}"
        seen_ids.add(doc.id)
        assert len(doc.title) > 5
        assert len(doc.text) > 20
        assert len(doc.service) > 2
        assert len(doc.tags) >= 2


def test_dataset_contains_connection_leak_and_rollback_scenarios():
    pool_docs = [
        d for d in HISTORICAL_DOCUMENTS
        if any("pool" in t for t in d.tags) or "connection-leak" in d.tags
    ]
    assert len(pool_docs) >= 3
    runbooks = [d for d in HISTORICAL_DOCUMENTS if d.document_type == DocumentType.RUNBOOK]
    assert len(runbooks) >= 4


@pytest.mark.anyio
async def test_seeder_dry_run():
    count = await seed_qdrant(dry_run=True)
    assert count == len(HISTORICAL_DOCUMENTS)
    assert count >= 20


@pytest.mark.anyio
async def test_seeder_mock_execution():
    count = await seed_qdrant(
        url="http://localhost:6333",
        collection_name="test_knowledge_seed",
        offline_mode=True,
    )
    assert count == len(HISTORICAL_DOCUMENTS)
    assert count >= 20


@pytest.mark.anyio
async def test_seeder_idempotency_and_duplicate_handling():
    # Repeated seeding runs must be idempotent and overwrite duplicate IDs cleanly
    from apps.agent.memory.qdrant import QdrantMemoryClient
    client = QdrantMemoryClient(offline_mode=True)
    col_name = "test_idempotency_col"

    # Seed first run
    c1 = await client.upsert_documents(HISTORICAL_DOCUMENTS, collection_name=col_name)
    assert c1 == len(HISTORICAL_DOCUMENTS)

    # Seed second run with same documents
    c2 = await client.upsert_documents(HISTORICAL_DOCUMENTS, collection_name=col_name)
    assert c2 == len(HISTORICAL_DOCUMENTS)

    # Verify mock store count does not duplicate points
    store = client._get_mock_store(col_name)
    assert len(store) == len(HISTORICAL_DOCUMENTS)


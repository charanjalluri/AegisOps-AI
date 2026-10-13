"""
AegisOps AI - Qdrant Semantic Memory Client (MEM-02)
Asynchronous Qdrant vector client using HTTP REST API with seamless in-memory
mock fallback for 100% offline development and unit test independence.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from apps.agent.memory.embedder import BaseEmbedder, DeterministicEmbedder
from apps.agent.memory.models import (
    CollectionConfig,
    DocumentType,
    KnowledgeDocument,
    SearchResult,
)
from apps.common.mcp.security import Sanitizer


class QdrantMemoryClient:
    """
    Asynchronous client for Qdrant vector storage.
    Supports live Qdrant container on :6333 or offline in-memory fallback.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        embedder: Optional[BaseEmbedder] = None,
        offline_mode: bool = False,
        timeout: float = 3.0,
    ):
        self.url = (url or os.getenv("QDRANT_URL", "http://localhost:6333")).rstrip("/")
        self.embedder = embedder or DeterministicEmbedder()
        self.offline_mode = offline_mode
        self.timeout = timeout

        # In-memory mock storage: collection_name -> Dict[doc_id, {"vector": List[float], "doc": KnowledgeDocument}]
        self._mock_collections: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def _get_mock_store(self, collection_name: str) -> Dict[str, Dict[str, Any]]:
        return self._mock_collections.setdefault(collection_name, {})

    async def _is_live_reachable(self) -> bool:
        if self.offline_mode:
            return False
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.url}/collections")
                return res.status_code == 200
        except Exception:
            return False

    async def ensure_collection(
        self,
        config: Optional[CollectionConfig] = None,
    ) -> bool:
        cfg = config or CollectionConfig()
        col = cfg.collection_name

        if self.offline_mode:
            self._get_mock_store(col)
            return True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.url}/collections/{col}")
                if res.status_code == 200:
                    return True

                payload = {
                    "vectors": {
                        "size": cfg.vector_size,
                        "distance": cfg.distance,
                    }
                }
                put_res = await client.put(f"{self.url}/collections/{col}", json=payload)
                if put_res.status_code in (200, 201, 409):
                    return True
                self._get_mock_store(col)
                return True
        except Exception:
            self._get_mock_store(col)
            return True

    async def upsert_documents(
        self,
        documents: List[KnowledgeDocument],
        collection_name: str = "aegisops_knowledge",
    ) -> int:
        if not documents:
            return 0

        # Embed all texts using full descriptive context
        texts = [doc.full_text() for doc in documents]
        vectors = self.embedder.embed_texts(texts)

        # Sanitize metadata before storing
        sanitized_docs: List[KnowledgeDocument] = []
        for doc in documents:
            clean_meta = Sanitizer.sanitize(doc.metadata) if doc.metadata else {}
            sanitized_doc = doc.model_copy(update={"metadata": clean_meta})
            sanitized_docs.append(sanitized_doc)

        is_live = await self._is_live_reachable()

        if not is_live:
            mock_store = self._get_mock_store(collection_name)
            for doc, vec in zip(sanitized_docs, vectors):
                mock_store[doc.id] = {"vector": vec, "doc": doc}
            return len(sanitized_docs)

        # Live Qdrant upsert
        try:
            points = []
            for doc, vec in zip(sanitized_docs, vectors):
                points.append(
                    {
                        "id": doc.id,
                        "vector": vec,
                        "payload": doc.model_dump(),
                    }
                )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.put(
                    f"{self.url}/collections/{collection_name}/points?wait=true",
                    json={"points": points},
                )
                if res.status_code == 200:
                    return len(sanitized_docs)
        except Exception:
            pass

        mock_store = self._get_mock_store(collection_name)
        for doc, vec in zip(sanitized_docs, vectors):
            mock_store[doc.id] = {"vector": vec, "doc": doc}
        return len(sanitized_docs)

    async def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.2,
        service: Optional[str] = None,
        document_type: Optional[str] = None,
        collection_name: str = "aegisops_knowledge",
    ) -> List[SearchResult]:
        if not query:
            return []

        query_vec = self.embedder.embed_text(query)
        is_live = await self._is_live_reachable()

        req_doc_type = (
            document_type.value if hasattr(document_type, "value") else str(document_type).lower()
            if document_type
            else None
        )

        if is_live:
            try:
                filters: Dict[str, Any] = {"must": []}
                if service:
                    filters["must"].append({"key": "service", "match": {"value": service}})
                if req_doc_type:
                    filters["must"].append({"key": "document_type", "match": {"value": req_doc_type}})

                search_payload: Dict[str, Any] = {
                    "vector": query_vec,
                    "limit": limit,
                    "with_payload": True,
                    "score_threshold": score_threshold,
                }
                if filters["must"]:
                    search_payload["filter"] = filters

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(
                        f"{self.url}/collections/{collection_name}/points/search",
                        json=search_payload,
                    )
                    if res.status_code == 200:
                        data = res.json().get("result", [])
                        results = []
                        for item in data:
                            doc_data = item.get("payload", {})
                            doc = KnowledgeDocument(**doc_data)
                            results.append(SearchResult(document=doc, score=float(item.get("score", 0.0))))
                        return results
            except Exception:
                pass

        # Mock search fallback
        mock_store = self._get_mock_store(collection_name)
        scored: List[SearchResult] = []

        for item in mock_store.values():
            doc: KnowledgeDocument = item["doc"]
            doc_vec: List[float] = item["vector"]

            # Filter checks
            if service and doc.service != service:
                continue
            if req_doc_type:
                doc_type_val = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
                if doc_type_val.lower() != req_doc_type:
                    continue

            sim = DeterministicEmbedder.cosine_similarity(query_vec, doc_vec)
            if sim >= score_threshold:
                scored.append(SearchResult(document=doc, score=round(sim, 4)))

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[:limit]

    async def get_document(
        self,
        doc_id: str,
        collection_name: str = "aegisops_knowledge",
    ) -> Optional[KnowledgeDocument]:
        is_live = await self._is_live_reachable()
        if is_live:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.get(f"{self.url}/collections/{collection_name}/points/{doc_id}")
                    if res.status_code == 200:
                        payload = res.json().get("result", {}).get("payload")
                        if payload:
                            return KnowledgeDocument(**payload)
            except Exception:
                pass

        mock_store = self._get_mock_store(collection_name)
        item = mock_store.get(doc_id)
        return item["doc"] if item else None

    async def count(self, collection_name: str = "aegisops_knowledge") -> int:
        is_live = await self._is_live_reachable()
        if is_live:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(
                        f"{self.url}/collections/{collection_name}/points/count",
                        json={"exact": True},
                    )
                    if res.status_code == 200:
                        return int(res.json().get("result", {}).get("count", 0))
            except Exception:
                pass

        return len(self._get_mock_store(collection_name))

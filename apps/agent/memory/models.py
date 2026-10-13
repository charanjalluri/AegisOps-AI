"""
AegisOps AI - Long-Term Semantic Memory Data Models (MEM-02)
Pydantic V2 models for operational knowledge, vector configurations, and search results.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    RUNBOOK = "runbook"


class KnowledgeDocument(BaseModel):
    id: str = Field(..., description="Unique document ID (e.g., INC-2025-089 or UUID)")
    document_type: DocumentType = Field(default=DocumentType.INCIDENT, description="Document type")
    service: str = Field(..., description="Target service (e.g., payment-service)")
    title: str = Field(..., description="Title of incident, postmortem, or runbook")
    root_cause: Optional[str] = Field(default=None, description="Identified root cause")
    symptoms: List[str] = Field(default_factory=list, description="Observed symptoms and metrics")
    resolution: Optional[str] = Field(default=None, description="Resolution steps or remediation")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    text: str = Field(..., description="Searchable narrative text representation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extra metadata")

    def full_text(self) -> str:
        """Combines all informative fields for semantic embedding."""
        parts = [self.title, self.text]
        if self.root_cause:
            parts.append(self.root_cause)
        if self.resolution:
            parts.append(self.resolution)
        if self.symptoms:
            parts.extend(self.symptoms)
        if self.tags:
            parts.extend(self.tags)
        return " ".join(parts)


class SearchResult(BaseModel):
    document: KnowledgeDocument
    score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")


class CollectionConfig(BaseModel):
    collection_name: str = "aegisops_knowledge"
    vector_size: int = 384
    distance: str = "Cosine"

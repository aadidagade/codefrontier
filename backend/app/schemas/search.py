import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectSearchRequest(BaseModel):
    """Payload for POST /api/v1/projects/{project_id}/search."""
    query: str = Field(..., min_length=1, description="Search query string")
    document_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional list of document UUIDs to filter")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of relevant chunks to retrieve")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum confidence/similarity threshold")
    search_mode: Optional[str] = Field("hybrid", description="Retrieval mode: 'hybrid', 'semantic', or 'keyword'")


class RetrievedChunk(BaseModel):
    """Retrieved document chunk retaining full source traceability metadata."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    similarity_score: float
    retrieval_method: str = "hybrid"  # semantic, keyword, hybrid


class ProjectSearchResponse(BaseModel):
    """Standardized search response returning ranked evidence chunks and source documents."""
    query: str
    total_results: int
    chunks: List[RetrievedChunk]
    source_documents: List[str]

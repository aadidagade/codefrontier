import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ProcessingLogItem(BaseModel):
    id: str
    stage: str
    label: str
    status: str
    timestamp: str
    detail: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """Full document representation including metadata and extraction stats."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID] = None
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    processing_status: str  # UPLOADED, EXTRACTING, EXTRACTED, CHUNKING, INDEXING, READY, FAILED, NEEDS_OCR
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    word_count: Optional[int] = None
    preview: Optional[str] = None
    progress: int = 0
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    """Live processing status for polling / progress indicators."""
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    progress: int
    error: Optional[str] = None
    logs: List[ProcessingLogItem] = []
    chunk_count: int = 0
    page_count: int = 0
    word_count: int = 0


class DocumentChunkResponse(BaseModel):
    """Semantic chunk representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    project_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    created_at: datetime


class DocumentSearchRequest(BaseModel):
    """Semantic vector search query request."""
    query: str
    top_k: int = 5
    similarity_threshold: Optional[float] = None
    document_ids: Optional[List[uuid.UUID]] = None


class DocumentSearchResultItem(BaseModel):
    """Semantic vector search match."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    similarity: float


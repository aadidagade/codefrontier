import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.models.base import UUIDMixin, utc_now

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.evidence import EvidenceReference


class Document(Base, UUIDMixin):
    """
    Source knowledge documentation ingested into the platform.
    """
    __tablename__ = "documents"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, txt, md
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        index=True,
    )  # uploaded, extracting_text, chunking_content, indexing, ready, failed
    extraction_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="documents_uploaded")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    evidence_references: Mapped[List["EvidenceReference"]] = relationship(
        "EvidenceReference",
        back_populates="document",
    )


class DocumentChunk(Base, UUIDMixin):
    """
    Semantic partition of an ingested document with 768-dim dense embedding for RAG.
    """
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunks_project_doc", "project_id", "document_id"),
        Index("ix_chunks_doc_index", "document_id", "chunk_index"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding using pgvector (768 dimensions for Gemini text-embedding-004 / gemini-embedding-2)
    embedding = mapped_column(Vector(768), nullable=True)

    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    project: Mapped["Project"] = relationship("Project", back_populates="document_chunks")
    evidence_references: Mapped[List["EvidenceReference"]] = relationship(
        "EvidenceReference",
        back_populates="chunk",
    )

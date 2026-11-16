import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, utc_now

if TYPE_CHECKING:
    from app.models.handover import Handover, HandoverSection
    from app.models.document import Document, DocumentChunk


class EvidenceReference(Base, UUIDMixin):
    """
    Bi-directional link connecting an AI claim in a handover section
    directly to the original source document and chunk passage.
    """
    __tablename__ = "evidence_references"

    handover_section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handover_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    claim_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    supporting_text_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="supported",
        nullable=False,
    )  # Supported, Partially Supported, Unsupported, Conflicting, Insufficient Evidence
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        if "chunk_id" in kwargs and "document_chunk_id" not in kwargs:
            kwargs["document_chunk_id"] = kwargs.pop("chunk_id")
        if "confidence_score" in kwargs and "relevance_score" not in kwargs:
            kwargs["relevance_score"] = kwargs.pop("confidence_score")
        super().__init__(*args, **kwargs)

    @property
    def chunk_id(self) -> Optional[uuid.UUID]:
        return self.document_chunk_id

    @chunk_id.setter
    def chunk_id(self, val: Optional[uuid.UUID]):
        self.document_chunk_id = val

    @property
    def confidence_score(self) -> float:
        return self.relevance_score

    @confidence_score.setter
    def confidence_score(self, val: float):
        self.relevance_score = val

    # Relationships
    handover_section: Mapped["HandoverSection"] = relationship(
        "HandoverSection",
        back_populates="evidence_references",
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        back_populates="evidence_references",
    )
    chunk: Mapped[Optional["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="evidence_references",
    )


class ClaimVerification(Base, UUIDMixin):
    """
    Detailed verification record for an individual AI-generated claim
    within a handover section, audited against ground-truth document chunks.
    Never invents evidence or references.
    """
    __tablename__ = "claim_verifications"

    handover_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handover_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handover_sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # Supported, Partially Supported, Unsupported, Conflicting, Insufficient Evidence
    supporting_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supporting_text_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alignment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verification_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    def __init__(self, *args, **kwargs):
        if "chunk_id" in kwargs and "document_chunk_id" not in kwargs:
            kwargs["document_chunk_id"] = kwargs.pop("chunk_id")
        if "confidence_score" in kwargs and "alignment_score" not in kwargs:
            kwargs["alignment_score"] = kwargs.pop("confidence_score")
        if "relevance_score" in kwargs and "alignment_score" not in kwargs:
            kwargs["alignment_score"] = kwargs.pop("relevance_score")
        super().__init__(*args, **kwargs)

    @property
    def chunk_id(self) -> Optional[uuid.UUID]:
        return self.document_chunk_id

    @chunk_id.setter
    def chunk_id(self, val: Optional[uuid.UUID]):
        self.document_chunk_id = val

    @property
    def confidence_score(self) -> float:
        return self.alignment_score

    @confidence_score.setter
    def confidence_score(self, val: float):
        self.alignment_score = val

    @property
    def relevance_score(self) -> float:
        return self.alignment_score

    @relevance_score.setter
    def relevance_score(self, val: float):
        self.alignment_score = val

    # Relationships
    handover: Mapped["Handover"] = relationship(
        "Handover",
        back_populates="claim_verifications",
    )
    handover_section: Mapped[Optional["HandoverSection"]] = relationship(
        "HandoverSection",
        back_populates="claim_verifications",
    )
    document: Mapped[Optional["Document"]] = relationship("Document")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship("DocumentChunk")

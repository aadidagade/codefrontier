import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.handover import HandoverSection
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
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default="supported",
        nullable=False,
    )  # supported, partially_supported, unsupported, conflicting

    # Relationships
    handover_section: Mapped["HandoverSection"] = relationship(
        "HandoverSection",
        back_populates="evidence_references",
    )
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="evidence_references",
    )
    chunk: Mapped[Optional["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="evidence_references",
    )

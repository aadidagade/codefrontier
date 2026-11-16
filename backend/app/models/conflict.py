import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, utc_now

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.handover import Handover
    from app.models.user import User


class Conflict(Base, UUIDMixin):
    """
    Contradictory information or conflicting claims detected across multiple source documents.
    """
    __tablename__ = "conflicts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    handover_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    conflict_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # date, owner, architecture, process, security
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_a: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_b: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="OPEN",
        nullable=False,
        index=True,
    )  # OPEN, UNDER_REVIEW, RESOLVED, DISMISSED
    resolution: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Advanced Contradiction Detection Engine Columns
    conflict_category_col: Mapped[Optional[str]] = mapped_column("conflict_category", String(100), nullable=True, index=True)
    statement_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statement_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_a_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_document_a_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_document_b_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_document_b_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_excerpt_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_excerpt_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detection_timestamp_col: Mapped[Optional[datetime]] = mapped_column("detection_timestamp", DateTime(timezone=True), nullable=True)
    resolution_status_col: Mapped[Optional[str]] = mapped_column("resolution_status", String(50), default="Unresolved", nullable=True, index=True)

    def __init__(self, *args, **kwargs):
        # Category alias
        cat = kwargs.pop("conflict_category", None) or kwargs.get("conflict_type", "architecture")
        kwargs["conflict_type"] = cat
        kwargs["conflict_category_col"] = cat

        # Status alias
        stat = kwargs.pop("resolution_status", None) or kwargs.get("status", "Unresolved")
        kwargs["status"] = stat
        kwargs["resolution_status_col"] = stat

        # Statements & Sources
        stmt_a = kwargs.get("statement_a") or kwargs.pop("conflicting_statement_a", None)
        stmt_b = kwargs.get("statement_b") or kwargs.pop("conflicting_statement_b", None)
        kwargs["statement_a"] = stmt_a
        kwargs["statement_b"] = stmt_b

        doc_a_name = kwargs.get("source_document_a_name") or kwargs.pop("source_document_a", None)
        doc_b_name = kwargs.get("source_document_b_name") or kwargs.pop("source_document_b", None)
        kwargs["source_document_a_name"] = doc_a_name
        kwargs["source_document_b_name"] = doc_b_name

        exc_a = kwargs.get("source_excerpt_a")
        exc_b = kwargs.get("source_excerpt_b")
        kwargs["source_excerpt_a"] = exc_a
        kwargs["source_excerpt_b"] = exc_b

        # Timestamp
        ts = kwargs.pop("detection_timestamp", None) or kwargs.get("created_at") or utc_now()
        kwargs["created_at"] = ts
        kwargs["detection_timestamp_col"] = ts

        # Ensure source_a and source_b dicts exist for legacy compatibility
        src_a = kwargs.get("source_a", {})
        if not src_a and (stmt_a or doc_a_name or exc_a):
            src_a = {
                "statement": stmt_a,
                "text": exc_a or stmt_a,
                "excerpt": exc_a or stmt_a,
                "document_name": doc_a_name,
                "document_id": str(kwargs.get("source_document_a_id")) if kwargs.get("source_document_a_id") else None,
            }
        kwargs["source_a"] = src_a

        src_b = kwargs.get("source_b", {})
        if not src_b and (stmt_b or doc_b_name or exc_b):
            src_b = {
                "statement": stmt_b,
                "text": exc_b or stmt_b,
                "excerpt": exc_b or stmt_b,
                "document_name": doc_b_name,
                "document_id": str(kwargs.get("source_document_b_id")) if kwargs.get("source_document_b_id") else None,
            }
        kwargs["source_b"] = src_b

        super().__init__(*args, **kwargs)

    @property
    def conflict_id(self) -> uuid.UUID:
        return self.id

    @property
    def conflict_category(self) -> str:
        return self.conflict_category_col or self.conflict_type

    @conflict_category.setter
    def conflict_category(self, val: str):
        self.conflict_type = val
        self.conflict_category_col = val

    @property
    def resolution_status(self) -> str:
        return self.resolution_status_col or self.status

    @resolution_status.setter
    def resolution_status(self, val: str):
        self.status = val
        self.resolution_status_col = val

    @property
    def detection_timestamp(self) -> datetime:
        return self.detection_timestamp_col or self.created_at

    @detection_timestamp.setter
    def detection_timestamp(self, val: datetime):
        self.created_at = val
        self.detection_timestamp_col = val

    @property
    def source_document_a(self) -> Optional[str]:
        return self.source_document_a_name or (self.source_a.get("document_name") if self.source_a else None)

    @source_document_a.setter
    def source_document_a(self, val: Optional[str]):
        self.source_document_a_name = val
        if self.source_a is not None and isinstance(self.source_a, dict):
            self.source_a["document_name"] = val

    @property
    def source_document_b(self) -> Optional[str]:
        return self.source_document_b_name or (self.source_b.get("document_name") if self.source_b else None)

    @source_document_b.setter
    def source_document_b(self, val: Optional[str]):
        self.source_document_b_name = val
        if self.source_b is not None and isinstance(self.source_b, dict):
            self.source_b["document_name"] = val

    @property
    def conflicting_statement_a(self) -> Optional[str]:
        return self.statement_a or (self.source_a.get("statement") or self.source_a.get("text") if self.source_a else None)

    @conflicting_statement_a.setter
    def conflicting_statement_a(self, val: Optional[str]):
        self.statement_a = val
        if self.source_a is not None and isinstance(self.source_a, dict):
            self.source_a["statement"] = val

    @property
    def conflicting_statement_b(self) -> Optional[str]:
        return self.statement_b or (self.source_b.get("statement") or self.source_b.get("text") if self.source_b else None)

    @conflicting_statement_b.setter
    def conflicting_statement_b(self, val: Optional[str]):
        self.statement_b = val
        if self.source_b is not None and isinstance(self.source_b, dict):
            self.source_b["statement"] = val

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="conflicts")
    handover: Mapped[Optional["Handover"]] = relationship("Handover", back_populates="conflicts")
    resolver: Mapped[Optional["User"]] = relationship("User")

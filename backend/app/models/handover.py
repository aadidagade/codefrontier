import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.evidence import EvidenceReference
    from app.models.conflict import Conflict
    from app.models.task import Task


class Handover(Base, UUIDMixin, TimestampMixin):
    """
    Structured knowledge transition package synthesizing repository documents.
    """
    __tablename__ = "handovers"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="draft",
        nullable=False,
        index=True,
    )  # draft, awaiting_review, changes_requested, approved, rejected, acknowledged
    version: Mapped[str] = mapped_column(String(50), default="v1.0", nullable=False)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    shared_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="handovers")
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="handovers_created",
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="handovers_assigned",
    )
    sections: Mapped[List["HandoverSection"]] = relationship(
        "HandoverSection",
        back_populates="handover",
        cascade="all, delete-orphan",
        order_by="HandoverSection.sort_order",
    )
    versions: Mapped[List["HandoverVersion"]] = relationship(
        "HandoverVersion",
        back_populates="handover",
        cascade="all, delete-orphan",
        order_by="desc(HandoverVersion.created_at)",
    )
    audit_logs: Mapped[List["HandoverAuditLog"]] = relationship(
        "HandoverAuditLog",
        back_populates="handover",
        cascade="all, delete-orphan",
        order_by="desc(HandoverAuditLog.created_at)",
    )
    conflicts: Mapped[List["Conflict"]] = relationship(
        "Conflict",
        back_populates="handover",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="handover",
        cascade="all, delete-orphan",
    )


class HandoverSection(Base, UUIDMixin):
    """
    Individual section within a handover (e.g., Overview, Decisions, Risks, Runbooks).
    """
    __tablename__ = "handover_sections"
    __table_args__ = (
        Index("ix_handover_section_sort", "handover_id", "sort_order"),
    )

    handover_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )  # pending, approved, changes_requested, rejected
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    handover: Mapped["Handover"] = relationship("Handover", back_populates="sections")
    evidence_references: Mapped[List["EvidenceReference"]] = relationship(
        "EvidenceReference",
        back_populates="handover_section",
        cascade="all, delete-orphan",
    )


class HandoverVersion(Base, UUIDMixin):
    """
    Snapshot history recording each revision of an approved or edited handover.
    """
    __tablename__ = "handover_versions"

    handover_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    handover: Mapped["Handover"] = relationship("Handover", back_populates="versions")
    creator: Mapped[Optional["User"]] = relationship("User")


class HandoverAuditLog(Base, UUIDMixin):
    """
    Immutable compliance log recording state transitions and user actions.
    """
    __tablename__ = "handover_audit_logs"

    handover_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    handover: Mapped["Handover"] = relationship("Handover", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User")

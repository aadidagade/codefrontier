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

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="conflicts")
    handover: Mapped[Optional["Handover"]] = relationship("Handover", back_populates="conflicts")
    resolver: Mapped[Optional["User"]] = relationship("User")

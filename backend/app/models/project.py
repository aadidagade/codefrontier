import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document, DocumentChunk
    from app.models.handover import Handover
    from app.models.conflict import Conflict
    from app.models.task import Task
    from app.models.notification import Notification


class ProjectMemberRole(str, enum.Enum):
    """Authorized roles for project members."""
    ADMIN = "ADMIN"
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"
    LEAD = "LEAD"


class Project(Base, UUIDMixin, TimestampMixin):
    """
    Isolated project workspace boundary ensuring cross-tenant document isolation.
    """
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="projects_created",
        foreign_keys=[created_by],
    )
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    document_chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    handovers: Mapped[List["Handover"]] = relationship(
        "Handover",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    conflicts: Mapped[List["Conflict"]] = relationship(
        "Conflict",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(Base, UUIDMixin):
    """
    Associates users with a project workspace with specific role privileges.
    """
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default=ProjectMemberRole.INCOMING.value,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")

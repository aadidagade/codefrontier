import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.project import Project, ProjectMember
    from app.models.document import Document
    from app.models.handover import Handover, HandoverAuditLog, HandoverVersion
    from app.models.task import Task
    from app.models.notification import Notification
    from app.models.conflict import Conflict


class User(Base, UUIDMixin, TimestampMixin):
    """
    Team member account with role permissions and project memberships.
    """
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    project_memberships: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    projects_created: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="creator",
        foreign_keys="Project.created_by",
    )
    documents_uploaded: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="uploader",
    )
    handovers_created: Mapped[List["Handover"]] = relationship(
        "Handover",
        back_populates="creator",
        foreign_keys="Handover.created_by",
    )
    handovers_assigned: Mapped[List["Handover"]] = relationship(
        "Handover",
        back_populates="assignee",
        foreign_keys="Handover.assigned_to",
    )
    tasks_assigned: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="assignee",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshToken(Base, UUIDMixin):
    """
    Stores cryptographic hashes of active refresh tokens for session revocation.
    """
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

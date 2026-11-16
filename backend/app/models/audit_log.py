import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project


class AuditActionType(str, enum.Enum):
    """Canonical action types tracked across system and project workflows."""
    # Authentication events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"

    # Project lifecycle events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"

    # Document management events
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"

    # Handover synthesis and review events
    HANDOVER_GENERATED = "handover_generated"
    HANDOVER_MODIFIED = "handover_modified"
    HANDOVER_APPROVED = "handover_approved"
    HANDOVER_REJECTED = "handover_rejected"
    HANDOVER_SHARED = "handover_shared"
    HANDOVER_ACKNOWLEDGED = "handover_acknowledged"
    TRANSITION_STATUS_UPDATED = "transition_status_updated"
    VERSION_RESTORED = "version_restored"

    # Task and continuity events
    TASK_PROGRESS_UPDATED = "task_progress_updated"
    TASK_STATUS_UPDATED = "task_status_updated"

    # Access governance and role events
    PERMISSION_CHANGED = "permission_changed"
    MEMBER_INVITED = "member_invited"
    ACCESS_REVOKED = "access_revoked"

    # Knowledge conflict resolution events
    CONFLICT_RESOLVED = "conflict_resolved"


class AuditEntityType(str, enum.Enum):
    """Categorical domain entities referenced by audit entries."""
    USER = "user"
    PROJECT = "project"
    DOCUMENT = "document"
    HANDOVER = "handover"
    HANDOVER_SECTION = "handover_section"
    PROJECT_MEMBER = "project_member"
    CONFLICT = "conflict"
    HANDOVER_VERSION = "handover_version"
    TASK = "task"


class AuditLog(Base, UUIDMixin):
    """
    Immutable compliance audit trail recording critical project and security activities.
    
    Security Guarantees:
    - Server-side creation only.
    - Immutable: ordinary project members cannot modify or delete audit records.
    - Read access restricted to authorized project roles with VIEW_AUDIT_LOGS permission.
    - Automatic redaction of secrets, tokens, passwords, and sensitive document payloads.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_project_timestamp", "project_id", "timestamp"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    change_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    request_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="audit_logs", lazy="select")

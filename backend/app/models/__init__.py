"""
Central ORM Registry: Exports all 15 SQLAlchemy 2.0 domain models.
Ensures Alembic and relationship mappers discover all schemas properly.
"""

from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.user import User, RefreshToken
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.models.handover import Handover, HandoverSection, HandoverVersion, HandoverAuditLog
from app.models.evidence import EvidenceReference
from app.models.conflict import Conflict
from app.models.task import Task, TaskDependency
from app.models.notification import Notification

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # 1. User
    "User",
    # 2. Project
    "Project",
    # 3. ProjectMember
    "ProjectMember",
    "ProjectMemberRole",
    # 4. Document
    "Document",
    # 5. DocumentChunk
    "DocumentChunk",
    # 6. Handover
    "Handover",
    # 7. HandoverSection
    "HandoverSection",
    # 8. EvidenceReference
    "EvidenceReference",
    # 9. Conflict
    "Conflict",
    # 10. Task
    "Task",
    # 11. TaskDependency
    "TaskDependency",
    # 12. Notification
    "Notification",
    # 13. HandoverAuditLog
    "HandoverAuditLog",
    # 14. HandoverVersion
    "HandoverVersion",
    # 15. RefreshToken
    "RefreshToken",
]

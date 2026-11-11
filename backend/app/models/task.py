import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.handover import Handover
    from app.models.user import User


class Task(Base, UUIDMixin, TimestampMixin):
    """
    Continuation responsibility transferred to incoming team members.
    """
    __tablename__ = "tasks"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False,
    )  # critical, high, medium, low
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, in_progress, completed, blocked
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    handover: Mapped[Optional["Handover"]] = relationship("Handover", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", back_populates="tasks_assigned")

    dependencies: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    dependents: Mapped[List["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
    )


class TaskDependency(Base, UUIDMixin):
    """
    Directed dependency between tasks (Task A requires Task B to be resolved first).
    Enforces non-self dependencies at database level.
    """
    __tablename__ = "task_dependencies"
    __table_args__ = (
        CheckConstraint("task_id != depends_on_task_id", name="ck_no_self_task_dependency"),
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency_pair"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[task_id],
        back_populates="dependencies",
    )
    depends_on_task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[depends_on_task_id],
        back_populates="dependents",
    )

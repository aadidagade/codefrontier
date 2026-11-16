import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskResponse(BaseModel):
    """Continuation responsibility item transferred to incoming members."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    dependencies_count: int = 0
    dependents_count: int = 0
    is_blocked: bool = False


class TaskCreate(BaseModel):
    """Payload to create a new continuation task."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, description="Task details, instructions, or handover context")
    assigned_to: Optional[uuid.UUID] = Field(None, description="Project member assigned to complete the task")
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    status: str = Field("pending", pattern="^(pending|in_progress|completed|blocked|cancelled)$")
    due_date: Optional[datetime] = Field(None, description="Target completion timestamp")
    handover_id: Optional[uuid.UUID] = Field(None, description="Associated handover session")


class TaskUpdate(BaseModel):
    """Payload to modify task attributes, priority, status, or assignee."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[uuid.UUID] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|blocked|cancelled)$")
    due_date: Optional[datetime] = None


class TaskDependencyCreate(BaseModel):
    """Payload to establish a dependency (prerequisite) between tasks."""
    depends_on_task_id: uuid.UUID = Field(
        ...,
        description="UUID of prerequisite task that must be resolved first",
    )


class TaskDependencyItem(BaseModel):
    """Dependency relationship representation with target task metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    depends_on_task_id: uuid.UUID
    depends_on_title: Optional[str] = None
    depends_on_status: Optional[str] = None
    is_resolved: bool = False


class TaskDependencyListResponse(BaseModel):
    """Comprehensive dependency overview showing blocking prerequisites and waiting dependents."""
    task_id: uuid.UUID
    task_title: str
    task_status: str
    is_blocked: bool
    prerequisites: List[TaskDependencyItem] = []
    dependents: List[TaskDependencyItem] = []


class ProgressNoteCreate(BaseModel):
    """Payload to append a timestamped progress note to a task."""
    text: str = Field(..., min_length=1, description="Progress note text")


class TaskProgressUpdateCreate(BaseModel):
    """Payload for incoming member or assignee to record a structured progress update."""
    update_text: str = Field(..., min_length=1, description="Detailed progress update or milestone notes")
    new_status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|blocked|cancelled)$", description="Optional new status transition")


class TaskProgressUpdateResponse(BaseModel):
    """Structured progress update item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    update_text: str
    status_before: Optional[str] = None
    status_after: Optional[str] = None
    created_at: datetime


class TaskStatusUpdate(BaseModel):
    """Payload to update continuation task status."""
    status: str = Field(..., pattern="^(pending|in_progress|completed|blocked|cancelled)$", description="New status")
    notes: Optional[str] = Field(None, description="Optional transition note or rationale")

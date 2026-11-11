import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.project import ProjectMemberRole


class ProjectCreate(BaseModel):
    """Payload to create a new project workspace."""
    name: str = Field(..., min_length=2, max_length=255, description="Project workspace name")
    description: Optional[str] = Field(None, description="Detailed project description or scope")
    organization_name: Optional[str] = Field(None, max_length=255, description="Organization or department")


class ProjectUpdate(BaseModel):
    """Payload to update an existing project."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    organization_name: Optional[str] = None
    status: Optional[str] = Field(None, description="active, in_progress, completed, archived")


class ProjectResponse(BaseModel):
    """Public project summary."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    organization_name: Optional[str] = None
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    members_count: Optional[int] = None


class MemberAdd(BaseModel):
    """Payload to add/invite an existing registered user to a project."""
    email: Optional[EmailStr] = Field(None, description="Registered user email to invite")
    user_id: Optional[uuid.UUID] = Field(None, description="Registered user UUID")
    role: ProjectMemberRole = Field(default=ProjectMemberRole.INCOMING, description="Assigned role: ADMIN, OUTGOING, INCOMING, LEAD")


class MemberUpdateRole(BaseModel):
    """Payload to change a member's role."""
    role: ProjectMemberRole = Field(..., description="New role: ADMIN, OUTGOING, INCOMING, LEAD")


class ProjectMemberResponse(BaseModel):
    """Detailed member profile within a project."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID  # ProjectMember ID
    project_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    profile_image: Optional[str] = None
    role: str
    joined_at: datetime


class ProjectOverviewResponse(BaseModel):
    """
    Comprehensive project dashboard overview containing live metrics
    queried directly from PostgreSQL.
    """
    project: ProjectResponse
    members: List[ProjectMemberResponse]
    total_members: int
    total_documents: int
    processed_documents: int
    total_handovers: int
    pending_reviews: int
    open_conflicts: int
    pending_tasks: int
    overall_handover_status: str
    recent_activity: List[dict] = Field(default_factory=list)

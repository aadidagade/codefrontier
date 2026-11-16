import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """
    Structured response representing an immutable compliance audit record.
    """
    id: uuid.UUID = Field(..., description="Unique audit record identifier")
    audit_id: uuid.UUID = Field(..., description="Alias for audit record identifier")
    user_id: Optional[uuid.UUID] = Field(None, description="Identifier of the user performing the activity")
    user_email: Optional[str] = Field(None, description="Email address of the acting user")
    user_name: Optional[str] = Field(None, description="Full name of the acting user")
    project_id: Optional[uuid.UUID] = Field(None, description="Project workspace identifier")
    action: str = Field(..., description="Canonical action type performed")
    action_type: str = Field(..., description="Canonical action type alias")
    entity_type: str = Field(..., description="Domain entity type impacted")
    entity_id: Optional[str] = Field(None, description="Entity identifier (UUID or string)")
    timestamp: datetime = Field(..., description="UTC timestamp of the logged activity")
    change_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Sanitized change metadata")
    request_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Client request context")

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, log: Any) -> "AuditLogResponse":
        user_email = None
        user_name = None
        if getattr(log, "user", None):
            user_email = log.user.email
            user_name = log.user.full_name

        action_val = str(log.action.value if hasattr(log.action, "value") else log.action)
        entity_val = str(log.entity_type.value if hasattr(log.entity_type, "value") else log.entity_type)

        return cls(
            id=log.id,
            audit_id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            user_name=user_name,
            project_id=log.project_id,
            action=action_val,
            action_type=action_val,
            entity_type=entity_val,
            entity_id=str(log.entity_id) if log.entity_id is not None else None,
            timestamp=log.timestamp,
            change_metadata=log.change_metadata or {},
            request_context=log.request_context or {},
        )


class AuditLogListResponse(BaseModel):
    """
    Paginated collection of audit log entries.
    """
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Database-backed in-app alert."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    """Payload to dispatch an in-app notification."""
    user_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    notification_type: str = Field(..., min_length=1, max_length=50)
    project_id: Optional[uuid.UUID] = None

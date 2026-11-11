from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata included in all API responses."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    """Standardized production API response envelope."""
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class PaginatedMeta(ResponseMeta):
    """Metadata for paginated collection responses."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized response envelope for paginated lists."""
    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    data: List[T] = Field(default_factory=list)
    meta: PaginatedMeta


class HealthCheckItem(BaseModel):
    status: str
    details: Optional[dict] = None
    error: Optional[str] = None


class SystemHealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    app_name: str
    environment: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    database: dict
    ai_service: dict

import math
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import Permission
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_permission
from app.dependencies.database import get_db
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.schemas.common import ApiResponse
from app.services.audit_service import AuditService

# Project-scoped router: /projects/{project_id}/audit-logs
project_audit_router = APIRouter()

# Global router: /audit-logs
router = APIRouter()


# =============================================================================
# 1. PROJECT-SCOPED AUDIT TRAIL ENDPOINTS
# =============================================================================

@project_audit_router.get(
    "/{project_id}/audit-logs",
    response_model=ApiResponse[AuditLogListResponse],
    summary="List Project Workspace Audit Logs",
    description=(
        "Retrieves the immutable chronological audit trail of all project activities "
        "(document uploads, handover reviews, permission changes, conflict resolutions, etc.). "
        "Strictly restricted to authorized roles with VIEW_AUDIT_LOGS permission."
    ),
)
async def list_project_audit_logs(
    project_id: uuid.UUID,
    action: Optional[str] = Query(None, description="Filter by action type (e.g. document_uploaded, member_invited)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (document, handover, etc.)"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    start_time: Optional[datetime] = Query(None, description="Filter records at or after this UTC timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter records at or before this UTC timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    member: ProjectMember = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
    db: AsyncSession = Depends(get_db),
):
    audit_svc = AuditService(db)
    items, total = await audit_svc.list_project_audit_logs(
        project_id=project_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )

    response_items = [AuditLogResponse.from_orm_model(item) for item in items]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ApiResponse(
        data=AuditLogListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
        message=f"Retrieved {len(response_items)} audit log record(s).",
    )


@project_audit_router.get(
    "/{project_id}/audit-logs/{audit_id}",
    response_model=ApiResponse[AuditLogResponse],
    summary="Get Specific Audit Trail Record",
    description="Retrieves a specific audit record with full metadata and request context.",
)
async def get_project_audit_log(
    project_id: uuid.UUID,
    audit_id: uuid.UUID,
    member: ProjectMember = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
    db: AsyncSession = Depends(get_db),
):
    audit_svc = AuditService(db)
    log = await audit_svc.get_audit_log(audit_id)
    if not log or log.project_id != project_id:
        raise NotFoundException(f"Audit record '{audit_id}' was not found in this project workspace.")

    return ApiResponse(
        data=AuditLogResponse.from_orm_model(log),
        message="Audit record details retrieved.",
    )


# =============================================================================
# 2. GLOBAL AUDIT TRAIL ENDPOINTS
# =============================================================================

@router.get(
    "",
    response_model=ApiResponse[AuditLogListResponse],
    summary="List System / User Activity Logs",
    description="Retrieves audit activities for the authenticated user or global workspace events.",
)
async def list_audit_logs(
    project_id: Optional[uuid.UUID] = Query(None, description="Optional project ID filter"),
    action: Optional[str] = Query(None, description="Optional action filter"),
    entity_type: Optional[str] = Query(None, description="Optional entity type filter"),
    start_time: Optional[datetime] = Query(None, description="Start UTC timestamp"),
    end_time: Optional[datetime] = Query(None, description="End UTC timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    audit_svc = AuditService(db)
    # Default to user's actions if not filtering by a project
    filter_user_id = current_user.id if project_id is None else None

    items, total = await audit_svc.list_audit_logs(
        user_id=filter_user_id,
        project_id=project_id,
        action=action,
        entity_type=entity_type,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )

    response_items = [AuditLogResponse.from_orm_model(item) for item in items]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ApiResponse(
        data=AuditLogListResponse(
            items=response_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
        message=f"Retrieved {len(response_items)} audit log record(s).",
    )


@router.get(
    "/{audit_id}",
    response_model=ApiResponse[AuditLogResponse],
    summary="Get Audit Log Entry",
    description="Retrieves a specific audit record.",
)
async def get_audit_log_by_id(
    audit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    audit_svc = AuditService(db)
    log = await audit_svc.get_audit_log(audit_id)
    if not log:
        raise NotFoundException(f"Audit record '{audit_id}' was not found.")

    return ApiResponse(
        data=AuditLogResponse.from_orm_model(log),
        message="Audit record details retrieved.",
    )


# =============================================================================
# 3. IMMUTABILITY ENFORCEMENT (Explicitly reject client mutations)
# =============================================================================

@project_audit_router.post("/{project_id}/audit-logs", status_code=status.HTTP_403_FORBIDDEN)
@project_audit_router.put("/{project_id}/audit-logs/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
@project_audit_router.patch("/{project_id}/audit-logs/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
@project_audit_router.delete("/{project_id}/audit-logs/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
@router.post("", status_code=status.HTTP_403_FORBIDDEN)
@router.put("/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
@router.patch("/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
@router.delete("/{audit_id}", status_code=status.HTTP_403_FORBIDDEN)
async def reject_audit_mutation():
    """
    Security Guarantee: Audit records are immutable.
    Client-side creation, modification, or deletion is strictly forbidden.
    """
    raise ForbiddenException(
        "Audit trail records are immutable and cannot be created, modified, or deleted by client requests."
    )

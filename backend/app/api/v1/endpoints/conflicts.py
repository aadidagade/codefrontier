import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies import authorization
from app.dependencies.authorization import require_project_membership
from app.models.user import User
from app.models.project import ProjectMemberRole
from app.models.conflict import Conflict
from app.models.audit_log import AuditActionType, AuditEntityType
from app.services.audit_service import AuditService
from app.schemas.common import ApiResponse
from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    ConflictResponse,
    ConflictResolveRequest,
    ConflictUpdateRequest,
    ContradictionDetectionReport,
    normalize_conflict_status,
)
from app.services.contradiction_service import ContradictionDetectionService
from app.services.rag_service import RAGService
from app.core.exceptions import NotFoundException, ValidationException, ForbiddenException
from app.core.permissions import Permission, ProjectRole, normalize_role, has_permission

# Router for /conflicts/...
router = APIRouter()

# Router for /projects/{project_id}/conflicts
project_conflicts_router = APIRouter()


# =============================================================================
# PROJECT-SCOPED CONFLICT ENDPOINTS (/projects/{project_id}/conflicts)
# =============================================================================

@project_conflicts_router.get(
    "/{project_id}/conflicts",
    response_model=ApiResponse[List[ConflictResponse]],
    summary="List Project Knowledge Conflicts",
    description="Returns all contradictory facts detected across project documents with source excerpts, page numbers, and status.",
)
async def list_project_conflicts(
    project_id: uuid.UUID,
    handoverId: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership()(project_id=project_id, current_user=current_user, db=db)

    stmt = select(Conflict).where(Conflict.project_id == project_id)
    if handoverId:
        stmt = stmt.where(Conflict.handover_id == handoverId)
    if status_filter:
        norm = normalize_conflict_status(status_filter)
        stmt = stmt.where(
            or_(
                Conflict.status == norm,
                Conflict.status == status_filter.upper(),
                Conflict.status == status_filter,
            )
        )

    stmt = stmt.order_by(Conflict.created_at.desc())
    result = await db.execute(stmt)
    if hasattr(result, "scalars"):
        sc = result.scalars()
        if hasattr(sc, "__await__"):
            sc = await sc
        records = sc.all() if hasattr(sc, "all") else []
        if hasattr(records, "__await__"):
            records = await records
    else:
        records = []

    items = [ConflictResponse.model_validate(c) for c in records]

    return ApiResponse(
        data=items,
        message=f"Retrieved {len(items)} knowledge conflict(s) for project.",
    )


@project_conflicts_router.post(
    "/{project_id}/conflicts/detect",
    response_model=ApiResponse[List[ConflictResponse]],
    summary="Run On-Demand Conflict Detection Across Project Documents",
    description="Scans all uploaded project documents to identify conflicting deadlines, tech stacks, task statuses, or team responsibilities.",
)
async def trigger_conflict_detection(
    project_id: uuid.UUID,
    handoverId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[
            ProjectMemberRole.ADMIN,
            ProjectMemberRole.PROJECT_OWNER,
            ProjectMemberRole.OUTGOING,
            ProjectMemberRole.LEAD,
        ]
    )(project_id=project_id, current_user=current_user, db=db)

    service = ContradictionDetectionService(db)
    report = await service.detect_project_conflicts(project_id=project_id, handover_id=handoverId)

    return ApiResponse(
        data=report.conflicts,
        message=f"Conflict detection completed. Identified {len(report.conflicts)} contradiction(s).",
    )


@project_conflicts_router.post(
    "/{project_id}/conflicts/report",
    response_model=ApiResponse[ContradictionDetectionReport],
    summary="Run Contradiction Detection and Return Detailed Audit Report",
)
async def trigger_conflict_detection_report(
    project_id: uuid.UUID,
    handoverId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[
            ProjectMemberRole.ADMIN,
            ProjectMemberRole.PROJECT_OWNER,
            ProjectMemberRole.OUTGOING,
            ProjectMemberRole.LEAD,
        ]
    )(project_id=project_id, current_user=current_user, db=db)

    service = ContradictionDetectionService(db)
    report = await service.detect_project_conflicts(project_id=project_id, handover_id=handoverId)

    return ApiResponse(
        data=report,
        message=f"Contradiction detection report generated with {report.contradictions_detected} contradiction(s).",
    )


# =============================================================================
# GLOBAL CONFLICT ENDPOINTS (/conflicts/...)
# =============================================================================

@router.get(
    "/categories",
    response_model=ApiResponse[List[str]],
    summary="List Supported Conflict Categories",
)
async def list_conflict_categories():
    return ApiResponse(
        data=[c.value for c in ConflictCategory],
        message="Supported contradiction categories retrieved.",
    )


@router.get(
    "",
    response_model=ApiResponse[List[ConflictResponse]],
    summary="List Knowledge Conflicts (Query Param)",
)
async def list_conflicts_query(
    projectId: Optional[uuid.UUID] = None,
    handoverId: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not projectId:
        return ApiResponse(data=[], message="Project ID parameter 'projectId' is required.")

    await require_project_membership()(project_id=projectId, current_user=current_user, db=db)

    stmt = select(Conflict).where(Conflict.project_id == projectId)
    if handoverId:
        stmt = stmt.where(Conflict.handover_id == handoverId)
    if status_filter:
        norm = normalize_conflict_status(status_filter)
        stmt = stmt.where(
            or_(
                Conflict.status == norm,
                Conflict.status == status_filter.upper(),
                Conflict.status == status_filter,
            )
        )

    stmt = stmt.order_by(Conflict.created_at.desc())
    result = await db.execute(stmt)
    if hasattr(result, "scalars"):
        sc = result.scalars()
        if hasattr(sc, "__await__"):
            sc = await sc
        records = sc.all() if hasattr(sc, "all") else []
        if hasattr(records, "__await__"):
            records = await records
    else:
        records = []

    items = [ConflictResponse.model_validate(c) for c in records]

    return ApiResponse(
        data=items,
        message=f"Retrieved {len(items)} knowledge conflict(s).",
    )


@router.get(
    "/{conflict_id}",
    response_model=ApiResponse[ConflictResponse],
    summary="Get Conflict Details (Both Sources & Traceability)",
    description="Returns both conflicting source excerpts, quotations, page numbers, and current resolution status.",
)
async def get_conflict_by_id(
    conflict_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContradictionDetectionService(db)
    conflict = await service.get_conflict(conflict_id)

    await require_project_membership()(project_id=conflict.project_id, current_user=current_user, db=db)

    return ApiResponse(
        data=ConflictResponse.model_validate(conflict),
        message="Conflict details retrieved.",
    )


@router.patch(
    "/{conflict_id}",
    response_model=ApiResponse[ConflictResponse],
    summary="Update Conflict Status or Notes (Unresolved, Under Review, etc.)",
)
async def update_conflict(
    conflict_id: uuid.UUID,
    payload: ConflictUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContradictionDetectionService(db)
    conflict = await service.get_conflict(conflict_id)

    await require_project_membership(
        allowed_roles=[
            ProjectMemberRole.ADMIN,
            ProjectMemberRole.PROJECT_OWNER,
            ProjectMemberRole.LEAD,
            ProjectMemberRole.REVIEWER,
            ProjectMemberRole.OUTGOING,
        ]
    )(project_id=conflict.project_id, current_user=current_user, db=db)

    target_status = payload.status or payload.resolution_status
    if target_status is not None:
        conflict = await service.update_conflict_status(
            conflict_id=conflict_id,
            new_status=target_status,
            notes=payload.notes,
            current_user=current_user,
        )

    if payload.description is not None:
        conflict.description = payload.description
        await db.commit()
        await db.refresh(conflict)

    return ApiResponse(
        data=ConflictResponse.model_validate(conflict),
        message=f"Conflict updated to status '{conflict.status}'.",
    )


@router.post(
    "/{conflict_id}/resolve",
    response_model=ApiResponse[dict],
    summary="Resolve Knowledge Conflict (LEAD / ADMIN Only)",
    description="Records human reviewer arbitration. Stores chosen source/value, resolution explanation, and responsible user.",
)
async def resolve_conflict_by_id(
    conflict_id: uuid.UUID,
    payload: ConflictResolveRequest,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ContradictionDetectionService(db)
    conflict = await service.get_conflict(conflict_id)

    # Authorized roles: Project Owner, Admin, Lead. Reviewers can resolve ONLY when authorized.
    await require_project_membership(
        permission=Permission.RESOLVE_CONFLICT
    )(project_id=conflict.project_id, current_user=current_user, db=db)

    conflict = await service.resolve_conflict(
        conflict_id=conflict_id,
        payload=payload,
        current_user=current_user,
    )

    # Record conflict resolved audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.CONFLICT_RESOLVED,
        entity_type=AuditEntityType.CONFLICT,
        entity_id=conflict.id,
        user_id=current_user.id,
        project_id=conflict.project_id,
        change_metadata={
            "conflict_id": str(conflict.id),
            "status": conflict.status,
            "resolution_status": conflict.resolution_status,
            "chosen_source": payload.chosen_source,
            "category": getattr(conflict, "category", getattr(conflict, "conflict_category", getattr(conflict, "conflict_type", "general"))),
            "severity": getattr(conflict, "severity", "medium"),
            "notes": payload.resolution_notes or payload.explanation,
        },
        request=request,
    )

    return ApiResponse(
        data={
            "conflictId": str(conflict.id),
            "status": conflict.status,
            "resolution_status": conflict.resolution_status,
            "resolvedBy": str(current_user.id),
            "explanation": payload.resolution_notes or payload.explanation,
            "authoritativeValue": payload.authoritative_value or payload.chosen_value,
        },
        message=f"Conflict marked as {conflict.status} with human arbitration recorded.",
    )


# Backwards compatibility alias for POST /resolve taking body
class LegacyResolveBody(BaseModel):
    conflictId: uuid.UUID
    resolutionType: Optional[str] = "resolved"
    chosenValue: Optional[str] = None
    resolutionNote: str
    correctionText: Optional[str] = None


@router.post(
    "/resolve",
    response_model=ApiResponse[dict],
    summary="Resolve Knowledge Conflict (Body conflictId alias)",
)
async def resolve_conflict_legacy(
    payload: LegacyResolveBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolve_req = ConflictResolveRequest(
        chosen_source=payload.resolutionType,
        authoritative_value=payload.chosenValue or payload.correctionText,
        chosen_value=payload.chosenValue or payload.correctionText,
        resolution_notes=payload.resolutionNote,
        explanation=payload.resolutionNote,
        status="Dismissed" if str(payload.resolutionType).lower() == "dismissed" else "Resolved",
    )
    return await resolve_conflict_by_id(
        conflict_id=payload.conflictId,
        payload=resolve_req,
        current_user=current_user,
        db=db,
    )

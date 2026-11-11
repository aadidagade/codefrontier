import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_project_membership
from app.models.user import User
from app.models.project import ProjectMemberRole
from app.models.conflict import Conflict
from app.schemas.common import ApiResponse
from app.schemas.handover import (
    ConflictResponse,
    ConflictResolveRequest,
    ConflictUpdateRequest,
)
from app.services.rag_service import RAGService
from app.core.exceptions import NotFoundException, ValidationException

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
        stmt = stmt.where(Conflict.status == status_filter.upper())

    stmt = stmt.order_by(Conflict.created_at.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        ConflictResponse(
            id=c.id,
            project_id=c.project_id,
            handover_id=c.handover_id,
            conflict_type=c.conflict_type,
            description=c.description,
            source_a=c.source_a,
            source_b=c.source_b,
            status=c.status,
            resolution=c.resolution,
            resolved_by=c.resolved_by,
            created_at=c.created_at,
        )
        for c in records
    ]

    return ApiResponse(
        data=items,
        message=f"Retrieved {len(items)} knowledge conflict(s) for project.",
    )


@project_conflicts_router.post(
    "/{project_id}/conflicts/detect",
    response_model=ApiResponse[List[ConflictResponse]],
    summary="Run On-Demand Conflict Detection Across Project Documents",
    description="Scans all uploaded project documents to identify conflicting deadlines, owners, configurations, or architecture choices.",
)
async def trigger_conflict_detection(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
    )(project_id=project_id, current_user=current_user, db=db)

    rag = RAGService(db)
    detected_raw = await rag.detect_conflicts(project_id=project_id)

    new_conflicts = []
    for conf in detected_raw:
        conflict_rec = Conflict(
            id=uuid.uuid4(),
            project_id=project_id,
            conflict_type=conf.get("conflict_type", "architecture"),
            description=conf.get("description", "Contradiction identified between documents."),
            source_a={"text": conf.get("source_a_quote", ""), "chunk_id": conf.get("source_a_chunk_id")},
            source_b={"text": conf.get("source_b_quote", ""), "chunk_id": conf.get("source_b_chunk_id")},
            status="OPEN",
        )
        db.add(conflict_rec)
        new_conflicts.append(conflict_rec)

    await db.commit()

    return ApiResponse(
        data=[
            ConflictResponse(
                id=c.id,
                project_id=c.project_id,
                handover_id=c.handover_id,
                conflict_type=c.conflict_type,
                description=c.description,
                source_a=c.source_a,
                source_b=c.source_b,
                status=c.status,
                resolution=c.resolution,
                resolved_by=c.resolved_by,
                created_at=c.created_at,
            )
            for c in new_conflicts
        ],
        message=f"Conflict detection completed. Identified {len(new_conflicts)} contradiction(s).",
    )


# =============================================================================
# GLOBAL CONFLICT ENDPOINTS (/conflicts/...)
# =============================================================================

@router.get(
    "",
    response_model=ApiResponse[List[ConflictResponse]],
    summary="List Knowledge Conflicts (Query Param)",
)
async def list_conflicts_query(
    projectId: Optional[uuid.UUID] = None,
    handoverId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not projectId:
        return ApiResponse(data=[], message="Project ID parameter 'projectId' is required.")

    await require_project_membership()(project_id=projectId, current_user=current_user, db=db)

    stmt = select(Conflict).where(Conflict.project_id == projectId)
    if handoverId:
        stmt = stmt.where(Conflict.handover_id == handoverId)

    stmt = stmt.order_by(Conflict.created_at.desc())
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [
        ConflictResponse(
            id=c.id,
            project_id=c.project_id,
            handover_id=c.handover_id,
            conflict_type=c.conflict_type,
            description=c.description,
            source_a=c.source_a,
            source_b=c.source_b,
            status=c.status,
            resolution=c.resolution,
            resolved_by=c.resolved_by,
            created_at=c.created_at,
        )
        for c in records
    ]

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
    stmt = select(Conflict).where(Conflict.id == conflict_id)
    result = await db.execute(stmt)
    conflict = result.scalars().first()
    if not conflict:
        raise NotFoundException("Conflict", conflict_id)

    await require_project_membership()(project_id=conflict.project_id, current_user=current_user, db=db)

    return ApiResponse(
        data=ConflictResponse(
            id=conflict.id,
            project_id=conflict.project_id,
            handover_id=conflict.handover_id,
            conflict_type=conflict.conflict_type,
            description=conflict.description,
            source_a=conflict.source_a,
            source_b=conflict.source_b,
            status=conflict.status,
            resolution=conflict.resolution,
            resolved_by=conflict.resolved_by,
            created_at=conflict.created_at,
        ),
        message="Conflict details retrieved.",
    )


@router.patch(
    "/{conflict_id}",
    response_model=ApiResponse[ConflictResponse],
    summary="Update Conflict Status or Notes (OPEN, UNDER_REVIEW, etc.)",
)
async def update_conflict(
    conflict_id: uuid.UUID,
    payload: ConflictUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conflict).where(Conflict.id == conflict_id)
    result = await db.execute(stmt)
    conflict = result.scalars().first()
    if not conflict:
        raise NotFoundException("Conflict", conflict_id)

    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD, ProjectMemberRole.OUTGOING]
    )(project_id=conflict.project_id, current_user=current_user, db=db)

    if payload.status is not None:
        valid_statuses = ("OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED")
        normalized_status = payload.status.upper()
        if normalized_status not in valid_statuses:
            raise ValidationException(f"Invalid status '{payload.status}'. Must be one of: {valid_statuses}")
        conflict.status = normalized_status

    if payload.description is not None:
        conflict.description = payload.description

    if payload.notes is not None:
        existing_res = conflict.resolution or {}
        existing_res["reviewer_notes"] = payload.notes
        conflict.resolution = existing_res

    await db.commit()
    await db.refresh(conflict)

    return ApiResponse(
        data=ConflictResponse(
            id=conflict.id,
            project_id=conflict.project_id,
            handover_id=conflict.handover_id,
            conflict_type=conflict.conflict_type,
            description=conflict.description,
            source_a=conflict.source_a,
            source_b=conflict.source_b,
            status=conflict.status,
            resolution=conflict.resolution,
            resolved_by=conflict.resolved_by,
            created_at=conflict.created_at,
        ),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conflict).where(Conflict.id == conflict_id)
    result = await db.execute(stmt)
    conflict = result.scalars().first()
    if not conflict:
        raise NotFoundException("Conflict", conflict_id)

    # Strictly restricted to LEAD or ADMIN roles
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
    )(project_id=conflict.project_id, current_user=current_user, db=db)

    resolution_status = "DISMISSED" if payload.status.upper() == "DISMISSED" else "RESOLVED"
    conflict.status = resolution_status
    conflict.resolution = {
        "chosen_source": payload.chosen_source,
        "chosen_value": payload.chosen_value,
        "resolution_explanation": payload.resolution_notes,
        "resolved_by_name": current_user.full_name or current_user.email,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    conflict.resolved_by = current_user.id
    await db.commit()

    return ApiResponse(
        data={
            "conflictId": str(conflict.id),
            "status": conflict.status,
            "resolvedBy": str(current_user.id),
            "explanation": payload.resolution_notes,
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
        chosen_value=payload.chosenValue or payload.correctionText,
        resolution_notes=payload.resolutionNote,
        status="DISMISSED" if payload.resolutionType == "dismissed" else "RESOLVED",
    )
    return await resolve_conflict_by_id(
        conflict_id=payload.conflictId,
        payload=resolve_req,
        current_user=current_user,
        db=db,
    )

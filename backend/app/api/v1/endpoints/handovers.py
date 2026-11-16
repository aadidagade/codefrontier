import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    require_handover_access,
    require_project_membership,
    require_permission,
    enforce_member_permission,
)
from app.core.permissions import Permission, ProjectRole, normalize_role
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.handover import Handover, HandoverSection, HandoverAuditLog, HandoverVersion
from app.models.conflict import Conflict
from app.models.task import Task, TaskDependency, TaskProgressUpdate
from app.models.notification import Notification
from app.models.audit_log import AuditActionType, AuditEntityType
from app.services.audit_service import AuditService
from app.schemas.common import ApiResponse
from app.schemas.handover import (
    GenerationRequest,
    SectionRegenerateRequest,
    HandoverDetailResponse,
    HandoverSummaryResponse,
    HandoverSectionResponse,
    HandoverSectionUpdate,
    EvidenceReferenceResponse,
    ConflictResponse,
    TaskResponse,
    HandoverStatus,
    HandoverTransitionStatus,
    normalize_transition_status,
    TransitionStatusUpdateRequest,
    HandoverContinuityTaskSummary,
    HandoverContinuityResponse,
    SharedHandoverResponse,
    SubmitReviewRequest,
    RequestChangesRequest,
    ApproveHandoverRequest,
    ShareHandoverRequest,
    AcknowledgeHandoverRequest,
    RejectHandoverRequest,
    RestoreVersionRequest,
    HandoverAuditLogResponse,
    HandoverVersionResponse,
    HandoverHistoryResponse,
    VersionCreateRequest,
    VersionDiffResponse,
    SectionDiff,
)
from app.services.rag_service import RAGService
from app.services.pdf_export_service import PDFExportService
from app.services.notification_service import NotificationService
from app.services.version_service import HandoverVersionService, increment_version, build_handover_snapshot
from app.core.exceptions import ForbiddenException, NotFoundException, BadRequestException

logger = logging.getLogger("app.api.handovers")

# Router mounted at /handovers
router = APIRouter()

# Router mounted at /projects for RESTful /projects/{project_id}/handovers/...
project_handovers_router = APIRouter()


async def fetch_full_handover(handover_id: uuid.UUID, db: AsyncSession) -> Optional[Handover]:
    """Retrieves full handover graph including sections, citations, conflicts, tasks, versions, and logs."""
    stmt = (
        select(Handover)
        .where(Handover.id == handover_id)
        .options(
            selectinload(Handover.sections).selectinload(HandoverSection.evidence_references),
            selectinload(Handover.conflicts),
            selectinload(Handover.tasks),
            selectinload(Handover.versions),
            selectinload(Handover.audit_logs),
        )
    )
    res = await db.execute(stmt)
    return res.scalars().first()


# =============================================================================
# PROJECT-SCOPED HANDOVER ENDPOINTS (/projects/{project_id}/handovers)
# =============================================================================

@project_handovers_router.post(
    "/{project_id}/handovers/generate",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Generate 10-Chapter Knowledge Handover",
    description="Loads project documentation, executes category-targeted hybrid retrieval, sends evidence to Gemini, validates 10 required sections, and saves handover as DRAFT. Requires GENERATE_HANDOVER permission.",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
async def generate_project_handover(
    project_id: uuid.UUID,
    req: GenerationRequest,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce GENERATE_HANDOVER permission and membership
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.GENERATE_HANDOVER,
    )(project_id=project_id, current_user=current_user, db=db)

    # Set project ID in request
    req.projectId = project_id

    service = RAGService(db)
    handover = await service.synthesize_handover(req, user_id=current_user.id)

    # Initialize Handover Version 1.0 snapshot
    version_svc = HandoverVersionService(db)
    await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=current_user.id,
        version_number=handover.version or "v1.0",
        version_description="Initial AI-powered 10-chapter knowledge handover generation",
        approval_status=HandoverStatus.DRAFT.value,
        mark_as_latest=True,
    )

    # Record handover generated audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_GENERATED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=current_user.id,
        project_id=handover.project_id,
        change_metadata={
            "title": handover.title,
            "version": handover.version,
            "status": handover.status,
            "sections_count": len(handover.sections) if hasattr(handover, "sections") else 10,
        },
        request=request,
    )

    return ApiResponse(
        data={
            "handoverId": str(handover.id),
            "projectId": str(handover.project_id),
            "title": handover.title,
            "status": handover.status,  # strictly "draft"
            "version": handover.version,
            "sectionsCount": len(handover.sections) if hasattr(handover, "sections") else 10,
        },
        message="AI-powered 10-chapter knowledge handover generated and saved as DRAFT.",
    )


@project_handovers_router.get(
    "/{project_id}/handovers",
    response_model=ApiResponse[List[HandoverSummaryResponse]],
    summary="List Project Knowledge Handovers",
    description="Retrieves handovers for a given project. INCOMING members can only see approved or acknowledged handovers.",
)
async def list_project_handovers(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_project_membership()(project_id=project_id, current_user=current_user, db=db)

    stmt = (
        select(Handover)
        .where(Handover.project_id == project_id)
        .options(
            selectinload(Handover.sections),
            selectinload(Handover.conflicts),
            selectinload(Handover.tasks),
        )
        .order_by(Handover.created_at.desc())
    )

    if member.role == ProjectMemberRole.INCOMING.value:
        stmt = stmt.where(Handover.status.in_(["APPROVED", "SHARED", "ACKNOWLEDGED", "approved", "shared", "acknowledged"]))

    result = await db.execute(stmt)
    records = result.scalars().all()

    summaries = [
        HandoverSummaryResponse(
            id=h.id,
            project_id=h.project_id,
            title=h.title,
            status=h.status,
            version=h.version,
            created_by=h.created_by,
            assigned_to=h.assigned_to,
            generated_at=h.generated_at,
            approved_at=h.approved_at,
            shared_at=h.shared_at,
            transition_status=h.transition_status or "Awaiting Acknowledgement",
            acknowledged_at=h.acknowledged_at,
            acknowledged_by=h.acknowledged_by,
            created_at=h.created_at,
            updated_at=h.updated_at,
            sections_count=len(h.sections),
            conflicts_count=len(h.conflicts),
            tasks_count=len(h.tasks),
        )
        for h in records
    ]

    return ApiResponse(
        data=summaries,
        message=f"Retrieved {len(summaries)} handover sessions for project.",
    )


# =============================================================================
# GLOBAL HANDOVER ENDPOINTS (/handovers/...)
# =============================================================================

@router.post(
    "/generate",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Knowledge Handover (Body projectId)",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
async def generate_handover_direct(
    req: GenerationRequest,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not req.projectId:
        raise NotFoundException("Project", "None")

    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.GENERATE_HANDOVER,
    )(project_id=req.projectId, current_user=current_user, db=db)

    service = RAGService(db)
    handover = await service.synthesize_handover(req, user_id=current_user.id)

    # Initialize Handover Version 1.0 snapshot
    version_svc = HandoverVersionService(db)
    await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=current_user.id,
        version_number=handover.version or "v1.0",
        version_description="Initial AI-powered 10-chapter knowledge handover generation",
        approval_status=HandoverStatus.DRAFT.value,
        mark_as_latest=True,
    )

    # Record handover generated audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_GENERATED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=current_user.id,
        project_id=handover.project_id,
        change_metadata={
            "title": handover.title,
            "version": handover.version,
            "status": handover.status,
            "sections_count": len(handover.sections) if hasattr(handover, "sections") else 10,
        },
        request=request,
    )

    return ApiResponse(
        data={
            "handoverId": str(handover.id),
            "projectId": str(handover.project_id),
            "title": handover.title,
            "status": handover.status,
            "version": handover.version,
            "sectionsCount": len(handover.sections) if hasattr(handover, "sections") else 10,
        },
        message="Knowledge handover generated and saved as DRAFT.",
    )


@router.get(
    "",
    response_model=ApiResponse[List[HandoverSummaryResponse]],
    summary="List Handover Sessions",
)
async def list_handovers_global(
    projectId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not projectId:
        return ApiResponse(data=[], message="Project ID parameter 'projectId' is required.")

    member = await require_project_membership()(project_id=projectId, current_user=current_user, db=db)

    stmt = (
        select(Handover)
        .where(Handover.project_id == projectId)
        .options(
            selectinload(Handover.sections),
            selectinload(Handover.conflicts),
            selectinload(Handover.tasks),
        )
        .order_by(Handover.created_at.desc())
    )

    if member.role == ProjectMemberRole.INCOMING.value:
        stmt = stmt.where(Handover.status.in_(["APPROVED", "SHARED", "ACKNOWLEDGED", "approved", "shared", "acknowledged"]))

    result = await db.execute(stmt)
    records = result.scalars().all()

    summaries = [
        HandoverSummaryResponse(
            id=h.id,
            project_id=h.project_id,
            title=h.title,
            status=h.status,
            version=h.version,
            created_by=h.created_by,
            assigned_to=h.assigned_to,
            generated_at=h.generated_at,
            approved_at=h.approved_at,
            shared_at=h.shared_at,
            transition_status=h.transition_status or "Awaiting Acknowledgement",
            acknowledged_at=h.acknowledged_at,
            acknowledged_by=h.acknowledged_by,
            created_at=h.created_at,
            updated_at=h.updated_at,
            sections_count=len(h.sections),
            conflicts_count=len(h.conflicts),
            tasks_count=len(h.tasks),
        )
        for h in records
    ]

    return ApiResponse(
        data=summaries,
        message=f"Retrieved {len(summaries)} handover sessions.",
    )


@router.get(
    "/shared-with-me",
    response_model=ApiResponse[List[SharedHandoverResponse]],
    summary="List Handovers Shared With Incoming Member",
    description="Retrieves all approved, shared, or acknowledged handovers accessible to the current incoming member across their projects.",
)
async def list_shared_with_me_handovers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pm_stmt = select(ProjectMember).where(ProjectMember.user_id == current_user.id)
    pm_res = await db.execute(pm_stmt)
    memberships = pm_res.scalars().all() if hasattr(pm_res, "scalars") else []
    project_ids = [m.project_id for m in memberships]

    if not project_ids:
        direct_stmt = (
            select(Handover)
            .where(Handover.assigned_to == current_user.id)
            .options(
                selectinload(Handover.project),
                selectinload(Handover.tasks),
                selectinload(Handover.assignee),
                selectinload(Handover.acknowledger),
            )
            .order_by(Handover.created_at.desc())
        )
        h_res = await db.execute(direct_stmt)
        handovers = h_res.scalars().all() if hasattr(h_res, "scalars") else []
    else:
        stmt = (
            select(Handover)
            .where(
                (Handover.assigned_to == current_user.id)
                | (
                    Handover.project_id.in_(project_ids)
                    & Handover.status.in_(["APPROVED", "SHARED", "ACKNOWLEDGED", "approved", "shared", "acknowledged"])
                )
            )
            .options(
                selectinload(Handover.project),
                selectinload(Handover.tasks),
                selectinload(Handover.assignee),
                selectinload(Handover.acknowledger),
            )
            .order_by(Handover.created_at.desc())
        )
        h_res = await db.execute(stmt)
        handovers = h_res.scalars().all() if hasattr(h_res, "scalars") else []

    now = datetime.now(timezone.utc)
    results = []
    for h in handovers:
        h_tasks = h.tasks if hasattr(h, "tasks") and h.tasks else []
        pending_cnt = sum(1 for t in h_tasks if (t.status or "").lower() in ("pending", "in_progress", "blocked"))
        overdue_cnt = sum(
            1 for t in h_tasks
            if t.due_date and t.due_date < now and (t.status or "").lower() != "completed"
        )
        proj_title = getattr(h.project, "name", getattr(h.project, "title", None)) if (hasattr(h, "project") and h.project) else None
        assignee_name = (h.assignee.full_name or h.assignee.email) if (hasattr(h, "assignee") and h.assignee) else None
        ack_name = (h.acknowledger.full_name or h.acknowledger.email) if (hasattr(h, "acknowledger") and h.acknowledger) else None

        results.append(
            SharedHandoverResponse(
                id=h.id,
                project_id=h.project_id,
                project_title=proj_title,
                title=h.title,
                version=h.version,
                status=h.status,
                transition_status=h.transition_status or "Awaiting Acknowledgement",
                approved_at=h.approved_at,
                shared_at=h.shared_at,
                acknowledged_at=h.acknowledged_at,
                acknowledged_by=h.acknowledged_by,
                acknowledged_by_name=ack_name,
                assigned_to=h.assigned_to,
                assigned_to_name=assignee_name,
                pending_tasks_count=pending_cnt,
                overdue_tasks_count=overdue_cnt,
            )
        )

    return ApiResponse(
        data=results,
        message=f"Retrieved {len(results)} shared handover package(s).",
    )


@router.get(
    "/{handover_id}",
    response_model=ApiResponse[HandoverDetailResponse],
    summary="Get Full Handover Details with 10 Sections & Claims",
    description="Protected against IDOR. INCOMING members cannot view unapproved drafts.",
)
async def get_handover_details(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Handover)
        .where(Handover.id == handover.id)
        .options(
            selectinload(Handover.sections).selectinload(HandoverSection.evidence_references),
            selectinload(Handover.conflicts),
            selectinload(Handover.tasks),
        )
    )
    result = await db.execute(stmt)
    full_handover = result.scalars().first() or handover

    sections_res = []
    for s in (full_handover.sections or []):
        cits = [
            EvidenceReferenceResponse(
                id=ev.id,
                handover_section_id=ev.handover_section_id,
                document_id=ev.document_id,
                document_chunk_id=ev.document_chunk_id,
                quoted_text=ev.quoted_text,
                page_number=ev.page_number,
                relevance_score=ev.relevance_score,
                verification_status=ev.verification_status,
            )
            for ev in s.evidence_references
        ]
        sections_res.append(
            HandoverSectionResponse(
                id=s.id,
                handover_id=s.handover_id,
                section_type=s.section_type,
                title=s.title,
                content=s.content,
                confidence=s.confidence,
                review_status=s.review_status,
                sort_order=s.sort_order,
                evidence_references=cits,
            )
        )

    conflicts_res = [
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
        for c in (full_handover.conflicts or [])
    ]

    tasks_res = [
        TaskResponse(
            id=t.id,
            project_id=t.project_id,
            handover_id=t.handover_id,
            title=t.title,
            description=t.description,
            assigned_to=t.assigned_to,
            priority=t.priority or "medium",
            status=t.status or "pending",
            due_date=t.due_date,
            created_at=t.created_at or now_utc,
            updated_at=t.updated_at or now_utc,
        )
        for t in (full_handover.tasks or [])
    ]

    detail = HandoverDetailResponse(
        id=full_handover.id,
        project_id=full_handover.project_id,
        created_by=full_handover.created_by,
        assigned_to=full_handover.assigned_to,
        title=full_handover.title,
        status=full_handover.status,
        version=full_handover.version,
        generated_at=full_handover.generated_at,
        approved_at=full_handover.approved_at,
        shared_at=full_handover.shared_at,
        transition_status=full_handover.transition_status or "Awaiting Acknowledgement",
        acknowledged_at=full_handover.acknowledged_at,
        acknowledged_by=full_handover.acknowledged_by,
        acknowledgement_notes=full_handover.acknowledgement_notes,
        checklist_confirmed=full_handover.checklist_confirmed or False,
        created_at=full_handover.created_at,
        updated_at=full_handover.updated_at,
        sections=sections_res,
        conflicts=conflicts_res,
        tasks=tasks_res,
    )

    return ApiResponse(
        data=detail,
        message="Handover details retrieved successfully.",
    )


@router.post(
    "/{handover_id}/sections/{section_id}/regenerate",
    response_model=ApiResponse[HandoverSectionResponse],
    summary="Regenerate Individual Section",
    description="Re-synthesizes a single section using category-targeted RAG evidence. Requires EDIT_HANDOVER permission.",
)
async def regenerate_section(
    section_id: uuid.UUID,
    payload: Optional[SectionRegenerateRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.EDIT_HANDOVER,
        handover_status=handover.status,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    # Versioning & Immutability Guarantee:
    # If regenerating a section in an approved/shared/acknowledged handover, preserve existing approved snapshot
    # and bump the version string (e.g. v1.0 -> v1.1), resetting status to DRAFT for re-review.
    current_status_upper = (handover.status or "").upper()
    if current_status_upper in ("APPROVED", "SHARED", "ACKNOWLEDGED"):
        existing_version_stmt = select(HandoverVersion).where(
            HandoverVersion.handover_id == handover.id,
            HandoverVersion.version_number == handover.version,
        )
        existing_v_res = await db.execute(existing_version_stmt)
        if not existing_v_res.scalars().first():
            full_h = await fetch_full_handover(handover.id, db) or handover
            snap = build_handover_snapshot(full_h, current_user.id)
            db.add(
                HandoverVersion(
                    id=uuid.uuid4(),
                    handover_id=handover.id,
                    version_number=handover.version,
                    snapshot=snap,
                    version_description=f"Preserved approved snapshot {handover.version} before section regeneration",
                    approval_status="APPROVED",
                    created_by=current_user.id,
                    is_latest=False,
                )
            )

        old_version = handover.version
        new_version = increment_version(old_version)
        handover.version = new_version
        handover.status = HandoverStatus.DRAFT.value
        handover.approved_at = None

    instructions = payload.instructions if payload else None
    service = RAGService(db)
    updated_sec = await service.regenerate_section(
        handover_id=handover.id,
        section_id=section_id,
        instructions=instructions,
        user_id=current_user.id,
    )

    cits = [
        EvidenceReferenceResponse(
            id=ev.id,
            handover_section_id=ev.handover_section_id,
            document_id=ev.document_id,
            document_chunk_id=ev.document_chunk_id,
            quoted_text=ev.quoted_text,
            page_number=ev.page_number,
            relevance_score=ev.relevance_score,
            verification_status=ev.verification_status,
        )
        for ev in updated_sec.evidence_references
    ]

    return ApiResponse(
        data=HandoverSectionResponse(
            id=updated_sec.id,
            handover_id=updated_sec.handover_id,
            section_type=updated_sec.section_type,
            title=updated_sec.title,
            content=updated_sec.content,
            confidence=updated_sec.confidence,
            review_status=updated_sec.review_status,
            sort_order=updated_sec.sort_order,
            evidence_references=cits,
        ),
        message=f"Section '{updated_sec.title}' successfully regenerated.",
    )


# =============================================================================
# SECTION UPDATE, REVIEW, APPROVAL, SHARING & VERSIONING WORKFLOW
# =============================================================================

@router.patch(
    "/{handover_id}/sections/{section_id}",
    response_model=ApiResponse[HandoverSectionResponse],
    summary="Update Handover Section Content or Review Status",
    description="Updates section text or review status. Requires EDIT_HANDOVER permission. Incoming members cannot edit approved handovers unless explicitly permitted. If the handover was already approved, creates an immutable version snapshot, bumps the version (e.g. v1.0 -> v1.1), and resets status to DRAFT.",
)
@router.put(
    "/{handover_id}/sections/{section_id}",
    response_model=ApiResponse[HandoverSectionResponse],
    summary="Update Handover Section Content or Review Status",
)
async def update_handover_section(
    section_id: uuid.UUID,
    payload: HandoverSectionUpdate,
    request: Request = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.EDIT_HANDOVER,
        handover_status=handover.status,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    stmt = (
        select(HandoverSection)
        .where(
            HandoverSection.id == section_id,
            HandoverSection.handover_id == handover.id,
        )
        .options(selectinload(HandoverSection.evidence_references))
    )
    result = await db.execute(stmt)
    section = result.scalars().first()
    if not section:
        raise NotFoundException("HandoverSection", section_id)

    # Versioning & Immutability Guarantee:
    # If editing an approved/shared/acknowledged handover, preserve existing approved snapshot
    # and bump the version string (e.g. v1.0 -> v1.1), resetting status to DRAFT for re-review.
    current_status_upper = (handover.status or "").upper()
    if current_status_upper in ("APPROVED", "SHARED", "ACKNOWLEDGED"):
        existing_version_stmt = select(HandoverVersion).where(
            HandoverVersion.handover_id == handover.id,
            HandoverVersion.version_number == handover.version,
        )
        existing_v_res = await db.execute(existing_version_stmt)
        if not existing_v_res.scalars().first():
            full_h = await fetch_full_handover(handover.id, db) or handover
            snap = build_handover_snapshot(full_h, current_user.id)
            db.add(
                HandoverVersion(
                    id=uuid.uuid4(),
                    handover_id=handover.id,
                    version_number=handover.version,
                    snapshot=snap,
                    version_description=f"Preserved approved snapshot {handover.version} before revision",
                    approval_status="APPROVED",
                    created_by=current_user.id,
                    is_latest=False,
                )
            )

        old_version = handover.version
        new_version = increment_version(old_version)
        handover.version = new_version
        handover.status = HandoverStatus.DRAFT.value
        handover.approved_at = None

        db.add(
            HandoverAuditLog(
                id=uuid.uuid4(),
                handover_id=handover.id,
                user_id=current_user.id,
                action="version_bumped",
                details={
                    "from_version": old_version,
                    "to_version": new_version,
                    "reason": "Section modified after approval; new draft version created for review.",
                },
            )
        )

    if payload.title is not None:
        section.title = payload.title
    if payload.content is not None:
        section.content = payload.content
    if payload.review_status is not None:
        section.review_status = payload.review_status

    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="section_updated",
        details={
            "section_id": str(section.id),
            "section_type": section.section_type,
            "review_status": section.review_status,
            "title_modified": payload.title is not None,
            "content_modified": payload.content is not None,
            "handover_version": handover.version,
            "handover_status": handover.status,
        },
    )
    db.add(audit)

    # Record handover modified audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_MODIFIED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=current_user.id,
        project_id=handover.project_id,
        change_metadata={
            "section_id": str(section.id),
            "section_title": section.title,
            "section_type": section.section_type,
            "title_modified": payload.title is not None,
            "content_modified": payload.content is not None,
            "review_status": section.review_status,
            "version": handover.version,
            "status": handover.status,
        },
        request=request,
    )

    await db.commit()
    await db.refresh(section)

    cits = [
        EvidenceReferenceResponse(
            id=ev.id,
            handover_section_id=ev.handover_section_id,
            document_id=ev.document_id,
            document_chunk_id=ev.document_chunk_id,
            quoted_text=ev.quoted_text,
            page_number=ev.page_number,
            relevance_score=ev.relevance_score,
            verification_status=ev.verification_status,
        )
        for ev in section.evidence_references
    ]

    return ApiResponse(
        data=HandoverSectionResponse(
            id=section.id,
            handover_id=section.handover_id,
            section_type=section.section_type,
            title=section.title,
            content=section.content,
            confidence=section.confidence,
            review_status=section.review_status,
            sort_order=section.sort_order,
            evidence_references=cits,
        ),
        message="Section updated successfully.",
    )


@router.post(
    "/{handover_id}/submit-review",
    response_model=ApiResponse[dict],
    summary="Submit Handover for Review",
    description="Transitions handover status from DRAFT or CHANGES_REQUESTED to IN_REVIEW. Requires SUBMIT_HANDOVER_FOR_REVIEW permission.",
)
async def submit_handover_review(
    payload: Optional[SubmitReviewRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.SUBMIT_HANDOVER_FOR_REVIEW,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("DRAFT", "CHANGES_REQUESTED"):
        raise BadRequestException(
            f"Cannot submit handover for review from status '{handover.status}'. "
            "Handover must be in DRAFT or CHANGES_REQUESTED state."
        )

    old_status = handover.status
    handover.status = HandoverStatus.IN_REVIEW.value

    now = datetime.now(timezone.utc)
    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="submitted_for_review",
        details={
            "submitted_by": str(current_user.id),
            "previous_status": old_status,
            "new_status": HandoverStatus.IN_REVIEW.value,
            "notes": payload.notes if payload else None,
            "submitted_at": now.isoformat(),
        },
    )
    db.add(audit)

    # Dispatch notification to project Leads & Admins
    notif_svc = NotificationService(db)
    await notif_svc.notify_handover_submitted_review(
        project_id=handover.project_id,
        handover_title=handover.title,
        submitted_by_name=current_user.full_name or current_user.email,
    )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "status": HandoverStatus.IN_REVIEW.value,
            "submittedAt": now.isoformat(),
        },
        message="Handover submitted for review successfully.",
    )


@router.post(
    "/{handover_id}/request-changes",
    response_model=ApiResponse[dict],
    summary="Request Changes on Handover (Reviewer / Project Owner / Admin)",
    description="Reviewer requests revisions on a submitted handover, specifying feedback and sections to correct. Requires APPROVE_HANDOVER permission.",
)
async def request_changes(
    payload: RequestChangesRequest,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.REVIEWER, ProjectMemberRole.LEAD],
        permission=Permission.APPROVE_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("IN_REVIEW", "DRAFT"):
        raise BadRequestException(
            f"Cannot request changes for handover with status '{handover.status}'. Handover must be in IN_REVIEW."
        )

    old_status = handover.status
    handover.status = HandoverStatus.CHANGES_REQUESTED.value

    # Update specified sections if provided
    if payload.section_ids:
        sec_stmt = select(HandoverSection).where(
            HandoverSection.handover_id == handover.id,
            HandoverSection.id.in_(payload.section_ids),
        )
        sec_res = await db.execute(sec_stmt)
        for sec in sec_res.scalars().all():
            sec.review_status = "changes_requested"

    now = datetime.now(timezone.utc)
    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="changes_requested",
        details={
            "requested_by": str(current_user.id),
            "feedback": payload.feedback,
            "section_ids": [str(sid) for sid in payload.section_ids] if payload.section_ids else [],
            "previous_status": old_status,
            "new_status": HandoverStatus.CHANGES_REQUESTED.value,
            "requested_at": now.isoformat(),
        },
    )
    db.add(audit)

    # Dispatch notification to handover author
    if handover.created_by:
        notif_svc = NotificationService(db)
        await notif_svc.notify_changes_requested(
            author_id=handover.created_by,
            project_id=handover.project_id,
            handover_title=handover.title,
            reviewer_name=current_user.full_name or current_user.email,
            feedback=payload.feedback,
        )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "status": HandoverStatus.CHANGES_REQUESTED.value,
            "feedback": payload.feedback,
            "requestedAt": now.isoformat(),
        },
        message="Changes requested on handover successfully.",
    )


@router.post(
    "/{handover_id}/approve",
    response_model=ApiResponse[dict],
    summary="Approve Handover & Create Immutable Snapshot (Reviewer / Project Owner / Admin)",
    description="Formal sign-off. Creates an immutable version snapshot and transitions status to APPROVED. Requires APPROVE_HANDOVER permission.",
)
async def approve_handover(
    payload: Optional[ApproveHandoverRequest] = None,
    request: Request = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.REVIEWER, ProjectMemberRole.LEAD],
        permission=Permission.APPROVE_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper in ("APPROVED", "SHARED", "ACKNOWLEDGED"):
        raise BadRequestException(f"Handover is already approved with status '{handover.status}'.")

    # Guard: check full handover sections
    full_handover = await fetch_full_handover(handover.id, db)
    if not full_handover:
        raise NotFoundException("Handover", handover.id)

    for s in (full_handover.sections or []):
        if (s.review_status or "").lower() == "rejected":
            raise BadRequestException(f"Cannot approve handover while section '{s.title}' is marked as rejected.")

    now = datetime.now(timezone.utc)
    old_status = full_handover.status
    full_handover.status = HandoverStatus.APPROVED.value
    full_handover.approved_at = now

    # Create immutable version snapshot
    snapshot = build_handover_snapshot(full_handover, current_user.id)
    approve_desc = payload.notes if payload and payload.notes else f"Approved version {full_handover.version}"
    version_record = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=full_handover.id,
        version_number=full_handover.version,
        snapshot=snapshot,
        version_description=approve_desc,
        approval_status=HandoverStatus.APPROVED.value,
        is_latest=True,
        created_by=current_user.id,
        created_at=now,
    )
    db.add(version_record)

    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=full_handover.id,
        user_id=current_user.id,
        action="approved",
        details={
            "approved_by": str(current_user.id),
            "approved_at": now.isoformat(),
            "version": full_handover.version,
            "previous_status": old_status,
            "new_status": HandoverStatus.APPROVED.value,
            "notes": payload.notes if payload else None,
        },
    )
    db.add(audit)

    # Record handover approved audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_APPROVED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=full_handover.id,
        user_id=current_user.id,
        project_id=full_handover.project_id,
        change_metadata={
            "title": full_handover.title,
            "approved_version": full_handover.version,
            "previous_status": old_status,
            "new_status": HandoverStatus.APPROVED.value,
            "notes": payload.notes if payload else None,
        },
        request=request,
    )

    # Dispatch notification to project members
    notif_svc = NotificationService(db)
    await notif_svc.notify_handover_approved(
        project_id=full_handover.project_id,
        handover_title=full_handover.title,
        approved_by_name=current_user.full_name or current_user.email,
    )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(full_handover.id),
            "status": HandoverStatus.APPROVED.value,
            "version": full_handover.version,
            "approvedAt": now.isoformat(),
        },
        message="Handover approved and immutable snapshot created successfully.",
    )


@router.post(
    "/{handover_id}/share",
    response_model=ApiResponse[dict],
    summary="Share Approved Handover with Incoming Members",
    description="Transitions status to SHARED, assigns incoming member, and dispatches in-app notification. Requires SHARE_HANDOVER permission.",
)
async def share_handover(
    payload: Optional[ShareHandoverRequest] = None,
    request: Request = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.REVIEWER, ProjectMemberRole.LEAD],
        permission=Permission.SHARE_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("APPROVED", "SHARED"):
        raise ForbiddenException(
            f"Cannot share handover with status '{handover.status}'. Only approved handovers can be shared with incoming members."
        )

    assigned_user_id = payload.assigned_to if payload and payload.assigned_to else None
    if assigned_user_id:
        # Validate that the assigned user is a member of the project
        await require_project_membership()(
            project_id=handover.project_id,
            current_user=User(id=assigned_user_id),
            db=db,
        )
        handover.assigned_to = assigned_user_id

        # Send in-app notification to assigned incoming member
        notif = Notification(
            id=uuid.uuid4(),
            user_id=assigned_user_id,
            title="Knowledge Handover Shared",
            message=f"Handover '{handover.title}' has been shared with you for onboarding and review.",
            notification_type="handover_shared",
        )
        db.add(notif)

    now = datetime.now(timezone.utc)
    old_status = handover.status
    handover.status = HandoverStatus.SHARED.value
    handover.shared_at = now

    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="shared",
        details={
            "shared_by": str(current_user.id),
            "assigned_to": str(handover.assigned_to) if handover.assigned_to else None,
            "previous_status": old_status,
            "new_status": HandoverStatus.SHARED.value,
            "shared_at": now.isoformat(),
            "notes": payload.notes if payload else None,
            "recipient_emails": payload.recipient_emails if payload else [],
        },
    )
    db.add(audit)

    # Record handover shared audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_SHARED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=current_user.id,
        project_id=handover.project_id,
        change_metadata={
            "title": handover.title,
            "assigned_to": str(handover.assigned_to) if handover.assigned_to else None,
            "previous_status": old_status,
            "new_status": HandoverStatus.SHARED.value,
            "recipient_emails": payload.recipient_emails if payload else [],
        },
        request=request,
    )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "status": HandoverStatus.SHARED.value,
            "sharedAt": now.isoformat(),
            "assignedTo": str(handover.assigned_to) if handover.assigned_to else None,
        },
        message="Handover shared with incoming team member(s).",
    )


@router.post(
    "/{handover_id}/acknowledge",
    response_model=ApiResponse[dict],
    summary="Acknowledge Handover (INCOMING Member)",
    description="Formal sign-off and assumption of project responsibility by incoming team member.",
)
async def acknowledge_handover(
    payload: Optional[AcknowledgeHandoverRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.INCOMING, ProjectMemberRole.ADMIN]
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("APPROVED", "SHARED"):
        raise ForbiddenException(
            f"Only approved or shared handovers can be acknowledged. Current status: '{handover.status}'."
        )

    now = datetime.now(timezone.utc)
    old_status = handover.status
    old_transition = handover.transition_status
    handover.status = HandoverStatus.ACKNOWLEDGED.value
    handover.transition_status = HandoverTransitionStatus.ACKNOWLEDGED.value
    handover.shared_at = handover.shared_at or now
    handover.assigned_to = current_user.id
    handover.acknowledged_at = now
    handover.acknowledged_by = current_user.id
    if payload:
        handover.checklist_confirmed = payload.checklist_confirmed
        handover.acknowledgement_notes = payload.notes
    else:
        handover.checklist_confirmed = True

    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="acknowledged",
        details={
            "acknowledged_by": str(current_user.id),
            "acknowledged_at": now.isoformat(),
            "checklist_confirmed": payload.checklist_confirmed if payload else True,
            "notes": payload.notes if payload else None,
            "previous_status": old_status,
            "new_status": HandoverStatus.ACKNOWLEDGED.value,
            "transition_status": HandoverTransitionStatus.ACKNOWLEDGED.value,
        },
    )
    db.add(audit)

    # Compliance audit log
    audit_svc = AuditService(db)
    await audit_svc.log_event(
        user_id=current_user.id,
        project_id=handover.project_id,
        action_type=AuditActionType.HANDOVER_ACKNOWLEDGED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        details={
            "handover_title": handover.title,
            "acknowledged_at": now.isoformat(),
            "acknowledged_by": str(current_user.id),
            "checklist_confirmed": payload.checklist_confirmed if payload else True,
            "notes": payload.notes if payload else None,
            "transition_status": HandoverTransitionStatus.ACKNOWLEDGED.value,
        },
    )

    # Dispatch notification to project Leads & Outgoing members
    notif_svc = NotificationService(db)
    await notif_svc.notify_handover_acknowledged(
        project_id=handover.project_id,
        handover_title=handover.title,
        acknowledged_by_name=current_user.full_name or current_user.email,
    )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "status": HandoverStatus.ACKNOWLEDGED.value,
            "transitionStatus": HandoverTransitionStatus.ACKNOWLEDGED.value,
            "acknowledgedAt": now.isoformat(),
            "acknowledgedBy": str(current_user.id),
            "assignedTo": str(handover.assigned_to),
        },
        message="Handover acknowledged. Project responsibility accepted.",
    )


@router.patch(
    "/{handover_id}/transition-status",
    response_model=ApiResponse[dict],
    summary="Update Handover Transition Status",
    description="Updates the overall continuity transition status: Awaiting Acknowledgement, Acknowledged, In Progress, Completed.",
)
async def update_handover_transition_status(
    payload: TransitionStatusUpdateRequest,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw_status = payload.transition_status.strip()
    normalized = normalize_transition_status(raw_status)

    old_status = handover.transition_status or "Awaiting Acknowledgement"
    handover.transition_status = normalized

    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="transition_status_updated",
        details={
            "old_transition_status": old_status,
            "new_transition_status": normalized,
            "notes": payload.notes,
        },
    )
    db.add(audit)

    audit_svc = AuditService(db)
    await audit_svc.log_event(
        user_id=current_user.id,
        project_id=handover.project_id,
        action_type=AuditActionType.TRANSITION_STATUS_UPDATED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        details={
            "old_transition_status": old_status,
            "new_transition_status": normalized,
            "notes": payload.notes,
        },
    )

    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "transitionStatus": handover.transition_status,
            "previousStatus": old_status,
            "notes": payload.notes,
        },
        message=f"Transition status updated to '{normalized}'.",
    )


@router.get(
    "/{handover_id}/continuity",
    response_model=ApiResponse[HandoverContinuityResponse],
    summary="Get Handover Continuity Dashboard",
    description="Returns comprehensive continuity workflow data: approved handover, latest version, pending tasks, overdue tasks, blockers, conflicts, and transition progress.",
)
async def get_handover_continuity(
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch project details
    p_stmt = select(Project).where(Project.id == handover.project_id)
    p_res = await db.execute(p_stmt)
    project = p_res.scalars().first() if hasattr(p_res, "scalars") else None
    project_title = getattr(project, "name", getattr(project, "title", None)) if project else None

    # Fetch names for acknowledger and assignee
    ack_name = None
    if handover.acknowledged_by:
        ack_res = await db.execute(select(User).where(User.id == handover.acknowledged_by))
        ack_user = ack_res.scalars().first() if hasattr(ack_res, "scalars") else None
        if ack_user:
            val = getattr(ack_user, "full_name", None) or getattr(ack_user, "email", None)
            ack_name = str(val) if isinstance(val, str) else None

    assignee_name = None
    if handover.assigned_to:
        as_res = await db.execute(select(User).where(User.id == handover.assigned_to))
        as_user = as_res.scalars().first() if hasattr(as_res, "scalars") else None
        if as_user:
            val = getattr(as_user, "full_name", None) or getattr(as_user, "email", None)
            assignee_name = str(val) if isinstance(val, str) else None

    # Fetch latest version snapshot
    latest_v_stmt = (
        select(HandoverVersion)
        .where(HandoverVersion.handover_id == handover.id)
        .order_by(HandoverVersion.created_at.desc())
    )
    latest_v_res = await db.execute(latest_v_stmt)
    versions = latest_v_res.scalars().all() if hasattr(latest_v_res, "scalars") else []
    latest_version_record = None
    for v in versions:
        if v.is_latest:
            latest_version_record = v
            break
    if not latest_version_record and versions:
        latest_version_record = versions[0]

    latest_version_resp = None
    if latest_version_record:
        v_creator_name = None
        if latest_version_record.created_by:
            v_c_res = await db.execute(select(User).where(User.id == latest_version_record.created_by))
            v_c = v_c_res.scalars().first() if hasattr(v_c_res, "scalars") else None
            if v_c:
                val = getattr(v_c, "full_name", None) or getattr(v_c, "email", None)
                v_creator_name = str(val) if isinstance(val, str) else None

        latest_version_resp = HandoverVersionResponse(
            id=latest_version_record.id,
            handover_id=latest_version_record.handover_id,
            version_number=latest_version_record.version_number,
            version_description=latest_version_record.version_description,
            approval_status=latest_version_record.approval_status,
            parent_version_id=latest_version_record.parent_version_id,
            is_latest=latest_version_record.is_latest,
            created_by=latest_version_record.created_by,
            creator_name=v_creator_name,
            created_at=latest_version_record.created_at,
            snapshot=latest_version_record.snapshot,
        )

    # Fetch tasks
    t_stmt = (
        select(Task)
        .where(
            (Task.handover_id == handover.id)
            | ((Task.project_id == handover.project_id) & (Task.handover_id.is_(None)))
        )
        .order_by(Task.created_at.asc())
    )
    t_res = await db.execute(t_stmt)
    all_raw_tasks = t_res.scalars().all() if hasattr(t_res, "scalars") else []

    # Map user names for tasks
    task_user_ids = {t.assigned_to for t in all_raw_tasks if t.assigned_to}
    task_user_map = {}
    if task_user_ids:
        tu_res = await db.execute(select(User).where(User.id.in_(task_user_ids)))
        tu_list = tu_res.scalars().all() if hasattr(tu_res, "scalars") else []
        task_user_map = {u.id: (u.full_name or u.email) for u in tu_list}

    # Fetch task dependencies
    task_ids = [t.id for t in all_raw_tasks]
    dep_map = {}
    if task_ids:
        dep_stmt = select(TaskDependency).where(TaskDependency.task_id.in_(task_ids))
        dep_res = await db.execute(dep_stmt)
        all_deps = dep_res.scalars().all() if hasattr(dep_res, "scalars") else []
        for d in all_deps:
            dep_map.setdefault(d.task_id, []).append(d.depends_on_task_id)

    task_dict = {t.id: t for t in all_raw_tasks}

    now_utc = datetime.now(timezone.utc)
    pending_tasks = []
    in_progress_tasks = []
    completed_tasks = []
    blocked_tasks = []
    overdue_tasks = []
    all_task_responses = []
    unresolved_blockers = []

    for t in all_raw_tasks:
        prereq_ids = dep_map.get(t.id, [])
        is_blocked = False
        blocker_prereqs = []
        for pid in prereq_ids:
            prereq_task = task_dict.get(pid)
            if prereq_task and (prereq_task.status or "").lower() != "completed":
                is_blocked = True
                blocker_prereqs.append({
                    "prerequisite_task_id": str(prereq_task.id),
                    "prerequisite_title": prereq_task.title,
                    "prerequisite_status": prereq_task.status,
                    "assigned_to": task_user_map.get(prereq_task.assigned_to, "Unassigned"),
                })

        if (t.status or "").lower() == "blocked":
            is_blocked = True

        is_overdue = bool(t.due_date and t.due_date < now_utc and (t.status or "").lower() != "completed")

        t_resp = TaskResponse(
            id=t.id,
            project_id=t.project_id,
            handover_id=t.handover_id,
            title=t.title,
            description=t.description,
            assigned_to=t.assigned_to,
            assigned_to_name=task_user_map.get(t.assigned_to),
            priority=t.priority or "medium",
            status=t.status or "pending",
            due_date=t.due_date,
            created_at=t.created_at or now_utc,
            updated_at=t.updated_at or now_utc,
            dependencies_count=len(prereq_ids),
            dependents_count=0,
            is_blocked=is_blocked,
        )
        all_task_responses.append(t_resp)

        status_lower = (t.status or "").lower()
        if status_lower == "completed":
            completed_tasks.append(t_resp)
        elif status_lower == "in_progress":
            in_progress_tasks.append(t_resp)
        else:
            pending_tasks.append(t_resp)

        if is_blocked:
            blocked_tasks.append(t_resp)
            unresolved_blockers.append({
                "task_id": str(t.id),
                "task_title": t.title,
                "task_status": t.status,
                "assigned_to": task_user_map.get(t.assigned_to, "Unassigned"),
                "blocking_prerequisites": blocker_prereqs,
            })

        if is_overdue:
            overdue_tasks.append(t_resp)

    tot = len(all_raw_tasks)
    comp = len(completed_tasks)
    summary = HandoverContinuityTaskSummary(
        total_tasks=tot,
        pending_tasks=len(pending_tasks),
        in_progress_tasks=len(in_progress_tasks),
        completed_tasks=comp,
        blocked_tasks=len(blocked_tasks),
        overdue_tasks=len(overdue_tasks),
        completion_percentage=round((comp / tot * 100), 1) if tot > 0 else 0.0,
    )

    # Unresolved conflicts
    c_stmt = (
        select(Conflict)
        .where(
            (Conflict.handover_id == handover.id)
            | (Conflict.project_id == handover.project_id)
        )
    )
    c_res = await db.execute(c_stmt)
    all_conflicts = c_res.scalars().all() if hasattr(c_res, "scalars") else []
    unresolved_conflicts = [
        ConflictResponse(
            id=c.id,
            project_id=c.project_id,
            section_id=c.handover_id,
            conflict_type=c.conflict_type,
            severity=getattr(c, "severity", "medium"),
            description=c.description,
            status=c.status,
            source_a=c.source_a,
            source_b=c.source_b,
            resolution=c.resolution,
        )
        for c in all_conflicts
        if (c.status or "").upper() != "RESOLVED"
    ]

    # Responsibilities distribution
    member_tasks_map = {}
    for t in all_raw_tasks:
        key = t.assigned_to or "Unassigned"
        member_tasks_map.setdefault(key, []).append(t)

    responsibilities = []
    for uid, u_tasks in member_tasks_map.items():
        name = task_user_map.get(uid, "Unassigned") if uid != "Unassigned" else "Unassigned"
        c_cnt = sum(1 for x in u_tasks if (x.status or "").lower() == "completed")
        p_cnt = len(u_tasks) - c_cnt
        responsibilities.append({
            "user_id": str(uid) if uid != "Unassigned" else None,
            "user_name": name,
            "total_tasks": len(u_tasks),
            "completed_tasks": c_cnt,
            "pending_tasks": p_cnt,
        })

    # Recent progress updates
    recent_progress_updates = []
    if task_ids:
        pu_stmt = (
            select(TaskProgressUpdate)
            .where(TaskProgressUpdate.task_id.in_(task_ids))
            .order_by(TaskProgressUpdate.created_at.desc())
            .limit(20)
        )
        pu_res = await db.execute(pu_stmt)
        pu_records = pu_res.scalars().all() if hasattr(pu_res, "scalars") else []
        for pu in pu_records:
            recent_progress_updates.append({
                "id": str(pu.id),
                "task_id": str(pu.task_id),
                "task_title": getattr(task_dict.get(pu.task_id), "title", "Unknown"),
                "user_id": str(pu.user_id),
                "user_name": task_user_map.get(pu.user_id, "Unknown"),
                "update_text": pu.update_text,
                "status_before": pu.status_before,
                "status_after": pu.status_after,
                "created_at": pu.created_at.isoformat() if pu.created_at else None,
            })

    return ApiResponse(
        data=HandoverContinuityResponse(
            handover_id=handover.id,
            project_id=handover.project_id,
            project_title=project_title,
            title=handover.title,
            version=handover.version or "v1.0",
            status=handover.status,
            transition_status=handover.transition_status or "Awaiting Acknowledgement",
            approved_at=handover.approved_at,
            shared_at=handover.shared_at,
            acknowledged_at=handover.acknowledged_at,
            acknowledged_by=handover.acknowledged_by,
            acknowledged_by_name=ack_name,
            acknowledgement_notes=handover.acknowledgement_notes,
            checklist_confirmed=handover.checklist_confirmed or False,
            assigned_to=handover.assigned_to,
            assigned_to_name=assignee_name,
            latest_version=latest_version_resp,
            tasks_summary=summary,
            pending_tasks=pending_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            blocked_tasks=blocked_tasks,
            overdue_tasks=overdue_tasks,
            all_tasks=all_task_responses,
            unresolved_blockers=unresolved_blockers,
            unresolved_conflicts=unresolved_conflicts,
            responsibilities=responsibilities,
            recent_progress_updates=recent_progress_updates,
        ),
        message="Handover continuity dashboard retrieved successfully.",
    )


@router.post(
    "/{handover_id}/reject",
    response_model=ApiResponse[dict],
    summary="Reject Handover (Reviewer / Project Owner / Admin)",
    description="Formally marks a submitted handover as REJECTED with feedback. Requires APPROVE_HANDOVER permission.",
)
async def reject_handover(
    payload: RejectHandoverRequest,
    request: Request = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.REVIEWER, ProjectMemberRole.LEAD],
        permission=Permission.APPROVE_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("IN_REVIEW", "DRAFT"):
        raise BadRequestException(f"Cannot reject handover with status '{handover.status}'. Must be in review.")

    old_status = handover.status
    handover.status = HandoverStatus.REJECTED.value

    # Record handover rejected audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.HANDOVER_REJECTED,
        entity_type=AuditEntityType.HANDOVER,
        entity_id=handover.id,
        user_id=current_user.id,
        project_id=handover.project_id,
        change_metadata={
            "title": handover.title,
            "version": handover.version,
            "previous_status": old_status,
            "new_status": HandoverStatus.REJECTED.value,
            "reason": payload.reason,
            "rejection_notes": getattr(payload, "rejection_notes", None) or payload.reason,
        },
        request=request,
    )

    now = datetime.now(timezone.utc)
    audit = HandoverAuditLog(
        id=uuid.uuid4(),
        handover_id=handover.id,
        user_id=current_user.id,
        action="rejected",
        details={
            "rejected_by": str(current_user.id),
            "reason": payload.reason,
            "previous_status": old_status,
            "new_status": HandoverStatus.REJECTED.value,
            "rejected_at": now.isoformat(),
        },
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(
        data={
            "id": str(handover.id),
            "status": HandoverStatus.REJECTED.value,
            "reason": payload.reason,
            "rejectedAt": now.isoformat(),
        },
        message="Handover formally rejected.",
    )


@router.get(
    "/{handover_id}/history",
    response_model=ApiResponse[HandoverHistoryResponse],
    summary="Get Handover Lifecycle Audit Trail & Version Snapshots",
    description="Returns chronological audit logs (actions, actors, timestamps) and immutable version snapshots. Requires VIEW_AUDIT_LOGS permission.",
)
async def get_handover_history(
    handover: Handover = Depends(require_handover_access),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if isinstance(current_user, User):
        await require_project_membership(
            permission=Permission.VIEW_AUDIT_LOGS,
        )(project_id=handover.project_id, current_user=current_user, db=db)
    # Fetch audit logs with user information
    audit_stmt = (
        select(HandoverAuditLog)
        .where(HandoverAuditLog.handover_id == handover.id)
        .options(selectinload(HandoverAuditLog.user))
        .order_by(HandoverAuditLog.created_at.desc())
    )
    audit_res = await db.execute(audit_stmt)
    audit_logs = audit_res.scalars().all()

    # Fetch version snapshots with creator information
    version_stmt = (
        select(HandoverVersion)
        .where(HandoverVersion.handover_id == handover.id)
        .options(selectinload(HandoverVersion.creator))
        .order_by(HandoverVersion.created_at.desc())
    )
    version_res = await db.execute(version_stmt)
    versions = version_res.scalars().all()

    history_data = HandoverHistoryResponse(
        handover_id=handover.id,
        current_version=handover.version,
        current_status=handover.status,
        audit_logs=[
            HandoverAuditLogResponse(
                id=a.id,
                handover_id=a.handover_id,
                user_id=a.user_id,
                user_name=a.user.full_name if a.user else None,
                user_email=a.user.email if a.user else None,
                action=a.action,
                details=a.details,
                created_at=a.created_at,
            )
            for a in audit_logs
        ],
        versions=[
            HandoverVersionResponse(
                id=v.id,
                handover_id=v.handover_id,
                version_number=v.version_number,
                version_description=v.version_description,
                approval_status=v.approval_status or "DRAFT",
                parent_version_id=v.parent_version_id,
                is_latest=bool(v.is_latest),
                created_by=v.created_by,
                creator_name=v.creator.full_name if v.creator else None,
                created_at=v.created_at,
                snapshot=v.snapshot or {},
            )
            for v in versions
        ],
    )

    return ApiResponse(
        data=history_data,
        message="Handover lifecycle history retrieved successfully.",
    )


# =============================================================================
# HANDOVER VERSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get(
    "/{handover_id}/versions",
    response_model=ApiResponse[List[HandoverVersionResponse]],
    summary="List All Versions for a Handover",
    description="Retrieves chronological immutable version snapshots with approval status and parent lineage. Requires Handover Access.",
)
@project_handovers_router.get(
    "/{project_id}/handovers/{handover_id}/versions",
    response_model=ApiResponse[List[HandoverVersionResponse]],
    summary="List All Versions for a Handover (Project-Scoped)",
)
async def list_handover_versions(
    handover_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version_svc = HandoverVersionService(db)
    versions = await version_svc.list_versions(handover.id)
    return ApiResponse(
        data=versions,
        message=f"Retrieved {len(versions)} versions for handover.",
    )


@router.get(
    "/{handover_id}/versions/latest",
    response_model=ApiResponse[HandoverVersionResponse],
    summary="Get Latest Version Snapshot for a Handover",
    description="Identifies and returns the active latest version snapshot.",
)
@project_handovers_router.get(
    "/{project_id}/handovers/{handover_id}/versions/latest",
    response_model=ApiResponse[HandoverVersionResponse],
    summary="Get Latest Version Snapshot (Project-Scoped)",
)
async def get_latest_handover_version(
    handover_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version_svc = HandoverVersionService(db)
    latest_v = await version_svc.get_latest_version(handover.id)
    if not latest_v:
        raise NotFoundException("HandoverVersion", "latest")
    return ApiResponse(
        data=version_svc.to_response(latest_v),
        message=f"Retrieved latest version {latest_v.version_number}.",
    )


@router.get(
    "/{handover_id}/versions/{version_id}",
    response_model=ApiResponse[HandoverVersionResponse],
    summary="Get Specific Handover Version Snapshot",
    description="Retrieves an immutable historical version snapshot by ID.",
)
@project_handovers_router.get(
    "/{project_id}/handovers/{handover_id}/versions/{version_id}",
    response_model=ApiResponse[HandoverVersionResponse],
    summary="Get Specific Handover Version Snapshot (Project-Scoped)",
)
async def get_handover_version(
    handover_id: uuid.UUID,
    version_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version_svc = HandoverVersionService(db)
    ver = await version_svc.get_version(handover.id, version_id)
    return ApiResponse(
        data=version_svc.to_response(ver),
        message=f"Retrieved version {ver.version_number}.",
    )


@router.post(
    "/{handover_id}/versions",
    response_model=ApiResponse[HandoverVersionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create New Handover Version Snapshot / Revision",
    description="Creates an immutable snapshot of current state as a new version revision. Requires EDIT_HANDOVER permission.",
)
@project_handovers_router.post(
    "/{project_id}/handovers/{handover_id}/versions",
    response_model=ApiResponse[HandoverVersionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create New Handover Version Snapshot (Project-Scoped)",
)
async def create_handover_version(
    handover_id: uuid.UUID,
    payload: Optional[VersionCreateRequest] = None,
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.EDIT_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    version_svc = HandoverVersionService(db)
    desc = payload.version_description if payload else None
    new_v = await version_svc.create_version_snapshot(
        handover_id=handover.id,
        user_id=current_user.id,
        version_number=handover.version,
        version_description=desc or f"Revision {handover.version}",
        approval_status=(handover.status or "DRAFT").upper(),
        mark_as_latest=True,
    )
    return ApiResponse(
        data=version_svc.to_response(new_v),
        message=f"Version snapshot {new_v.version_number} created successfully.",
    )


@router.get(
    "/{handover_id}/versions/{from_version_id}/compare/{to_version_id}",
    response_model=ApiResponse[VersionDiffResponse],
    summary="Compare Two Handover Versions (Diff)",
    description="Calculates a chapter-by-chapter and section-by-section diff between two historical version snapshots.",
)
@project_handovers_router.get(
    "/{project_id}/handovers/{handover_id}/versions/{from_version_id}/compare/{to_version_id}",
    response_model=ApiResponse[VersionDiffResponse],
    summary="Compare Two Handover Versions (Project-Scoped)",
)
async def compare_handover_versions(
    handover_id: uuid.UUID,
    from_version_id: Union[uuid.UUID, str],
    to_version_id: Union[uuid.UUID, str],
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version_svc = HandoverVersionService(db)
    diff = await version_svc.compare_versions(handover.id, from_version_id, to_version_id)
    return ApiResponse(
        data=diff,
        message=f"Successfully compared versions {diff.from_version_number} and {diff.to_version_number}.",
    )


@router.get(
    "/{handover_id}/compare",
    response_model=ApiResponse[VersionDiffResponse],
    summary="Compare Two Handover Versions via Query Parameters",
    description="Compares two stored handover version snapshots specified by ID or version number.",
)
@project_handovers_router.get(
    "/{project_id}/handovers/{handover_id}/compare",
    response_model=ApiResponse[VersionDiffResponse],
    summary="Compare Two Handover Versions via Query Parameters (Project-Scoped)",
)
async def compare_handover_versions_query(
    handover_id: uuid.UUID,
    from_version: str,
    to_version: str,
    project_id: Optional[uuid.UUID] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    version_svc = HandoverVersionService(db)
    diff = await version_svc.compare_versions(handover.id, from_version, to_version)
    return ApiResponse(
        data=diff,
        message=f"Successfully compared versions {diff.from_version_number} and {diff.to_version_number}.",
    )


@router.post(
    "/{handover_id}/versions/{version_id}/restore",
    response_model=ApiResponse[HandoverDetailResponse],
    summary="Restore Handover to Prior Version Snapshot",
    description="Restores handover sections and content from a historical version snapshot by creating a new revision. Never deletes historical versions. Requires EDIT_HANDOVER permission.",
)
@project_handovers_router.post(
    "/{project_id}/handovers/{handover_id}/versions/{version_id}/restore",
    response_model=ApiResponse[HandoverDetailResponse],
    summary="Restore Handover to Prior Version Snapshot (Project Scoped)",
)
async def restore_handover_version(
    handover_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: Optional[RestoreVersionRequest] = None,
    request: Request = None,
    project_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    handover = await fetch_full_handover(handover_id, db)
    if not handover:
        raise NotFoundException("Handover", handover_id)

    # Permission check: EDIT_HANDOVER
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.PROJECT_OWNER, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD],
        permission=Permission.EDIT_HANDOVER,
    )(project_id=handover.project_id, current_user=current_user, db=db)

    version_svc = HandoverVersionService(db)
    reason = payload.reason if payload and payload.reason else None
    restored_handover, _ = await version_svc.restore_version(
        handover_id=handover_id,
        version_id=version_id,
        user_id=current_user.id,
        reason=reason,
    )
    return await get_handover_details(handover=restored_handover, db=db)


@router.get(
    "/{handover_id}/export/pdf",
    summary="Export Handover Package as Formatted PDF (ReportLab)",
    description="Generates a styled, publication-ready PDF report containing all 10 chapters, citations, recommendations, and action items.",
)
async def export_handover_pdf(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
    full_h = await fetch_full_handover(handover.id, db)
    if not full_h:
        raise NotFoundException("Handover", handover.id)

    proj_stmt = select(Project.name).where(Project.id == full_h.project_id)
    proj_res = await db.execute(proj_stmt)
    proj_name = proj_res.scalar_one_or_none() or "Project Workspace"

    pdf_buffer = PDFExportService.generate_handover_pdf(full_h, project_name=proj_name)
    filename = f"handover_{full_h.id.hex[:8]}_v{full_h.version}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.delete(
    "/{handover_id}",
    response_model=ApiResponse[dict],
    summary="Delete Handover Draft (Admin / Project Owner / Creator)",
)
async def delete_handover(
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_project_membership()(project_id=handover.project_id, current_user=current_user, db=db)

    canonical_role = normalize_role(member.role)
    is_admin = canonical_role in (ProjectRole.ADMIN, ProjectRole.PROJECT_OWNER)
    is_creator = handover.created_by == current_user.id

    if not (is_admin or is_creator):
        raise ForbiddenException("Only the handover creator or a project ADMIN/Owner can delete this handover.")

    if (handover.status or "").upper() in ("ACKNOWLEDGED",) and not is_admin:
        raise ForbiddenException("Acknowledged handovers cannot be deleted except by a project ADMIN or Project Owner.")

    await db.delete(handover)
    await db.commit()

    return ApiResponse(
        data={"id": str(handover.id), "deleted": True},
        message="Handover deleted successfully.",
    )

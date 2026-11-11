import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    require_handover_access,
    require_project_membership,
)
from app.models.user import User
from app.models.project import Project, ProjectMemberRole
from app.models.handover import Handover, HandoverSection, HandoverAuditLog, HandoverVersion
from app.models.conflict import Conflict
from app.models.task import Task
from app.models.notification import Notification
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
    SubmitReviewRequest,
    RequestChangesRequest,
    ApproveHandoverRequest,
    ShareHandoverRequest,
    AcknowledgeHandoverRequest,
    RejectHandoverRequest,
    HandoverAuditLogResponse,
    HandoverVersionResponse,
    HandoverHistoryResponse,
)
from app.services.rag_service import RAGService
from app.services.pdf_export_service import PDFExportService
from app.services.notification_service import NotificationService
from app.core.exceptions import ForbiddenException, NotFoundException, BadRequestException

logger = logging.getLogger("app.api.handovers")

# Router mounted at /handovers
router = APIRouter()

# Router mounted at /projects for RESTful /projects/{project_id}/handovers/...
project_handovers_router = APIRouter()


def increment_version(version_str: str) -> str:
    """
    Increment semantic version string for new draft after an approved snapshot.
    e.g. 'v1.0' -> 'v1.1', '1.0' -> '1.1', 'v1' -> 'v1.1'
    """
    prefix = "v" if version_str.lower().startswith("v") else ""
    raw = version_str.lstrip("vV")
    parts = raw.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        major = parts[0]
        minor = int(parts[1]) + 1
        return f"{prefix}{major}.{minor}"
    elif len(parts) == 1 and parts[0].isdigit():
        return f"{prefix}{parts[0]}.1"
    else:
        return f"{version_str}.1"


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


def build_handover_snapshot(full_h: Handover, user_id: Optional[uuid.UUID] = None) -> dict:
    """Creates a complete JSON-serializable snapshot of an approved handover state."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(full_h.id),
        "project_id": str(full_h.project_id),
        "title": full_h.title,
        "version": full_h.version,
        "status": (full_h.status or "").upper(),
        "created_by": str(full_h.created_by) if full_h.created_by else None,
        "approved_by": str(user_id) if user_id else None,
        "snapshot_created_at": now_iso,
        "sections": [
            {
                "id": str(s.id),
                "section_type": s.section_type,
                "title": s.title,
                "content": s.content,
                "confidence": s.confidence,
                "review_status": s.review_status,
                "sort_order": s.sort_order,
                "evidence_references": [
                    {
                        "id": str(ev.id),
                        "document_id": str(ev.document_id),
                        "document_chunk_id": str(ev.document_chunk_id) if ev.document_chunk_id else None,
                        "quoted_text": ev.quoted_text,
                        "page_number": ev.page_number,
                        "relevance_score": ev.relevance_score,
                        "verification_status": ev.verification_status,
                    }
                    for ev in (s.evidence_references or [])
                ],
            }
            for s in (full_h.sections or [])
        ],
        "conflicts": [
            {
                "id": str(c.id),
                "conflict_type": c.conflict_type,
                "description": c.description,
                "status": c.status,
                "resolution": c.resolution,
            }
            for c in (full_h.conflicts or [])
        ],
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "assigned_to": str(t.assigned_to) if t.assigned_to else None,
            }
            for t in (full_h.tasks or [])
        ],
    }


# =============================================================================
# PROJECT-SCOPED HANDOVER ENDPOINTS (/projects/{project_id}/handovers)
# =============================================================================

@project_handovers_router.post(
    "/{project_id}/handovers/generate",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Generate 10-Chapter Knowledge Handover (OUTGOING / LEAD / ADMIN Only)",
    description="Loads project documentation, executes category-targeted hybrid retrieval, sends evidence to Gemini, validates 10 required sections, and saves handover as DRAFT.",
)
async def generate_project_handover(
    project_id: uuid.UUID,
    req: GenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce role: OUTGOING, LEAD, or ADMIN
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
    )(project_id=project_id, current_user=current_user, db=db)

    # Set project ID in request
    req.projectId = project_id

    service = RAGService(db)
    handover = await service.synthesize_handover(req, user_id=current_user.id)

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
)
async def generate_handover_direct(
    req: GenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not req.projectId:
        raise NotFoundException("Project", "None")

    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
    )(project_id=req.projectId, current_user=current_user, db=db)

    service = RAGService(db)
    handover = await service.synthesize_handover(req, user_id=current_user.id)

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
    full_handover = result.scalars().first()

    sections_res = []
    for s in full_handover.sections:
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
        for c in full_handover.conflicts
    ]

    tasks_res = [
        TaskResponse(
            id=t.id,
            project_id=t.project_id,
            handover_id=t.handover_id,
            title=t.title,
            description=t.description,
            assigned_to=t.assigned_to,
            priority=t.priority,
            status=t.status,
            due_date=t.due_date,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in full_handover.tasks
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
    summary="Regenerate Individual Section (OUTGOING / LEAD / ADMIN Only)",
    description="Re-synthesizes a single section using category-targeted RAG evidence without touching the rest of the handover.",
)
async def regenerate_section(
    section_id: uuid.UUID,
    payload: Optional[SectionRegenerateRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
    )(project_id=handover.project_id, current_user=current_user, db=db)

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
    summary="Update Handover Section Content or Review Status (OUTGOING / LEAD / ADMIN Only)",
    description="Updates section text or review status. If the handover was already approved, creates an immutable version snapshot, bumps the version (e.g. v1.0 -> v1.1), and resets status to DRAFT.",
)
@router.put(
    "/{handover_id}/sections/{section_id}",
    response_model=ApiResponse[HandoverSectionResponse],
    summary="Update Handover Section Content or Review Status (OUTGOING / LEAD / ADMIN Only)",
)
async def update_handover_section(
    section_id: uuid.UUID,
    payload: HandoverSectionUpdate,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
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
            full_h = await fetch_full_handover(handover.id, db)
            if full_h:
                snap = build_handover_snapshot(full_h, current_user.id)
                db.add(
                    HandoverVersion(
                        id=uuid.uuid4(),
                        handover_id=handover.id,
                        version_number=handover.version,
                        snapshot=snap,
                        created_by=current_user.id,
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
    summary="Submit Handover for Review (OUTGOING / LEAD / ADMIN Only)",
    description="Transitions handover status from DRAFT or CHANGES_REQUESTED to IN_REVIEW.",
)
async def submit_handover_review(
    payload: Optional[SubmitReviewRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
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
    summary="Request Changes on Handover (LEAD / ADMIN Only)",
    description="Reviewer requests revisions on a submitted handover, specifying feedback and sections to correct.",
)
async def request_changes(
    payload: RequestChangesRequest,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
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
    summary="Approve Handover & Create Immutable Snapshot (LEAD / ADMIN Only)",
    description="Formal lead sign-off. Creates an immutable version snapshot and transitions status to APPROVED.",
)
async def approve_handover(
    payload: Optional[ApproveHandoverRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
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
    version_record = HandoverVersion(
        id=uuid.uuid4(),
        handover_id=full_handover.id,
        version_number=full_handover.version,
        snapshot=snapshot,
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
    summary="Share Approved Handover with Incoming Members (OUTGOING / LEAD / ADMIN Only)",
    description="Transitions status to SHARED, assigns incoming member, and dispatches in-app notification.",
)
async def share_handover(
    payload: Optional[ShareHandoverRequest] = None,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.OUTGOING, ProjectMemberRole.LEAD]
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
    handover.status = HandoverStatus.ACKNOWLEDGED.value
    handover.shared_at = handover.shared_at or now
    handover.assigned_to = current_user.id

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
        },
    )
    db.add(audit)

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
            "acknowledgedAt": now.isoformat(),
            "assignedTo": str(handover.assigned_to),
        },
        message="Handover acknowledged. Project responsibility accepted.",
    )


@router.post(
    "/{handover_id}/reject",
    response_model=ApiResponse[dict],
    summary="Reject Handover (LEAD / ADMIN Only)",
    description="Formally marks a submitted handover as REJECTED with feedback.",
)
async def reject_handover(
    payload: RejectHandoverRequest,
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
    )(project_id=handover.project_id, current_user=current_user, db=db)

    current_status_upper = (handover.status or "").upper()
    if current_status_upper not in ("IN_REVIEW", "DRAFT"):
        raise BadRequestException(f"Cannot reject handover with status '{handover.status}'. Must be in review.")

    old_status = handover.status
    handover.status = HandoverStatus.REJECTED.value

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
    description="Returns chronological audit logs (actions, actors, timestamps) and immutable version snapshots.",
)
async def get_handover_history(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
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
                created_by=v.created_by,
                creator_name=v.creator.full_name if v.creator else None,
                created_at=v.created_at,
                snapshot=v.snapshot,
            )
            for v in versions
        ],
    )

    return ApiResponse(
        data=history_data,
        message="Handover lifecycle history retrieved successfully.",
    )


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
    summary="Delete Handover Draft (ADMIN / OUTGOING Creator)",
)
async def delete_handover(
    handover: Handover = Depends(require_handover_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_project_membership()(project_id=handover.project_id, current_user=current_user, db=db)

    is_admin = member.role == ProjectMemberRole.ADMIN.value
    is_creator = handover.created_by == current_user.id

    if not (is_admin or is_creator):
        raise ForbiddenException("Only the handover creator or a project ADMIN can delete this handover.")

    if handover.status in ("acknowledged", "ACKNOWLEDGED") and not is_admin:
        raise ForbiddenException("Acknowledged handovers cannot be deleted except by a project ADMIN.")

    await db.delete(handover)
    await db.commit()

    return ApiResponse(
        data={"id": str(handover.id), "deleted": True},
        message="Handover deleted successfully.",
    )

import io
import uuid
from fastapi import APIRouter, Depends, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.schemas.common import ApiResponse
from app.dependencies.authorization import require_handover_access
from app.dependencies.database import get_db
from app.models.handover import Handover, HandoverSection

router = APIRouter()


@router.get(
    "/{handover_id}/markdown",
    response_class=PlainTextResponse,
    summary="Export Approved Handover as Markdown (IDOR Protected)",
    description="Generates an exhaustive Markdown document containing all sections, evidence citations, and action items.",
)
async def export_handover_markdown(
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
    full_h = result.scalars().first()

    lines = [
        f"# {full_h.title}",
        "",
        f"- **Status**: `{full_h.status.upper()}`",
        f"- **Version**: {full_h.version}",
        f"- **Generated At**: {full_h.generated_at.strftime('%Y-%m-%d %H:%M UTC') if full_h.generated_at else 'N/A'}",
        f"- **Approved At**: {full_h.approved_at.strftime('%Y-%m-%d %H:%M UTC') if full_h.approved_at else 'Pending Approval'}",
        "",
        "---",
        "",
    ]

    # Sections
    for sec in full_h.sections:
        lines.append(f"## {sec.title}")
        lines.append(f"*Confidence: {int(sec.confidence * 100)}% | Review: {sec.review_status}*")
        lines.append("")
        content = sec.content or {}
        if isinstance(content, dict):
            if "markdown" in content:
                lines.append(content["markdown"])
                lines.append("")
            if "summary" in content:
                lines.append(f"> {content['summary']}")
                lines.append("")
            if "key_points" in content and isinstance(content["key_points"], list):
                lines.append("### Key Points")
                for kp in content["key_points"]:
                    lines.append(f"- {kp}")
                lines.append("")
        elif isinstance(content, str):
            lines.append(content)
            lines.append("")

        if sec.evidence_references:
            lines.append("#### Evidence & Traceability Citations")
            for cit in sec.evidence_references:
                page_str = f" (Page {cit.page_number})" if cit.page_number else ""
                lines.append(f"- *\"{cit.quoted_text}\"*{page_str} — [Score: {int(cit.relevance_score * 100)}%]")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Continuation Tasks
    if full_h.tasks:
        lines.append("## Actionable Continuation Tasks")
        for idx, t in enumerate(full_h.tasks, start=1):
            lines.append(f"{idx}. **[{t.priority.upper()}] {t.title}** (Status: `{t.status}`)")
            if t.description:
                lines.append(f"   {t.description}")
        lines.append("")

    # Conflicts
    if full_h.conflicts:
        lines.append("## Knowledge Contradictions & Discrepancies")
        for c in full_h.conflicts:
            lines.append(f"- **[{c.conflict_type.upper()}]** {c.description} (Status: `{c.status}`)")
        lines.append("")

    return PlainTextResponse(content="\n".join(lines), media_type="text/markdown")


@router.get(
    "/{handover_id}/json",
    response_model=ApiResponse[dict],
    summary="Export Approved Handover as Structured JSON (IDOR Protected)",
)
async def export_handover_json(
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
    full_h = result.scalars().first()

    data = {
        "id": str(full_h.id),
        "projectId": str(full_h.project_id),
        "title": full_h.title,
        "status": full_h.status,
        "version": full_h.version,
        "generatedAt": full_h.generated_at.isoformat() if full_h.generated_at else None,
        "approvedAt": full_h.approved_at.isoformat() if full_h.approved_at else None,
        "sharedAt": full_h.shared_at.isoformat() if full_h.shared_at else None,
        "sections": [
            {
                "id": str(s.id),
                "sectionType": s.section_type,
                "title": s.title,
                "content": s.content,
                "confidence": s.confidence,
                "reviewStatus": s.review_status,
                "citations": [
                    {
                        "id": str(ev.id),
                        "documentId": str(ev.document_id),
                        "chunkId": str(ev.document_chunk_id) if ev.document_chunk_id else None,
                        "quotedText": ev.quoted_text,
                        "pageNumber": ev.page_number,
                        "relevanceScore": ev.relevance_score,
                    }
                    for ev in s.evidence_references
                ],
            }
            for s in full_h.sections
        ],
        "conflicts": [
            {
                "id": str(c.id),
                "type": c.conflict_type,
                "description": c.description,
                "sourceA": c.source_a,
                "sourceB": c.source_b,
                "status": c.status,
                "resolution": c.resolution,
            }
            for c in full_h.conflicts
        ],
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
            }
            for t in full_h.tasks
        ],
    }

    return ApiResponse(
        data=data,
        message="Structured handover exported in standard JSON format.",
    )


@router.get(
    "/{handover_id}/pdf",
    summary="Export Approved Handover as PDF (ReportLab)",
    description="Compiles the handover package into a publication-ready PDF report with ReportLab.",
)
async def export_handover_pdf(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
    from app.services.pdf_export_service import PDFExportService
    from app.models.project import Project

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
    full_h = result.scalars().first()

    proj_stmt = select(Project.name).where(Project.id == full_h.project_id)
    proj_res = await db.execute(proj_stmt)
    proj_name = proj_res.scalar_one_or_none() or "Project Workspace"

    buffer = PDFExportService.generate_handover_pdf(full_h, project_name=proj_name)
    filename = f"handover_{full_h.id.hex[:8]}_v{full_h.version}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )

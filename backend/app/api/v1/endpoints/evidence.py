import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    require_handover_access,
    require_project_membership,
)
from app.models.user import User
from app.models.handover import Handover, HandoverSection
from app.models.evidence import EvidenceReference
from app.models.document import Document, DocumentChunk
from app.schemas.common import ApiResponse
from app.schemas.handover import (
    ClaimVerificationRequest,
    ClaimVerificationResult,
    HandoverVerificationReport,
)
from app.services.verification_service import EvidenceVerificationService
from app.core.exceptions import NotFoundException

router = APIRouter()


class EvidenceCitation(BaseModel):
    id: str
    claimText: str
    sourceDocId: str
    sourceDocName: str
    pageOrSection: str
    excerpt: str = ""
    confidenceScore: int = 95
    verificationStatus: str = "SUPPORTED"


@router.get(
    "/{handover_id}",
    response_model=ApiResponse[List[EvidenceCitation]],
    summary="List Evidence Citations for Handover (IDOR Protected)",
    description="Returns all traceable evidence links backing factual claims in the handover.",
)
async def list_handover_evidence(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(EvidenceReference, Document.original_filename)
        .join(Document, EvidenceReference.document_id == Document.id)
        .join(HandoverSection, EvidenceReference.handover_section_id == HandoverSection.id)
        .where(HandoverSection.handover_id == handover.id)
    )

    result = await db.execute(stmt)
    rows = result.all()

    citations = [
        EvidenceCitation(
            id=str(ev.id),
            claimText=ev.quoted_text,
            sourceDocId=str(ev.document_id),
            sourceDocName=doc_name,
            pageOrSection=f"Page {ev.page_number}" if ev.page_number else "Section",
            excerpt=ev.quoted_text,
            confidenceScore=int(ev.relevance_score * 100),
            verificationStatus=ev.verification_status,
        )
        for ev, doc_name in rows
    ]

    return ApiResponse(
        data=citations,
        message=f"Retrieved {len(citations)} evidence citation(s).",
    )


@router.get(
    "/passage/{chunk_id}",
    response_model=ApiResponse[dict],
    summary="Get Original Chunk Passage Excerpt (Protected)",
    description="Fetches full passage text and context metadata for an evidence reference.",
)
async def get_chunk_passage(
    chunk_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DocumentChunk, Document.original_filename)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.id == chunk_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise NotFoundException("DocumentChunk", chunk_id)

    chunk, doc_name = row

    # IDOR check: verify user is authorized for the project owning this chunk
    await require_project_membership()(project_id=chunk.project_id, current_user=current_user, db=db)

    return ApiResponse(
        data={
            "chunkId": str(chunk.id),
            "documentId": str(chunk.document_id),
            "documentName": doc_name,
            "chunkIndex": chunk.chunk_index,
            "pageNumber": chunk.page_number,
            "sectionTitle": chunk.section_title,
            "content": chunk.content,
        },
        message="Source chunk passage retrieved successfully.",
    )


@router.post(
    "/verify",
    response_model=ApiResponse[ClaimVerificationResult],
    summary="Verify Factual Claim Against Source Chunks",
    description="Compares a claim directly against source chunk texts and returns an impartial alignment verdict (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, NEEDS_REVIEW).",
)
async def verify_claim_ad_hoc(
    payload: ClaimVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chunks: List[DocumentChunk] = []
    if payload.chunk_ids:
        stmt = select(DocumentChunk).where(DocumentChunk.id.in_(payload.chunk_ids))
        result = await db.execute(stmt)
        chunks = list(result.scalars().all())

    service = EvidenceVerificationService(db)
    eval_result = await service.verify_claim_against_chunks(
        claim_text=payload.claim_text,
        chunks=chunks,
    )

    return ApiResponse(
        data=eval_result,
        message=f"Claim evaluated: status={eval_result.verification_status.value} (score={eval_result.alignment_score:.2f}).",
    )


@router.post(
    "/{evidence_id}/verify",
    response_model=ApiResponse[ClaimVerificationResult],
    summary="Verify Single Stored Evidence Reference",
    description="Evaluates an individual EvidenceReference against its linked chunk and updates its status in PostgreSQL.",
)
async def verify_single_evidence(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EvidenceVerificationService(db)
    result = await service.verify_evidence_reference(evidence_id)

    return ApiResponse(
        data=result,
        message="Evidence reference verified and updated in database.",
    )


@router.post(
    "/handovers/{handover_id}/verify-all",
    response_model=ApiResponse[HandoverVerificationReport],
    summary="Audit & Verify All Claims for Handover",
    description="Evaluates every factual claim across all chapters of a handover against original chunks and compiles a verification report.",
)
async def verify_all_handover_claims(
    handover: Handover = Depends(require_handover_access),
    db: AsyncSession = Depends(get_db),
):
    service = EvidenceVerificationService(db)
    report = await service.verify_handover_all_claims(handover.id)

    return ApiResponse(
        data=report,
        message=f"Handover claims audited: {report.supported_claims}/{report.total_claims} supported.",
    )

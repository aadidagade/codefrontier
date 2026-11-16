import logging
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import (
    require_document_access,
    require_project_membership,
    require_permission,
    enforce_member_permission,
)
from app.core.permissions import Permission
from app.models.user import User
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.document import Document, DocumentChunk
from app.models.audit_log import AuditActionType, AuditEntityType
from app.services.audit_service import AuditService
from app.services.document_processing_service import DocumentProcessingService
from app.repositories.document_repository import DocumentRepository
from app.services.gemini_service import gemini_service
from app.core.rate_limit import rate_limit
from app.schemas.common import ApiResponse
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentStatusResponse,
    DocumentChunkResponse,
    DocumentSearchRequest,
    DocumentSearchResultItem,
)

logger = logging.getLogger("app.api.documents")


async def process_document_background(doc_id: uuid.UUID):
    """Background task worker to run document extraction and vector indexing asynchronously."""
    async with AsyncSessionLocal() as session:
        try:
            service = DocumentProcessingService(session)
            await service.execute_processing_pipeline(doc_id)
        except Exception as exc:
            logger.error(f"Background processing error for document {doc_id}: {exc}")


# Router for /api/v1/documents
router = APIRouter()

# Router for /api/v1/projects/{project_id}/documents
project_documents_router = APIRouter()


# =============================================================================
# PROJECT-SCOPED DOCUMENT ENDPOINTS (/projects/{project_id}/documents)
# =============================================================================

@project_documents_router.post(
    "/{project_id}/documents/upload",
    response_model=ApiResponse[List[DocumentDetailResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Documents to Project (Multi-File Support)",
    description="Uploads one or more documents (PDF, DOCX, TXT, MD), validates MIME/magic bytes, enforces size limits, and triggers text extraction and intelligent chunking. Requires UPLOAD_DOCUMENTS permission.",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
async def upload_documents(
    project_id: uuid.UUID,
    request: Request,
    files: List[UploadFile] = File(..., description="One or more documents to upload"),
    background: bool = Query(False, description="Whether to execute extraction and indexing asynchronously in the background"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    member: ProjectMember = Depends(require_permission(Permission.UPLOAD_DOCUMENTS)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentProcessingService(db)
    audit_svc = AuditService(db)
    processed_documents: List[DocumentDetailResponse] = []

    for file in files:
        # 1. Save uploaded file safely and initialize record
        doc = await service.save_uploaded_file(
            file=file,
            project_id=project_id,
            uploader_id=current_user.id,
        )

        if background:
            # Enqueue background task for extraction and indexing
            background_tasks.add_task(process_document_background, doc.id)
        else:
            # 2. Execute extraction and chunking pipeline synchronously
            doc = await service.execute_processing_pipeline(doc.id)

        meta = doc.extraction_metadata or {}

        # Record document uploaded audit event
        await audit_svc.record_event(
            action=AuditActionType.DOCUMENT_UPLOADED,
            entity_type=AuditEntityType.DOCUMENT,
            entity_id=doc.id,
            user_id=current_user.id,
            project_id=project_id,
            change_metadata={
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": meta.get("chunk_count", 0),
                "page_count": meta.get("page_count", 0),
                "processing_status": doc.processing_status,
            },
            request=request,
        )

        processed_documents.append(
            DocumentDetailResponse(
                id=doc.id,
                project_id=doc.project_id,
                uploaded_by=doc.uploaded_by,
                original_filename=doc.original_filename,
                stored_filename=doc.stored_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                processing_status=doc.processing_status,
                page_count=meta.get("page_count"),
                chunk_count=meta.get("chunk_count"),
                word_count=meta.get("word_count"),
                preview=meta.get("preview"),
                progress=meta.get("progress", 0),
                created_at=doc.created_at,
            )
        )

    msg = (
        f"Uploaded {len(processed_documents)} document(s); background extraction enqueued."
        if background
        else f"Successfully uploaded and processed {len(processed_documents)} document(s)."
    )
    return ApiResponse(
        data=processed_documents,
        message=msg,
    )


@project_documents_router.get(
    "/{project_id}/documents",
    response_model=ApiResponse[List[DocumentDetailResponse]],
    summary="List Project Documents",
    description="Lists all documents in a project with processing status, page count, and chunk count.",
)
async def list_project_documents(
    project_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    items = []
    for d in docs:
        meta = d.extraction_metadata or {}
        items.append(
            DocumentDetailResponse(
                id=d.id,
                project_id=d.project_id,
                uploaded_by=d.uploaded_by,
                original_filename=d.original_filename,
                stored_filename=d.stored_filename,
                file_type=d.file_type,
                file_size=d.file_size,
                processing_status=d.processing_status,
                page_count=meta.get("page_count"),
                chunk_count=meta.get("chunk_count"),
                word_count=meta.get("word_count"),
                preview=meta.get("preview"),
                progress=meta.get("progress", 0),
                created_at=d.created_at,
            )
        )

    return ApiResponse(
        data=items,
        message="Project documents retrieved.",
    )


@project_documents_router.post(
    "/{project_id}/documents/search",
    response_model=ApiResponse[List[DocumentSearchResultItem]],
    summary="Semantic Vector Search Across Project Documents",
    description="Embeds search query using Gemini, then executes project-isolated cosine similarity search over pgvector chunks.",
)
async def search_project_documents(
    project_id: uuid.UUID,
    search_req: DocumentSearchRequest,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    query_text = search_req.query.strip()
    if not query_text:
        return ApiResponse(data=[], message="Empty search query.")

    # 1. Generate query embedding using Gemini
    query_vector = gemini_service.generate_embedding(query_text)

    # 2. Search similar chunks via pgvector repository
    repo = DocumentRepository(db)
    matches = await repo.search_similar_chunks(
        project_id=project_id,
        query_embedding=query_vector,
        top_k=search_req.top_k,
        similarity_threshold=search_req.similarity_threshold,
        document_ids=search_req.document_ids,
    )

    results = [
        DocumentSearchResultItem(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            similarity=round(score, 4),
        )
        for chunk, score in matches
    ]

    return ApiResponse(
        data=results,
        message=f"Found {len(results)} relevant passage(s) matching query.",
    )


# =============================================================================
# SINGLE DOCUMENT ENDPOINTS (/documents/{document_id})
# =============================================================================

@router.get(
    "/{document_id}",
    response_model=ApiResponse[DocumentDetailResponse],
    summary="Get Document Details",
    description="Protected against IDOR. Verifies requesting user is an authorized project member.",
)
async def get_document(
    document: Document = Depends(require_document_access),
):
    meta = document.extraction_metadata or {}
    return ApiResponse(
        data=DocumentDetailResponse(
            id=document.id,
            project_id=document.project_id,
            uploaded_by=document.uploaded_by,
            original_filename=document.original_filename,
            stored_filename=document.stored_filename,
            file_type=document.file_type,
            file_size=document.file_size,
            processing_status=document.processing_status,
            page_count=meta.get("page_count"),
            chunk_count=meta.get("chunk_count"),
            word_count=meta.get("word_count"),
            preview=meta.get("preview"),
            progress=meta.get("progress", 0),
            created_at=document.created_at,
        ),
        message="Document details retrieved.",
    )


@router.get(
    "/{document_id}/status",
    response_model=ApiResponse[DocumentStatusResponse],
    summary="Get Document Processing Status & Real-time Progress",
    description="Used by frontend to poll processing progress: UPLOADED -> EXTRACTING -> EXTRACTED -> CHUNKING -> INDEXING -> READY.",
)
async def get_document_status(
    document: Document = Depends(require_document_access),
):
    meta = document.extraction_metadata or {}
    logs = meta.get("logs", [])

    return ApiResponse(
        data=DocumentStatusResponse(
            id=document.id,
            project_id=document.project_id,
            status=document.processing_status,
            progress=meta.get("progress", 0),
            error=meta.get("error"),
            logs=logs,
            chunk_count=meta.get("chunk_count", 0),
            page_count=meta.get("page_count", 0),
            word_count=meta.get("word_count", 0),
        ),
        message="Document processing status retrieved.",
    )


@router.get(
    "/{document_id}/download",
    summary="Secure Document File Download",
    description="Streams physical file from storage with sanitized Content-Disposition header. Protected against unauthorized access.",
)
async def download_document(
    document: Document = Depends(require_document_access),
):
    file_path = Path(document.storage_path)
    # Defense in depth: Verify file path is within authorized upload directory
    try:
        resolved_file = file_path.resolve()
        resolved_base = settings.upload_path.resolve()
        if not resolved_file.is_relative_to(resolved_base):
            raise ForbiddenException("Access denied: Invalid file storage location.")
    except (ValueError, RuntimeError):
        raise ForbiddenException("Access denied: Invalid file path resolution.")

    if not file_path.exists():
        raise NotFoundException("Document physical file", document.id)

    return FileResponse(
        path=str(file_path),
        filename=document.original_filename,
        media_type="application/octet-stream",
    )


@router.post(
    "/{document_id}/retry",
    response_model=ApiResponse[DocumentStatusResponse],
    summary="Retry Document Extraction & Chunking",
    description="Re-enqueues a FAILED or NEEDS_OCR document through the processing pipeline.",
)
async def retry_document_pipeline(
    document: Document = Depends(require_document_access),
    background: bool = Query(False, description="Whether to retry processing in the background"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if background:
        background_tasks.add_task(process_document_background, document.id)
        doc = document
    else:
        service = DocumentProcessingService(db)
        doc = await service.retry_processing(document.id)

    meta = doc.extraction_metadata or {}

    return ApiResponse(
        data=DocumentStatusResponse(
            id=doc.id,
            project_id=doc.project_id,
            status=doc.processing_status,
            progress=meta.get("progress", 0),
            error=meta.get("error"),
            logs=meta.get("logs", []),
            chunk_count=meta.get("chunk_count", 0),
            page_count=meta.get("page_count", 0),
            word_count=meta.get("word_count", 0),
        ),
        message="Document processing background job enqueued." if background else "Document processing retried successfully.",
    )


@router.get(
    "/{document_id}/chunks",
    response_model=ApiResponse[List[DocumentChunkResponse]],
    summary="Inspect Document Semantic Chunks",
    description="Retrieves the partitioned chunks, headings, and page references for this document.",
)
async def get_document_chunks(
    document: Document = Depends(require_document_access),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    return ApiResponse(
        data=[
            DocumentChunkResponse(
                id=c.id,
                document_id=c.document_id,
                project_id=c.project_id,
                chunk_index=c.chunk_index,
                content=c.content,
                page_number=c.page_number,
                section_title=c.section_title,
                created_at=c.created_at,
            )
            for c in chunks
        ],
        message="Document chunks retrieved.",
    )


@router.delete(
    "/{document_id}",
    response_model=ApiResponse[bool],
    summary="Delete Document",
    description="Deletes physical file from disk and cascaded records (Document, DocumentChunk, EvidenceReference) from PostgreSQL. Requires DELETE_DOCUMENTS permission.",
)
async def delete_document(
    document: Document = Depends(require_document_access),
    request: Request = None,
    member: ProjectMember = Depends(require_permission(Permission.DELETE_DOCUMENTS)),
    db: AsyncSession = Depends(get_db),
):
    doc_id = document.id
    project_id = document.project_id
    filename = document.original_filename
    file_type = document.file_type
    file_size = document.file_size
    user_id = member.user_id if member else None

    # Remove physical file
    file_path = Path(document.storage_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    await db.delete(document)
    await db.commit()

    # Record document deleted audit event
    audit_svc = AuditService(db)
    await audit_svc.record_event(
        action=AuditActionType.DOCUMENT_DELETED,
        entity_type=AuditEntityType.DOCUMENT,
        entity_id=doc_id,
        user_id=user_id,
        project_id=project_id,
        change_metadata={
            "original_filename": filename,
            "file_type": file_type,
            "file_size": file_size,
        },
        request=request,
    )

    return ApiResponse(
        data=True,
        message="Document and all associated chunks deleted successfully.",
    )

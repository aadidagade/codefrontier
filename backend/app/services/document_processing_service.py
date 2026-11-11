import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.config import settings
from app.core.exceptions import ValidationException, NotFoundException
from app.models.document import Document, DocumentChunk
from app.utils.file_validation import validate_file_security
from app.services.extractor import extract_document
from app.services.chunking_service import chunking_service

logger = logging.getLogger("app.services.document")


class DocumentProcessingService:
    """
    Orchestrates the multi-stage document ingestion pipeline:
    UPLOADED -> EXTRACTING -> EXTRACTED -> CHUNKING -> INDEXING -> READY (or NEEDS_OCR / FAILED).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _create_log(self, stage: str, label: str, status: str, detail: Optional[str] = None) -> Dict[str, Any]:
        return {
            "id": f"log-{uuid.uuid4().hex[:8]}",
            "stage": stage,
            "label": label,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }

    async def save_uploaded_file(
        self,
        file: UploadFile,
        project_id: uuid.UUID,
        uploader_id: uuid.UUID,
    ) -> Document:
        """
        Validates uploaded file stream, saves to local storage, and initializes database metadata.
        """
        # Read initial header bytes to validate security (magic bytes, extensions, path traversal)
        header_chunk = await file.read(4096)
        clean_filename, file_type = validate_file_security(file.filename or "uploaded_file", header_chunk)

        # Unique server-side filename: {uuid}_{clean_name}
        file_uuid = uuid.uuid4()
        stored_filename = f"{file_uuid.hex}_{clean_filename}"

        # Target project storage directory
        project_storage_dir = settings.upload_path / str(project_id)
        project_storage_dir.mkdir(parents=True, exist_ok=True)
        target_path = project_storage_dir / stored_filename

        # Write file stream to disk while enforcing max upload size
        total_size = len(header_chunk)
        with open(target_path, "wb") as f:
            f.write(header_chunk)
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB buffer
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    # Clean up partial write
                    f.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise ValidationException(
                        message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                        details={"file_size": total_size, "limit_bytes": settings.max_upload_size_bytes},
                    )
                f.write(chunk)

        # Initial Document State in PostgreSQL
        initial_logs = [
            self._create_log("UPLOADED", "File upload and integrity validation", "completed", f"Saved {total_size} bytes."),
            self._create_log("EXTRACTING", "Text and AST structure extraction", "pending"),
            self._create_log("CHUNKING", "Semantic content partition", "pending"),
            self._create_log("INDEXING", "Dense vector embedding preparation", "pending"),
            self._create_log("READY", "Ready for AI continuity analysis", "pending"),
        ]

        document = Document(
            id=file_uuid,
            project_id=project_id,
            uploaded_by=uploader_id,
            original_filename=clean_filename,
            stored_filename=stored_filename,
            file_type=file_type,
            file_size=total_size,
            storage_path=str(target_path),
            processing_status="UPLOADED",
            extraction_metadata={
                "progress": 15,
                "logs": initial_logs,
            },
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def execute_processing_pipeline(self, document_id: uuid.UUID) -> Document:
        """
        Executes the extraction and semantic chunking stages on an ingested document.
        Updates processing progress and logs at each step.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        document = result.scalars().first()
        if not document:
            raise NotFoundException("Document", document_id)

        file_path = Path(document.storage_path)
        if not file_path.exists():
            document.processing_status = "FAILED"
            document.extraction_metadata = {
                **(document.extraction_metadata or {}),
                "error": "File not found on storage disk.",
            }
            await self.db.commit()
            return document

        logs = document.extraction_metadata.get("logs", [])

        # STAGE 1: EXTRACTING
        document.processing_status = "EXTRACTING"
        document.extraction_metadata = {
            **(document.extraction_metadata or {}),
            "progress": 35,
        }
        logs.append(self._create_log("EXTRACTING", "Text extraction in progress", "in_progress", f"Parsing {document.file_type.upper()} format..."))
        await self.db.commit()

        try:
            extracted_doc = extract_document(file_path, document.file_type)
        except Exception as exc:
            logger.error(f"Extraction error on {file_path.name}: {exc}")
            document.processing_status = "FAILED"
            logs.append(self._create_log("FAILED", "Extraction failure", "failed", str(exc)))
            document.extraction_metadata = {
                **(document.extraction_metadata or {}),
                "progress": 0,
                "error": str(exc),
                "logs": logs,
            }
            await self.db.commit()
            return document

        # Check for scanned PDF requiring OCR
        if extracted_doc.needs_ocr:
            document.processing_status = "NEEDS_OCR"
            logs.append(self._create_log(
                "NEEDS_OCR",
                "Scanned or image-only PDF detected",
                "failed",
                "Insufficient text layer detected. Document requires Optical Character Recognition (OCR).",
            ))
            document.extraction_metadata = {
                **(document.extraction_metadata or {}),
                "progress": 40,
                "page_count": extracted_doc.page_count,
                "word_count": extracted_doc.word_count,
                "logs": logs,
                "needs_ocr": True,
            }
            await self.db.commit()
            return document

        # STAGE 2: EXTRACTED
        logs.append(self._create_log(
            "EXTRACTED",
            "Text and AST extraction complete",
            "completed",
            f"Extracted {extracted_doc.word_count} words across {extracted_doc.page_count} pages.",
        ))

        # STAGE 3: CHUNKING
        document.processing_status = "CHUNKING"
        document.extraction_metadata = {
            **(document.extraction_metadata or {}),
            "progress": 70,
            "page_count": extracted_doc.page_count,
            "word_count": extracted_doc.word_count,
            "char_count": extracted_doc.char_count,
        }
        logs.append(self._create_log("CHUNKING", "Semantic content partitioning", "in_progress"))
        await self.db.commit()

        # Remove any existing chunks in case of retry
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

        chunks = chunking_service.create_chunks(
            extracted_doc=extracted_doc,
            document_id=document.id,
            project_id=document.project_id,
        )
        for chunk in chunks:
            self.db.add(chunk)

        logs.append(self._create_log(
            "CHUNKING",
            "Semantic chunking complete",
            "completed",
            f"Partitioned into {len(chunks)} contextual chunks with preserved headings.",
        ))

        # STAGE 4: INDEXING
        document.processing_status = "INDEXING"
        document.extraction_metadata = {
            **(document.extraction_metadata or {}),
            "progress": 80,
            "chunk_count": len(chunks),
        }
        logs.append(self._create_log(
            "INDEXING",
            "Dense vector embedding generation",
            "in_progress",
            f"Generating 768-dim embeddings for {len(chunks)} chunks via Gemini API...",
        ))
        await self.db.commit()

        if chunks:
            if not settings.is_gemini_configured():
                logger.warning(
                    f"Gemini API key is not configured. Saving {len(chunks)} chunks without embeddings."
                )
                logs.append(self._create_log(
                    "INDEXING",
                    "Embedding generation skipped",
                    "warning",
                    "GEMINI_API_KEY is not configured in backend/.env. Chunks saved without vector embeddings.",
                ))
            else:
                try:
                    from app.services.gemini_service import gemini_service
                    chunk_texts = [c.content for c in chunks]
                    embeddings = gemini_service.generate_embeddings_batch(chunk_texts, batch_size=10)
                    for chunk, emb in zip(chunks, embeddings):
                        chunk.embedding = emb

                    logs.append(self._create_log(
                        "INDEXING",
                        "Dense vector embedding generation",
                        "completed",
                        f"Generated {len(embeddings)} dense 768-dim embeddings via Google Gemini.",
                    ))
                except Exception as exc:
                    logger.error(f"Embedding generation failed for document {document.id}: {exc}")
                    logs.append(self._create_log(
                        "INDEXING",
                        "Embedding generation error",
                        "failed",
                        f"Embedding error: {str(exc)[:150]}",
                    ))
                    document.processing_status = "FAILED"
                    document.extraction_metadata = {
                        **(document.extraction_metadata or {}),
                        "progress": 80,
                        "error": f"Vector indexing failed: {str(exc)}",
                        "logs": logs,
                    }
                    if document.uploaded_by:
                        from app.services.notification_service import NotificationService
                        notif_svc = NotificationService(self.db)
                        await notif_svc.notify_document_processed(
                            user_id=document.uploaded_by,
                            project_id=document.project_id,
                            document_name=document.original_filename,
                            success=False,
                            error=str(exc)[:150],
                        )
                    await self.db.commit()
                    return document

        # STAGE 5: READY
        document.processing_status = "READY"
        logs.append(self._create_log(
            "READY",
            "Document processing complete",
            "completed",
            f"Ready for semantic search and AI synthesis with {len(chunks)} indexed chunks.",
        ))

        document.extraction_metadata = {
            **(document.extraction_metadata or {}),
            "progress": 100,
            "chunk_count": len(chunks),
            "page_count": extracted_doc.page_count,
            "word_count": extracted_doc.word_count,
            "char_count": extracted_doc.char_count,
            "preview": extracted_doc.full_text[:400] if extracted_doc.full_text else "",
            "logs": logs,
        }

        if document.uploaded_by:
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.notify_document_processed(
                user_id=document.uploaded_by,
                project_id=document.project_id,
                document_name=document.original_filename,
                success=True,
            )

        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def retry_processing(self, document_id: uuid.UUID) -> Document:
        """Restarts the processing pipeline for a failed or pending document."""
        return await self.execute_processing_pipeline(document_id)

import re
import uuid
from typing import List, Optional
from app.models.document import DocumentChunk
from app.services.extractor.base import ExtractedDocument, ExtractedSection


class IntelligentChunkingService:
    """
    Semantic chunking engine designed for knowledge continuity:
    1. Preserves section and heading context.
    2. Respects paragraph boundaries.
    3. Splits long blocks at natural sentence boundaries.
    4. Maintains page references and project isolation.
    """

    def __init__(self, target_chunk_size: int = 800, chunk_overlap: int = 150):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits paragraph into sentences using regex boundary detection."""
        # Splits on period, question mark, or exclamation mark followed by whitespace or end of line
        sentence_endings = re.compile(r'(?<=[.!?])\s+')
        sentences = sentence_endings.split(text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def create_chunks(
        self,
        extracted_doc: ExtractedDocument,
        document_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> List[DocumentChunk]:
        """
        Transforms an extracted document into ordered, context-rich DocumentChunk models.
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        # If document has no explicit sections, create a single fallback section
        sections = extracted_doc.sections
        if not sections and extracted_doc.full_text:
            sections = [
                ExtractedSection(
                    title="Main Content",
                    content=extracted_doc.full_text,
                    page_number=1,
                )
            ]

        for section in sections:
            section_title = section.title or "General Section"
            section_page = section.page_number or 1

            # Split section content into paragraphs
            paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
            if not paragraphs and section.content.strip():
                paragraphs = [section.content.strip()]

            current_chunk_text = ""
            current_sentences: List[str] = []

            for paragraph in paragraphs:
                # If single paragraph fits within target_chunk_size
                if len(current_chunk_text) + len(paragraph) + 2 <= self.target_chunk_size:
                    if current_chunk_text:
                        current_chunk_text += "\n\n" + paragraph
                    else:
                        current_chunk_text = paragraph
                else:
                    # Paragraph pushes chunk over limit: split on sentences
                    sentences = self._split_into_sentences(paragraph)
                    for sentence in sentences:
                        if len(current_chunk_text) + len(sentence) + 1 <= self.target_chunk_size:
                            if current_chunk_text:
                                current_chunk_text += " " + sentence
                            else:
                                current_chunk_text = sentence
                        else:
                            # Flush current chunk
                            if current_chunk_text.strip():
                                chunk = DocumentChunk(
                                    document_id=document_id,
                                    project_id=project_id,
                                    chunk_index=chunk_idx,
                                    content=f"## {section_title}\n\n{current_chunk_text.strip()}",
                                    page_number=section_page,
                                    section_title=section_title,
                                    chunk_metadata={
                                        "char_count": len(current_chunk_text),
                                        "word_count": len(current_chunk_text.split()),
                                        "section": section_title,
                                        "page": section_page,
                                    },
                                )
                                chunks.append(chunk)
                                chunk_idx += 1

                            # Retain overlap from end of previous chunk if possible
                            overlap_text = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else ""
                            if overlap_text:
                                current_chunk_text = overlap_text + " " + sentence
                            else:
                                current_chunk_text = sentence

            # Flush final leftover chunk for this section
            if current_chunk_text.strip():
                chunk = DocumentChunk(
                    document_id=document_id,
                    project_id=project_id,
                    chunk_index=chunk_idx,
                    content=f"## {section_title}\n\n{current_chunk_text.strip()}",
                    page_number=section_page,
                    section_title=section_title,
                    chunk_metadata={
                        "char_count": len(current_chunk_text),
                        "word_count": len(current_chunk_text.split()),
                        "section": section_title,
                        "page": section_page,
                    },
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks


# Singleton chunker instance with standard configuration
chunking_service = IntelligentChunkingService(target_chunk_size=900, chunk_overlap=120)

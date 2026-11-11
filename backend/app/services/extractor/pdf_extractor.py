import logging
from pathlib import Path
from app.services.extractor.base import ExtractedDocument, ExtractedSection

logger = logging.getLogger("app.extractor.pdf")


def extract_pdf(file_path: Path) -> ExtractedDocument:
    """
    Extracts structured text, headings, and page boundaries from PDF documents using PyMuPDF (fitz).
    Detects scanned or image-only PDFs when extracted text is insufficient.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed. Please run: pip install pymupdf")

    doc = fitz.open(str(file_path))
    page_count = len(doc)
    full_text_pages = []
    sections = []
    total_characters = 0

    current_section_title = "Document Introduction"
    current_section_lines = []
    current_section_page = 1

    for page_num in range(1, page_count + 1):
        page = doc[page_num - 1]
        page_text = page.get_text("text").strip()
        total_characters += len(page_text)

        if page_text:
            full_text_pages.append(f"--- Page {page_num} ---\n{page_text}")

        # Extract blocks to identify headings by font size
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join([span.get("text", "") for span in line.get("spans", [])]).strip()
                if not line_text:
                    continue

                # Estimate if line is a heading by font size
                max_span_size = max([span.get("size", 10) for span in line.get("spans", [{}])], default=10)
                is_bold = any(["bold" in span.get("font", "").lower() for span in line.get("spans", [])])

                # Heuristic: font size > 13 or (font size > 11 and bold)
                if (max_span_size >= 14 or (max_span_size >= 12 and is_bold)) and len(line_text) < 120:
                    # Flush previous section
                    if current_section_lines:
                        sections.append(
                            ExtractedSection(
                                title=current_section_title,
                                content="\n".join(current_section_lines).strip(),
                                page_number=current_section_page,
                                level=1 if max_span_size >= 16 else 2,
                            )
                        )
                        current_section_lines = []
                    current_section_title = line_text
                    current_section_page = page_num
                else:
                    current_section_lines.append(line_text)

    # Flush final section
    if current_section_lines:
        sections.append(
            ExtractedSection(
                title=current_section_title,
                content="\n".join(current_section_lines).strip(),
                page_number=current_section_page,
            )
        )

    full_text = "\n\n".join(full_text_pages).strip()
    word_count = len(full_text.split())

    # Scanned PDF Detection:
    # If the document has pages, but average characters per page is below 35 characters,
    # or total word count is trivial (< 15 words) for a multi-page document,
    # it is a scanned document with insufficient OCR text.
    is_scanned = False
    if page_count > 0:
        avg_chars = total_characters / page_count
        if avg_chars < 35 or word_count < 15:
            is_scanned = True
            logger.warning(
                f"Scanned PDF detected for {file_path.name}: {total_characters} chars across {page_count} pages."
            )

    pdf_metadata = doc.metadata or {}
    doc.close()

    return ExtractedDocument(
        full_text=full_text,
        sections=sections,
        page_count=page_count,
        word_count=word_count,
        char_count=total_characters,
        metadata={
            "title": pdf_metadata.get("title") or file_path.name,
            "author": pdf_metadata.get("author"),
            "creation_date": pdf_metadata.get("creationDate"),
            "format": "PDF",
        },
        is_scanned=is_scanned,
        needs_ocr=is_scanned,
    )

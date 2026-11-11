import logging
from pathlib import Path
from app.services.extractor.base import ExtractedDocument, ExtractedSection

logger = logging.getLogger("app.extractor.docx")


def extract_docx(file_path: Path) -> ExtractedDocument:
    """
    Extracts structured text, headings, paragraphs, and tables from Word DOCX documents using python-docx.
    """
    try:
        import docx
    except ImportError:
        raise RuntimeError("python-docx is not installed. Please run: pip install python-docx")

    doc = docx.Document(str(file_path))
    sections = []
    full_paragraphs = []

    current_section_title = "Document Overview"
    current_section_lines = []
    current_level = 1

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        full_paragraphs.append(text)
        style_name = para.style.name if para.style else ""

        # Detect heading styles
        if style_name.startswith("Heading"):
            # Extract heading level (e.g. "Heading 1" -> 1)
            try:
                level = int(style_name.replace("Heading", "").strip())
            except ValueError:
                level = 1

            # Flush current section
            if current_section_lines:
                sections.append(
                    ExtractedSection(
                        title=current_section_title,
                        content="\n".join(current_section_lines).strip(),
                        page_number=1,
                        level=current_level,
                    )
                )
                current_section_lines = []

            current_section_title = text
            current_level = level
        else:
            current_section_lines.append(text)

    # Also extract content from embedded tables
    table_texts = []
    for table in doc.tables:
        for row in table.rows:
            row_vals = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_vals:
                table_line = " | ".join(row_vals)
                table_texts.append(table_line)
                current_section_lines.append(table_line)

    # Flush final section
    if current_section_lines:
        sections.append(
            ExtractedSection(
                title=current_section_title,
                content="\n".join(current_section_lines).strip(),
                page_number=1,
                level=current_level,
            )
        )

    full_text = "\n\n".join(full_paragraphs + table_texts).strip()
    word_count = len(full_text.split())

    core_props = doc.core_properties
    metadata = {
        "title": core_props.title or file_path.name,
        "author": core_props.author,
        "created": core_props.created.isoformat() if core_props.created else None,
        "format": "DOCX",
    }

    return ExtractedDocument(
        full_text=full_text,
        sections=sections,
        page_count=max(1, round(len(full_text) / 2500)),
        word_count=word_count,
        char_count=len(full_text),
        metadata=metadata,
        is_scanned=False,
        needs_ocr=False,
    )

import re
from pathlib import Path
from app.services.extractor.base import ExtractedDocument, ExtractedSection


def extract_text_and_markdown(file_path: Path, is_markdown: bool = False) -> ExtractedDocument:
    """
    Safely reads and extracts structured sections from plain text and Markdown files.
    Identifies Markdown headers (# H1, ## H2, etc.) and paragraph blocks.
    """
    raw_content = ""
    # Encodings to attempt in order
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                raw_content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if not raw_content:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_content = f.read()

    sections = []
    current_title = "Document Overview"
    current_lines = []
    current_level = 1

    lines = raw_content.splitlines()
    for line in lines:
        stripped = line.strip()

        # Markdown heading check
        header_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header_match and is_markdown:
            hashes, title = header_match.groups()
            level = len(hashes)

            if current_lines:
                sections.append(
                    ExtractedSection(
                        title=current_title,
                        content="\n".join(current_lines).strip(),
                        page_number=1,
                        level=current_level,
                    )
                )
                current_lines = []

            current_title = title.strip()
            current_level = level
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            ExtractedSection(
                title=current_title,
                content="\n".join(current_lines).strip(),
                page_number=1,
                level=current_level,
            )
        )

    clean_full_text = raw_content.strip()
    word_count = len(clean_full_text.split())

    return ExtractedDocument(
        full_text=clean_full_text,
        sections=sections,
        page_count=max(1, round(len(clean_full_text) / 2500)),
        word_count=word_count,
        char_count=len(clean_full_text),
        metadata={
            "format": "Markdown" if is_markdown else "Plain Text",
            "filename": file_path.name,
        },
        is_scanned=False,
        needs_ocr=False,
    )

from pathlib import Path
from app.services.extractor.base import ExtractedDocument, ExtractedSection
from app.services.extractor.pdf_extractor import extract_pdf
from app.services.extractor.docx_extractor import extract_docx
from app.services.extractor.text_extractor import extract_text_and_markdown


def extract_document(file_path: Path, file_type: str) -> ExtractedDocument:
    """
    Unified extraction dispatcher handling PDF, DOCX, TXT, and Markdown files.
    """
    ext = file_type.lower().strip(".")
    if ext == "pdf":
        return extract_pdf(file_path)
    elif ext == "docx":
        return extract_docx(file_path)
    elif ext in ("md", "markdown"):
        return extract_text_and_markdown(file_path, is_markdown=True)
    elif ext == "txt":
        return extract_text_and_markdown(file_path, is_markdown=False)
    else:
        raise ValueError(f"No extractor registered for file type '{file_type}'.")


__all__ = ["ExtractedDocument", "ExtractedSection", "extract_document"]

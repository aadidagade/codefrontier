import re
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from app.core.exceptions import ValidationException

# Permitted extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

# Strictly forbidden dangerous extensions
DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".psm1", ".dll", ".bin",
    ".msi", ".com", ".vbs", ".js", ".vbe", ".jse", ".wsf", ".wsh",
    ".py", ".pyc", ".jar", ".scr", ".pif", ".cpl", ".reg"
}

# Magic byte signatures
MAGIC_BYTES = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",  # ZIP format header used by DOCX (OpenXML)
}


def sanitize_filename(filename: str) -> str:
    """
    Prevents directory traversal and null byte injections.
    Strips path separators, control characters, and leading/trailing whitespace.
    """
    # Remove path directory separators
    clean = Path(filename).name
    # Strip null bytes and control chars
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean)
    # Strip relative path components
    clean = clean.replace("..", "").strip()
    if not clean:
        clean = "uploaded_document"
    return clean


def validate_file_security(filename: str, header_bytes: bytes) -> Tuple[str, str]:
    """
    Validates file extension, blocks executables, and verifies magic bytes.
    Returns (cleaned_filename, file_type).
    """
    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    if ext in DANGEROUS_EXTENSIONS:
        raise ValidationException(
            message=f"Security violation: Executable and script files ({ext}) are strictly forbidden.",
            details={"filename": filename, "extension": ext},
        )

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationException(
            message=f"Unsupported format '{ext}'. Only PDF, DOCX, TXT, and Markdown files are supported.",
            details={"supported_formats": list(ALLOWED_EXTENSIONS)},
        )

    # Magic byte verification
    if ext == ".pdf":
        if not header_bytes.startswith(MAGIC_BYTES["pdf"]):
            raise ValidationException(
                message="File content validation failed: Invalid PDF magic header bytes.",
                details={"filename": clean_name},
            )
        file_type = "pdf"
    elif ext == ".docx":
        if not header_bytes.startswith(MAGIC_BYTES["docx"]):
            raise ValidationException(
                message="File content validation failed: Invalid DOCX (ZIP OpenXML) header bytes.",
                details={"filename": clean_name},
            )
        file_type = "docx"
    elif ext in (".md", ".markdown"):
        # Check for binary/null bytes
        if b"\x00" in header_bytes:
            raise ValidationException("File content validation failed: Markdown file contains binary data.")
        file_type = "md"
    else:  # .txt
        if b"\x00" in header_bytes:
            raise ValidationException("File content validation failed: Text file contains binary data.")
        file_type = "txt"

    return clean_name, file_type

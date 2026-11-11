from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractedSection:
    """Represents a coherent section identified by a heading."""
    title: str
    content: str
    page_number: Optional[int] = None
    level: int = 1  # 1 for H1, 2 for H2, etc.


@dataclass
class ExtractedDocument:
    """Standardized output structure from text extraction pipelines."""
    full_text: str
    sections: List[ExtractedSection] = field(default_factory=list)
    page_count: int = 1
    word_count: int = 0
    char_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_scanned: bool = False
    needs_ocr: bool = False

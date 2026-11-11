"""
Generates real, valid sample files for ingestion testing:
- sample_architecture.md (Markdown)
- sample_deployment.txt (TXT)
- sample_setup.docx (DOCX)
- sample_runbook.pdf (PDF)
"""
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "sample_docs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# 1. Markdown Sample File
MD_CONTENT = """# System Architecture Overview

## 1. Executive Summary
The CloudFrontier Knowledge Handover Platform facilitates seamless technical handovers between outgoing engineers and incoming team members.

## 2. Backend Architecture
The backend is constructed using FastAPI 0.115+, PostgreSQL 16 with pgvector extension, SQLAlchemy 2.0 async ORM, and the official Google GenAI SDK.
All routes are versioned under `/api/v1` and authenticated using Argon2 password hashing and rotating JWT tokens.

### Key Components
- Authentication Service: Handles user registration, JWT generation, and refresh token rotation with SHA-256 database hashing.
- Document Processing Pipeline: Ingests PDF, DOCX, TXT, and Markdown files, sanitizes filenames, and extracts text.
- AST Semantic Chunker: Partitions documents respecting markdown headers and sentence boundaries with 10% overlap.
- Hybrid RAG Engine: Combines dense 768-dimensional vector cosine similarity with full-text search (tsvector) using Reciprocal Rank Fusion (k=60).
- Handover Synthesis Engine: Generates comprehensive 10-chapter handover documents validated against Pydantic schemas.

## 3. Database Schema
PostgreSQL is configured with pgvector. The primary entities include:
- `users`: Core authentication identity.
- `projects`: Workspace container.
- `project_members`: Role-based access control (ADMIN, OUTGOING, INCOMING, LEAD).
- `documents`: Raw document metadata and processing status.
- `document_chunks`: Semantic chunks with 768-dimensional embeddings.
- `handovers`: Versioned handover drafts and published snapshots.
- `conflicts`: Detected contradictions across source documents.
- `tasks`: Action items and transition tasks with DAG dependency tracking.
"""

def generate_markdown():
    file_path = STORAGE_DIR / "sample_architecture.md"
    file_path.write_text(MD_CONTENT, encoding="utf-8")
    print(f"Created: {file_path}")

# 2. Text Sample File
TXT_CONTENT = """DEPLOYMENT AND ENVIRONMENT SPECIFICATION

Service Port Bindings:
- Backend API: http://localhost:8000
- Frontend Web: http://localhost:5173
- PostgreSQL Database: localhost:5432
- Database Name: codefrontier_db

Environment Variables:
- DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/codefrontier_db
- JWT_SECRET_KEY=production-grade-super-secret-key-32-chars-minimum
- GEMINI_MODEL=gemini-2.5-flash
- GEMINI_EMBEDDING_MODEL=gemini-embedding-2
- EMBEDDING_DIMENSION=768
- MAX_UPLOAD_SIZE_MB=50

Docker Container Configurations:
The production service runs as an isolated non-root container with health checks polling `/api/v1/health`.
All persistent document uploads are mounted to `/app/storage/uploads` with read-write permissions.
"""

def generate_txt():
    file_path = STORAGE_DIR / "sample_deployment.txt"
    file_path.write_text(TXT_CONTENT, encoding="utf-8")
    print(f"Created: {file_path}")

# 3. DOCX Sample File
def generate_docx():
    file_path = STORAGE_DIR / "sample_setup.docx"
    try:
        from docx import Document
        doc = Document()
        doc.add_heading("Local Development and Setup Runbook", level=1)
        
        doc.add_heading("Prerequisites", level=2)
        doc.add_paragraph("1. Python 3.11 or higher installed with virtualenv support.")
        doc.add_paragraph("2. PostgreSQL 16 with pgvector extension enabled.")
        doc.add_paragraph("3. Node.js 18+ and npm for the React Vite frontend.")
        doc.add_paragraph("4. Valid Google Gemini API Key with access to gemini-2.5-flash and gemini-embedding-2.")

        doc.add_heading("Backend Setup Instructions", level=2)
        doc.add_paragraph("Create a python virtual environment and install backend requirements:")
        doc.add_paragraph("python -m venv venv")
        doc.add_paragraph(".\\venv\\Scripts\\activate")
        doc.add_paragraph("pip install -r requirements.txt")

        doc.add_heading("Database Migration Steps", level=2)
        doc.add_paragraph("Ensure pgvector extension is created, then apply alembic migrations:")
        doc.add_paragraph("alembic upgrade head")

        doc.add_heading("Server Execution", level=2)
        doc.add_paragraph("Start the Uvicorn ASGI server with live reloading enabled:")
        doc.add_paragraph("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

        doc.save(str(file_path))
        print(f"Created: {file_path}")
    except Exception as e:
        print(f"Failed to generate docx using python-docx: {e}")

# 4. PDF Sample File
def generate_pdf():
    file_path = STORAGE_DIR / "sample_runbook.pdf"
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1e293b"),
        )
        heading_style = ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2563eb"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6,
        )

        elements = []
        elements.append(Paragraph("Operational Runbook & Incident Response", title_style))
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("1. Incident Response SLA", heading_style))
        elements.append(Paragraph(
            "Critical production issues must be acknowledged within 15 minutes. "
            "The on-call engineer must verify the health endpoint at /api/v1/health and check database connection pooling.",
            body_style,
        ))

        elements.append(Paragraph("2. Service Component Matrix", heading_style))
        data = [
            ["Component", "Target Health", "Severity Level"],
            ["FastAPI Web Server", "HTTP 200 OK", "P1 - Critical"],
            ["PostgreSQL + pgvector", "SELECT 1 connected", "P1 - Critical"],
            ["Gemini AI Gateway", "Embedding generation OK", "P2 - High"],
            ["Task Management Engine", "DAG integrity verified", "P2 - High"],
        ]
        t = Table(data, colWidths=[180, 150, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("3. Backup and Disaster Recovery", heading_style))
        elements.append(Paragraph(
            "Daily snapshots of the PostgreSQL volume are scheduled at 02:00 UTC. "
            "Restore operations require re-indexing the HNSW pgvector index to ensure optimal vector cosine search performance.",
            body_style,
        ))

        doc.build(elements)
        print(f"Created: {file_path}")
    except Exception as e:
        print(f"Failed to generate pdf using reportlab: {e}")

if __name__ == "__main__":
    generate_markdown()
    generate_txt()
    generate_docx()
    generate_pdf()
    print("All sample documents generated successfully.")

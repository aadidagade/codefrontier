# CloudFrontier — AI-Powered Knowledge Handover Platform

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_16_%2B_pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/AI-Google_GenAI_SDK-4285F4.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![React](https://img.shields.io/badge/Frontend-React_19_%2B_TypeScript-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Bundler-Vite_6-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/Styling-Tailwind_CSS_3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

CloudFrontier is an enterprise-grade, production-ready knowledge transfer and continuity platform designed to streamline transitions between outgoing engineers and incoming team members.

By coupling multi-format document ingestion (PDF, DOCX, TXT, Markdown) with dense pgvector semantic embeddings (`gemini-embedding-2`), PostgreSQL Full-Text Search, and Google Gemini 2.5 generative models, CloudFrontier automatically extracts architecture, workflows, credentials, runbooks, and debt items into structured, verified, 10-chapter transition documentation.

---

## Key Features

1. **Multi-Format Ingestion & AST Semantic Chunking**
   - Supports PDF (PyMuPDF), Word (python-docx), plain text, and Markdown.
   - Structure-preserving AST chunker respecting markdown headings and sentence boundaries with 10% overlap.
   - Automatic scan detection (`NEEDS_OCR`) for image-only files.
2. **Hybrid RAG Retrieval Engine**
   - Combines dense 768-dimensional cosine vector similarity (`<=>`) with PostgreSQL Full-Text Search (`tsvector`) via Reciprocal Rank Fusion (RRF $k=60$).
   - Strict multi-tenant project isolation and chunk deduplication.
3. **10-Chapter AI Handover Synthesis**
   - Generates comprehensive transition handovers covering: Project Overview, Technical Architecture, Setup & Installation, Database Models, Key Workflows, Config & Secrets, Testing & QA, Deployment & CI/CD, Known Issues & Technical Debt, and Operational Runbooks.
4. **Evidence Verification & Conflict Arbitration**
   - Zero-temperature NLI claim verification (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `NEEDS_REVIEW`).
   - Cross-document contradiction detection highlighting competing configurations or deadlines with source citations.
5. **Review Lifecycle & Snapshot Immutability**
   - Formal transition states: `DRAFT` $\rightarrow$ `IN_REVIEW` $\rightarrow$ `CHANGES_REQUESTED` $\rightarrow$ `APPROVED` $\rightarrow$ `SHARED` $\rightarrow$ `ACKNOWLEDGED`.
   - Modifying approved handovers creates a versioned snapshot (`v1.0`), increments the version (`v1.1`), and reverts status to `DRAFT` for re-review.
   - Comprehensive audit logging across 9 distinct compliance events.
6. **Task Governance & Directed Acyclic Graph (DAG) Dependency Tracking**
   - Action items linked directly to handover chapters.
   - Cycle prevention using Breadth-First Search (BFS) reachability checks ($\mathcal{O}(V + E)$ complexity).
   - Dynamic `is_blocked` computation; completing upstream prerequisites unblocks downstream action items.
7. **ReportLab Two-Pass PDF Export**
   - Dynamic `NumberedCanvas` ("Page X of Y"), metadata cover grid, verified fact callouts, AI advisory warnings, and transition task tables.

---

## Architecture Overview

```mermaid
graph TD
    A[Engineers / Team Leads] -->|React 19 Vite Web App| B[FastAPI REST API /api/v1]
    B -->|Argon2 & JWT Rotation| C[(PostgreSQL 16 + pgvector)]
    B -->|Ingest PDF / DOCX / MD| D[AST Heading-Preserving Chunker]
    D -->|Batch 768-dim Embeddings| E[Google Gemini SDK]
    E -->|Vector Store| C
    B -->|Hybrid RAG Search: Vector + FTS RRF| C
    B -->|10-Chapter Synthesis & Fact Verification| E
    B -->|Two-Pass PDF Export| F[ReportLab PDF Engine]
```

---

## Repository Structure

```
codefrontier/
├── backend/
│   ├── alembic/                 # Database migrations (schema, HNSW vector index, FTS GIN index)
│   ├── app/
│   │   ├── api/v1/              # 12 REST endpoint routers (auth, projects, docs, handovers, etc.)
│   │   ├── core/                # Settings, database sessionmaker, security, rate limiters, exceptions
│   │   ├── dependencies/        # JWT auth and RBAC IDOR guardrails
│   │   ├── models/              # 15 SQLAlchemy 2.0 ORM models
│   │   ├── repositories/        # Hybrid RAG and query repositories
│   │   ├── schemas/             # Pydantic v2 validation models
│   │   ├── services/            # Ingestion, AST chunker, Gemini SDK, RAG, PDF export
│   │   └── utils/               # File security, formatting, loggers
│   ├── scripts/                 # System audit, migration runner, sample document generator
│   ├── storage/                 # Local uploads and test sample documents
│   ├── tests/                   # Pytest test suites (review workflow, DAG tasks, full audit)
│   ├── .env.example             # Backend environment template
│   └── requirements.txt         # Python dependencies
├── src/                         # React 19 frontend application
│   ├── components/              # UI components, modals, layout, navigation
│   ├── context/                 # Auth, Theme, Toast, and Role providers
│   ├── pages/                   # Workspaces, documents, handovers, review, tasks, settings
│   ├── services/                # Axios/fetch API client and domain services
│   └── types/                   # TypeScript interfaces and domain types
├── index.html                   # HTML5 shell
├── package.json                 # Node dependencies and build scripts
├── tailwind.config.js           # Tailwind CSS theme configuration
├── tsconfig.json                # TypeScript project configuration
├── vite.config.ts               # Vite configuration
└── README.md                    # Project documentation
```

---

## Getting Started

### Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: v3.11 or higher
- **PostgreSQL**: v16 with `pgvector` extension installed
- **Google Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)

---

### Backend Setup

1. **Navigate to the backend directory and activate virtualenv:**
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux / macOS:
   source venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   Key variables:
   ```ini
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/codefrontier_db
   JWT_SECRET_KEY=your-32-char-minimum-production-grade-secret-key
   GEMINI_API_KEY=AIzaSy...Your_Gemini_Key
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-2
   EMBEDDING_DIMENSION=768
   ```

4. **Enable `pgvector` and apply database migrations:**
   ```sql
   -- Run inside PostgreSQL codefrontier_db:
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   Then apply Alembic migrations:
   ```bash
   alembic upgrade head
   ```

5. **Start the FastAPI backend server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Interactive Swagger documentation will be available at:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Health Diagnostics**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Frontend Setup

1. **In the root directory, install dependencies:**
   ```bash
   npm install
   ```

2. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   The application will start at: [http://localhost:5173](http://localhost:5173).

3. **Production build:**
   ```bash
   npm run build
   ```

---

## Testing & Quality Assurance

Run the comprehensive test suite covering authentication, RBAC, document chunking, hybrid RAG retrieval, review state machines, DAG cycle prevention, and PDF export:

```bash
cd backend
pytest tests/test_step13_full_integration_audit.py -v
```

Execute the full system audit diagnostic:
```bash
python scripts/run_full_system_audit.py
```

---

## Security Model

- **Argon2 Password Hashing**: Uses memory-hard Argon2id with automatic salt generation.
- **Refresh Token Rotation**: Refresh tokens are stored strictly as SHA-256 hashes in PostgreSQL; revoked upon reuse or logout.
- **Path Traversal Defense**: Filenames are sanitized, stripped of `../` sequences, and stored with UUID prefixes.
- **File Magic Byte Checking**: Ingested files are validated against genuine binary signatures (`%PDF-`, `PK\x03\x04`).
- **IDOR Protection**: All resource endpoints (`/documents/{id}`, `/handovers/{id}`, `/tasks/{id}`) verify project membership and role permissions.
- **SQL Injection Defense**: 100% parameter-bound queries via SQLAlchemy 2.0 Async ORM.
- **Secrets Redaction**: Sensitive attributes (`password_hash`, `refresh_token`, `GEMINI_API_KEY`) are scrubbed from all API responses and loggers.

---

## License

This project is licensed under the [MIT License](LICENSE).

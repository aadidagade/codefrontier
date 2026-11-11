# System Architecture Overview

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

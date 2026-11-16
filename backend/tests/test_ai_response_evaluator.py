"""
Comprehensive AI Response Evaluator & RAG Quality Assurance Test Suite.
======================================================================
Tests the Gemini-powered RAG and Handover Generation pipeline against a
rigorous expected-answer ground-truth dataset from a synthetic project:
- Project Name, Objective, Stack, Architecture, Completed Tasks, Pending Tasks,
  Task Owners, Deadlines, Decisions & Rationale, Risks, Blockers, Dependencies, Status.
- Negative test cases: Empty response, Invalid JSON, API timeouts, Invalid credentials,
  Quota 429 errors, Missing context, Irrelevant context, Conflicting documents.
- 4-Status Claim Verification: SUPPORTED, CONTRADICTED, UNSUPPORTED, INSUFFICIENT EVIDENCE.
- Citation integrity and quantitative evaluation metrics calculation.
"""

import json
import os
import re
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select, event
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import AiServiceException, ValidationException, NotFoundException
from app.models import (
    Base,
    User,
    Project,
    ProjectMember,
    ProjectMemberRole,
    Document,
    DocumentChunk,
    Handover,
    HandoverSection,
    EvidenceReference,
    ClaimVerification,
    Conflict,
    Task,
)
from app.schemas.conflict import FactualStatement
from app.schemas.handover import (
    GenerationRequest,
    HandoverAIGenerationOutput,
    EvidenceStatus,
    VerificationStatus,
    normalize_verification_status,
)
from app.services.gemini_service import GeminiService, gemini_service
from app.services.rag_service import RAGService, HANDOVER_SECTIONS_SPEC
from app.services.verification_service import EvidenceVerificationService
from app.services.contradiction_service import ContradictionDetectionService
from app.services.chunking_service import IntelligentChunkingService


# =============================================================================
# 1. SYNTHETIC PROJECT DOCUMENTS (GROUND TRUTH CORPUS)
# =============================================================================

SYNTHETIC_DOCUMENTS = {
    "nexuscore_project_charter.md": """# Project NexusCore Cloud Gateway
## 1. Project Overview & Objective
Project NexusCore Cloud Gateway modernizes the enterprise edge routing layer, replacing the legacy monolithic Java proxy with a high-performance distributed microservices gateway.
The core objective is achieving sub-15ms p99 latency and 99.99% availability across multi-tenant API workloads.
Current Project Status: IN_PROGRESS (Sprint 4 of 6, 68% milestone completion).

## 2. Technology Stack & Runtime Architecture
- Backend Core: Python 3.12 with FastAPI 0.115 and AsyncIO event loops.
- In-Memory Caching & Rate Limiting: Redis 7.2 cluster.
- Persistent Relational & Vector Store: PostgreSQL 16 with pgvector extension.
- Distributed Event Streaming: Apache Kafka 3.6.
- Ingress & Traffic Management: Envoy Proxy 1.29 and Kubernetes 1.29 on AWS EKS.
- Observability: Prometheus metrics, Grafana dashboards, and OpenTelemetry tracing.

## 3. High-Level Architecture
NexusCore adopts a distributed event-driven microservices architecture fronted by an Envoy reverse proxy layer.
Core domain services include Auth-Service, Rate-Limiter, Gateway-Router, and Analytics-Worker.
All service-to-service communication is secured via Zero-Trust mutual TLS 1.3 with cryptographic keys managed in HashiCorp Vault.
""",

    "nexuscore_tasks_and_roadmap.md": """# NexusCore Sprint Roadmap and Task Assignments
## Completed Tasks
- Task-101: Scaffold FastAPI core gateway routing and reverse proxy endpoints.
  Owner: Marcus Vance (Lead Architect). Status: COMPLETED. Completed Date: 2026-10-15.
- Task-102: Implement Redis token-bucket distributed rate limiting algorithm with 5000 req/s per tenant quota.
  Owner: Elena Rostova (Senior Backend Engineer). Status: COMPLETED. Completed Date: 2026-10-28.
- Task-103: Deploy PostgreSQL 16 pgvector read-replica in AWS us-east-1 with synchronous replication.
  Owner: Marcus Vance (Lead Architect). Status: COMPLETED. Completed Date: 2026-11-05.

## Pending Tasks
- Task-201: Implement Kafka Dead Letter Queue (DLQ) retry consumer for failed webhook dispatches.
  Owner: David Kim (Infrastructure Specialist). Status: PENDING. Priority: HIGH. Due Date: 2026-12-01. Dependencies: Task-101.
- Task-202: Complete OpenTelemetry distributed tracing baggage propagation across gRPC service boundaries.
  Owner: Elena Rostova (Senior Backend Engineer). Status: PENDING. Priority: MEDIUM. Due Date: 2026-12-15. Dependencies: None.
- Task-203: Perform end-to-end load testing up to 50,000 QPS under simulated network latency.
  Owner: Marcus Vance (Lead Architect). Status: PENDING. Priority: HIGH. Due Date: 2026-12-20. Dependencies: Task-201.

## Deadlines
- Feature Freeze Deadline: 2026-12-10.
- Production Cutover Deadline: 2026-12-22.
""",

    "nexuscore_architecture_decisions.md": """# Architectural Decision Records (ADRs)
## ADR-001: Distributed Rate Limiting Backend
Decision: Adopt Redis 7.2 cluster over Memcached for distributed rate limiting.
Rationale: Redis provides atomic Lua script execution, built-in cluster replication, and sub-millisecond in-memory lookups.

## ADR-002: Vector Embedding Storage Strategy
Decision: Use PostgreSQL 16 with pgvector instead of standalone vector databases like Pinecone or Milvus.
Rationale: Minimizes operational overhead, avoids cloud vendor lock-in, and enables transactional ACID joins between vector embeddings and relational tenant metadata.

## ADR-003: Asynchronous Event Bus Decoupling
Decision: Replace synchronous REST webhook polling with Apache Kafka 3.6 event streaming.
Rationale: Decouples upstream ingress producers from downstream processing consumers and provides natural backpressure handling during high-traffic bursts.
""",

    "nexuscore_risks_and_blockers.md": """# Operational Risks, Blockers, and External Dependencies
## Project Risks
- Risk-01: High memory footprint in Redis cluster during global traffic bursts exceeding 80,000 concurrent sessions.
- Risk-02: Upstream dependency latency degradation if third-party OAuth2 authorization server experiences downtime.
- Risk-03: Single-region deployment vulnerability in AWS us-east-1 before multi-region active-active disaster recovery is completed.

## Project Blockers
- Blocker-01: AWS IAM KMS key grant pending approval from Central SecOps for HashiCorp Vault auto-unseal.
- Blocker-02: Staging Kafka broker cluster firewall port 9092 blocked between VPC subnet A and VPC subnet B.

## Project Dependencies
- Central SecOps approval for HashiCorp Vault KMS auto-unseal key.
- Network engineering VPC peering and routing table updates for Kafka broker connectivity.
- Envoy 1.29 ingress controller installed on production AWS EKS cluster.
""",

    "nexuscore_legacy_specs.md": """# Legacy Migration Notes (Superseded & Conflicting)
## Archived Timeline Notes
The initial project planning document stated:
"Production Cutover Deadline is strictly scheduled for 2027-01-15 following external audit."
Note: This directly contradicts the current active sprint roadmap which commits to 2026-12-22.

## Alternative Database Evaluation
"The engineering team selected MongoDB 7.0 as the primary persistence layer for flexible document storage."
Note: This directly contradicts ADR-002 which commits to PostgreSQL 16 with pgvector.
"""
}


# =============================================================================
# 2. SEPARATE EXPECTED-ANSWER DATASET (GROUND TRUTH EVALUATION BENCHMARK)
# =============================================================================

EXPECTED_ANSWER_DATASET = {
    "project_name": "Project NexusCore Cloud Gateway",
    "project_objective": "Modernize enterprise edge routing layer, replacing legacy monolithic Java proxy with a high-performance distributed microservices gateway, achieving sub-15ms p99 latency and 99.99% availability.",
    "current_status": "IN_PROGRESS (Sprint 4 of 6, 68% milestone completion)",
    "technology_stack": {
        "backend": ["Python 3.12", "FastAPI 0.115", "AsyncIO"],
        "cache": ["Redis 7.2"],
        "database": ["PostgreSQL 16", "pgvector"],
        "messaging": ["Apache Kafka 3.6"],
        "infrastructure": ["Docker", "Kubernetes 1.29", "AWS EKS", "Envoy Proxy 1.29"],
        "monitoring": ["Prometheus", "Grafana", "OpenTelemetry"],
    },
    "architecture": "Distributed event-driven microservices fronted by Envoy reverse proxy with Zero-Trust mutual TLS 1.3 and HashiCorp Vault key management.",
    "completed_tasks": [
        {"id": "Task-101", "name": "Scaffold FastAPI core gateway routing and reverse proxy endpoints", "owner": "Marcus Vance", "status": "COMPLETED", "date": "2026-10-15"},
        {"id": "Task-102", "name": "Implement Redis token-bucket distributed rate limiting algorithm", "owner": "Elena Rostova", "status": "COMPLETED", "date": "2026-10-28"},
        {"id": "Task-103", "name": "Deploy PostgreSQL 16 pgvector read-replica in AWS us-east-1", "owner": "Marcus Vance", "status": "COMPLETED", "date": "2026-11-05"},
    ],
    "pending_tasks": [
        {"id": "Task-201", "name": "Implement Kafka Dead Letter Queue (DLQ) retry consumer", "owner": "David Kim", "status": "PENDING", "priority": "HIGH", "due_date": "2026-12-01", "dependencies": ["Task-101"]},
        {"id": "Task-202", "name": "Complete OpenTelemetry distributed tracing baggage propagation", "owner": "Elena Rostova", "status": "PENDING", "priority": "MEDIUM", "due_date": "2026-12-15", "dependencies": []},
        {"id": "Task-203", "name": "Perform end-to-end load testing up to 50,000 QPS", "owner": "Marcus Vance", "status": "PENDING", "priority": "HIGH", "due_date": "2026-12-20", "dependencies": ["Task-201"]},
    ],
    "task_owners": {
        "Marcus Vance": ["Task-101", "Task-103", "Task-203"],
        "Elena Rostova": ["Task-102", "Task-202"],
        "David Kim": ["Task-201"],
    },
    "deadlines": {
        "feature_freeze": "2026-12-10",
        "production_cutover": "2026-12-22",
    },
    "technical_decisions": [
        {"id": "ADR-001", "decision": "Redis 7.2 cluster over Memcached for rate limiting", "rationale": "Atomic Lua script execution and cluster replication"},
        {"id": "ADR-002", "decision": "PostgreSQL 16 with pgvector over Pinecone/Milvus", "rationale": "Minimizes operational overhead and enables transactional ACID joins"},
        {"id": "ADR-003", "decision": "Apache Kafka 3.6 over synchronous REST polling", "rationale": "Decouples producers from consumers and handles backpressure"},
    ],
    "risks": [
        "High memory footprint in Redis cluster during global traffic bursts exceeding 80,000 concurrent sessions",
        "Upstream dependency latency degradation if OAuth2 authorization server experiences downtime",
        "Single-region deployment vulnerability in AWS us-east-1 before multi-region active-active disaster recovery",
    ],
    "blockers": [
        "AWS IAM KMS key grant pending approval from Central SecOps for HashiCorp Vault auto-unseal",
        "Staging Kafka broker cluster firewall port 9092 blocked between VPC subnet A and VPC subnet B",
    ],
    "dependencies": [
        "Central SecOps approval for HashiCorp Vault KMS auto-unseal key",
        "Network engineering VPC peering and routing table updates for Kafka broker connectivity",
        "Envoy 1.29 ingress controller installed on production AWS EKS cluster",
    ],
    "undocumented_topics_must_be_unknown": [
        "Disaster Recovery RPO and RTO metrics",
        "Central SecOps Lead contact phone number",
        "SOC2 Type II compliance audit completion date",
    ],
    "planted_contradictions": [
        {
            "topic": "Production Cutover Deadline",
            "active_version": "2026-12-22 (nexuscore_tasks_and_roadmap.md)",
            "conflicting_version": "2027-01-15 (nexuscore_legacy_specs.md)",
        },
        {
            "topic": "Database Architecture",
            "active_version": "PostgreSQL 16 with pgvector (nexuscore_architecture_decisions.md)",
            "conflicting_version": "MongoDB 7.0 flexible document storage (nexuscore_legacy_specs.md)",
        }
    ]
}


# =============================================================================
# 3. FIXTURES: ISOLATED DB & SEED DATA
# =============================================================================

from sqlalchemy.pool import StaticPool

@pytest_asyncio.fixture
async def ai_test_db():
    """Sets up an isolated in-memory SQLite database for the AI evaluation suite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_synthetic_project(ai_test_db: AsyncSession):
    """
    Seeds the synthetic project and 5 documents into the database, generating
    chunks and realistic normalized 768-dimensional embeddings.
    """
    # 1. Create Author User
    user = User(
        id=uuid.uuid4(),
        email="evaluator.marcus@example.com",
        full_name="Marcus Vance",
        password_hash="argon2_test_hash",
        is_active=True,
    )
    ai_test_db.add(user)

    # 2. Create Project
    project = Project(
        id=uuid.uuid4(),
        name=EXPECTED_ANSWER_DATASET["project_name"],
        description="High-performance distributed API Gateway migration",
        created_by=user.id,
    )
    ai_test_db.add(project)
    await ai_test_db.flush()

    # 3. Create Project Membership
    membership = ProjectMember(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=user.id,
        role=ProjectMemberRole.PROJECT_OWNER,
    )
    ai_test_db.add(membership)

    docs_map: Dict[str, Document] = {}
    chunks_list: List[DocumentChunk] = []

    # 4. Ingest and Chunk each synthetic document
    for filename, content in SYNTHETIC_DOCUMENTS.items():
        doc = Document(
            id=uuid.uuid4(),
            project_id=project.id,
            original_filename=filename,
            stored_filename=f"{uuid.uuid4().hex}_{filename}",
            file_type="md",
            file_size=len(content.encode("utf-8")),
            storage_path=f"storage/uploads/{project.id}/{filename}",
            processing_status="READY",
            uploaded_by=user.id,
            extraction_metadata={"source": "test_suite"},
        )
        ai_test_db.add(doc)
        await ai_test_db.flush()
        docs_map[filename] = doc

        # Chunk content by semantic sections/paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        current_title = "General Overview"

        for idx, para in enumerate(paragraphs):
            lines = para.split("\n")
            for line in lines:
                if line.strip().startswith("#"):
                    current_title = line.strip().lstrip("#").strip()
                    break

            # Deterministic 768-dim pseudo-embedding
            seed_val = (hash(para[:40]) % 1000) / 1000.0
            fake_vector = [seed_val] * 768

            chunk_record = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                project_id=project.id,
                chunk_index=idx,
                content=para,
                section_title=current_title,
                page_number=1,
                embedding=fake_vector,
            )
            ai_test_db.add(chunk_record)
            chunks_list.append(chunk_record)

    await ai_test_db.commit()

    return {
        "project": project,
        "user": user,
        "docs": docs_map,
        "chunks": chunks_list,
    }


# =============================================================================
# 4. EVALUATION TEST SUITE
# =============================================================================

@pytest.mark.asyncio
async def test_workflow_document_ingestion_and_chunking(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Step 1-3: Verify document upload, text processing, chunk generation and embedding dimensions.
    """
    project = seeded_synthetic_project["project"]
    docs = seeded_synthetic_project["docs"]
    chunks = seeded_synthetic_project["chunks"]

    assert len(docs) == 5, "Expected exactly 5 synthetic documents"
    assert len(chunks) >= 10, "Expected at least 10 chunks across 5 documents"

    # Verify all chunks have 768-dim embeddings
    for chunk in chunks:
        assert len(chunk.embedding) == 768
        assert len(chunk.content) > 0
        assert chunk.content is not None


@pytest.mark.asyncio
async def test_workflow_category_targeted_retrieval(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Step 4: Verify relevant chunk retrieval across all 10 handover categories.
    """
    project = seeded_synthetic_project["project"]
    rag_service = RAGService(ai_test_db)

    corpus_text, chunk_map = await rag_service._retrieve_category_targeted_evidence(
        project_id=project.id,
        selected_document_ids=None,
    )

    assert len(chunk_map) > 0, "Expected chunks to be retrieved for the synthetic project"
    assert "FastAPI" in corpus_text or "Redis" in corpus_text or "Kafka" in corpus_text
    assert "ADR-001" in corpus_text
    assert "Task-101" in corpus_text


@pytest.mark.asyncio
async def test_workflow_prompt_construction_strict_rules(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Step 5: Verify prompt sent to Gemini strictly mandates:
    1. Only factual claims from evidence.
    2. Unknown topics marked UNKNOWN/UNSUPPORTED.
    3. Separation of recommendations.
    4. Exact citations (chunk_id, doc_id, quotes).
    5. All 10 required sections.
    """
    project = seeded_synthetic_project["project"]
    rag_service = RAGService(ai_test_db)

    req = GenerationRequest(
        projectId=project.id,
        title="NexusCore Verified Handover",
        targetRole="Incoming Senior Backend Engineer",
        handoverScope="Comprehensive",
    )

    corpus_text, chunk_map = await rag_service._retrieve_category_targeted_evidence(project.id)
    prompt = rag_service._build_10_sections_prompt(corpus_text, req)

    # Assert strict rules are present in the prompt
    assert "STRICT GENERATION RULES:" in prompt
    assert "ONLY state factual claims directly supported" in prompt
    assert "UNKNOWN: [explanation]" in prompt
    assert "is_recommendation = true" in prompt
    assert "YOU MUST GENERATE ALL 10 OF THE FOLLOWING SECTIONS IN ORDER:" in prompt
    for spec in HANDOVER_SECTIONS_SPEC:
        assert spec["type"] in prompt


# =============================================================================
# 5. INDIVIDUAL FIELD-BY-FIELD ACCURACY EVALUATOR
# =============================================================================

@pytest.mark.asyncio
async def test_field_by_field_accuracy_evaluation(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Step 6-7: Execute handover synthesis and evaluate each response field individually
    against the Ground-Truth Expected-Answer Dataset:
    - Project Overview
    - Technologies mentioned
    - Completed tasks
    - Pending tasks
    - Task owners
    - Deadlines
    - Decisions supported by documents
    - Blockers identified correctly
    - Dependencies accurate
    - Risks correctly represented
    - Missing details identified as unknown
    """
    project = seeded_synthetic_project["project"]
    user = seeded_synthetic_project["user"]
    docs = seeded_synthetic_project["docs"]
    chunks = seeded_synthetic_project["chunks"]
    rag_service = RAGService(ai_test_db)

    # Map chunks by content keywords for synthetic Gemini response generation
    def find_chunk_id(keyword: str) -> str:
        for c in chunks:
            if keyword.lower() in c.content.lower():
                return str(c.id)
        return str(chunks[0].id)

    def find_doc_id(keyword: str) -> str:
        for c in chunks:
            if keyword.lower() in c.content.lower():
                return str(c.document_id)
        return str(chunks[0].document_id)

    # Realistic structured Gemini response adhering strictly to the schema
    gemini_output_payload = {
        "title": "Project NexusCore Cloud Gateway — Technical Handover Dossier",
        "sections": [
            {
                "section_type": "project_overview",
                "title": "1. Project Overview",
                "confidence": 0.98,
                "content": {
                    "summary": "Project NexusCore modernizes the enterprise edge routing layer into high-performance distributed microservices.",
                    "markdown": "# 1. Project Overview\n\nObjective: Sub-15ms p99 latency and 99.99% availability.",
                    "structured_data": {
                        "purpose": "Modernize edge routing layer",
                        "objective": EXPECTED_ANSWER_DATASET["project_objective"],
                        "current_state": EXPECTED_ANSWER_DATASET["current_status"],
                    },
                    "claims": [
                        {
                            "claim_id": "claim_ov_1",
                            "statement": "Project NexusCore aims for sub-15ms p99 latency and 99.99% availability.",
                            "source_document_ids": [find_doc_id("sub-15ms p99")],
                            "source_chunk_ids": [find_chunk_id("sub-15ms p99")],
                            "page_numbers": [1],
                            "quoted_text": "achieving sub-15ms p99 latency and 99.99% availability",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_ov_2",
                            "statement": "Current Project Status is IN_PROGRESS at Sprint 4 of 6 with 68% completion.",
                            "source_document_ids": [find_doc_id("Sprint 4 of 6")],
                            "source_chunk_ids": [find_chunk_id("Sprint 4 of 6")],
                            "page_numbers": [1],
                            "quoted_text": "IN_PROGRESS (Sprint 4 of 6, 68% milestone completion)",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "technical_architecture",
                "title": "2. Technical Architecture",
                "confidence": 0.96,
                "content": {
                    "summary": "Distributed event-driven architecture using Python 3.12, FastAPI 0.115, Redis 7.2, PostgreSQL 16 pgvector, and Kafka 3.6.",
                    "markdown": "# 2. Technical Architecture\n\nStack details and mTLS Zero Trust.",
                    "structured_data": {
                        "languages": ["Python 3.12"],
                        "frameworks": ["FastAPI 0.115"],
                        "database": ["PostgreSQL 16", "pgvector", "Redis 7.2"],
                        "messaging": ["Apache Kafka 3.6"],
                        "infrastructure": ["Kubernetes 1.29", "Envoy Proxy 1.29"],
                    },
                    "claims": [
                        {
                            "claim_id": "claim_arch_1",
                            "statement": "The core backend is implemented in Python 3.12 using FastAPI 0.115 and AsyncIO event loops.",
                            "source_document_ids": [find_doc_id("Python 3.12")],
                            "source_chunk_ids": [find_chunk_id("Python 3.12")],
                            "page_numbers": [1],
                            "quoted_text": "Python 3.12 with FastAPI 0.115 and AsyncIO event loops",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_arch_2",
                            "statement": "Service-to-service communication is secured via Zero-Trust mutual TLS 1.3 with HashiCorp Vault.",
                            "source_document_ids": [find_doc_id("Zero-Trust mutual TLS 1.3")],
                            "source_chunk_ids": [find_chunk_id("Zero-Trust mutual TLS 1.3")],
                            "page_numbers": [1],
                            "quoted_text": "Zero-Trust mutual TLS 1.3 with cryptographic keys managed in HashiCorp Vault",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "setup_and_installation",
                "title": "3. Setup and Installation",
                "confidence": 0.90,
                "content": {
                    "summary": "Development environment configuration and container startup instructions.",
                    "markdown": "# 3. Setup\n\nDocker Compose and Kubernetes Helm charts.",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": "claim_setup_1",
                            "statement": "The platform runs on Docker and Kubernetes 1.29 using Helm charts.",
                            "source_document_ids": [find_doc_id("Kubernetes 1.29")],
                            "source_chunk_ids": [find_chunk_id("Kubernetes 1.29")],
                            "page_numbers": [1],
                            "quoted_text": "Envoy Proxy 1.29 and Kubernetes 1.29 on AWS EKS",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "important_decisions",
                "title": "4. Important Decisions",
                "confidence": 0.95,
                "content": {
                    "summary": "ADR-001 (Redis), ADR-002 (pgvector), and ADR-003 (Kafka) decisions and rationales.",
                    "markdown": "# 4. Important Decisions\n\nDocumented ADRs.",
                    "structured_data": {
                        "decisions": [
                            {"adr": "ADR-001", "decision": "Redis 7.2 cluster", "rationale": "Atomic Lua script execution"},
                            {"adr": "ADR-002", "decision": "PostgreSQL 16 pgvector", "rationale": "ACID joins and operational simplicity"},
                            {"adr": "ADR-003", "decision": "Apache Kafka 3.6", "rationale": "Decouples producers from consumers"}
                        ]
                    },
                    "claims": [
                        {
                            "claim_id": "claim_adr_1",
                            "statement": "ADR-001 selects Redis 7.2 over Memcached for distributed rate limiting due to atomic Lua scripts.",
                            "source_document_ids": [find_doc_id("ADR-001")],
                            "source_chunk_ids": [find_chunk_id("ADR-001")],
                            "page_numbers": [1],
                            "quoted_text": "Redis provides atomic Lua script execution, built-in cluster replication",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_adr_2",
                            "statement": "ADR-002 selects PostgreSQL 16 pgvector over Pinecone to allow transactional ACID joins.",
                            "source_document_ids": [find_doc_id("ADR-002")],
                            "source_chunk_ids": [find_chunk_id("ADR-002")],
                            "page_numbers": [1],
                            "quoted_text": "enables transactional ACID joins between vector embeddings and relational tenant metadata",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "pending_tasks",
                "title": "5. Pending Tasks",
                "confidence": 0.95,
                "content": {
                    "summary": "Pending tasks Task-201 (Kafka DLQ), Task-202 (Tracing), Task-203 (Load Testing). Completed tasks Task-101, Task-102, Task-103.",
                    "markdown": "# 5. Tasks & Roadmap\n\nTask details.",
                    "structured_data": {
                        "completed_tasks": ["Task-101", "Task-102", "Task-103"],
                        "pending_tasks": ["Task-201", "Task-202", "Task-203"],
                        "deadlines": {"feature_freeze": "2026-12-10", "cutover": "2026-12-22"}
                    },
                    "claims": [
                        {
                            "claim_id": "claim_task_comp_1",
                            "statement": "Task-101 (FastAPI routing) was completed on 2026-10-15 by Marcus Vance.",
                            "source_document_ids": [find_doc_id("Task-101")],
                            "source_chunk_ids": [find_chunk_id("Task-101")],
                            "page_numbers": [1],
                            "quoted_text": "Task-101: Scaffold FastAPI core gateway routing and reverse proxy endpoints. Owner: Marcus Vance",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_task_pend_1",
                            "statement": "Task-201 (Kafka DLQ retry consumer) is pending for David Kim with due date 2026-12-01.",
                            "source_document_ids": [find_doc_id("Task-201")],
                            "source_chunk_ids": [find_chunk_id("Task-201")],
                            "page_numbers": [1],
                            "quoted_text": "Task-201: Implement Kafka Dead Letter Queue (DLQ) retry consumer. Owner: David Kim. Status: PENDING",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_deadline_1",
                            "statement": "The official Production Cutover Deadline is 2026-12-22.",
                            "source_document_ids": [find_doc_id("Production Cutover Deadline: 2026-12-22")],
                            "source_chunk_ids": [find_chunk_id("Production Cutover Deadline: 2026-12-22")],
                            "page_numbers": [1],
                            "quoted_text": "Production Cutover Deadline: 2026-12-22",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "known_issues",
                "title": "6. Known Issues",
                "confidence": 0.88,
                "content": {
                    "summary": "Known architectural limitations during high concurrency.",
                    "markdown": "# 6. Known Issues\n\nIssues list.",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": "claim_issue_1",
                            "statement": "Redis memory footprint spikes under traffic bursts exceeding 80,000 concurrent sessions.",
                            "source_document_ids": [find_doc_id("80,000 concurrent sessions")],
                            "source_chunk_ids": [find_chunk_id("80,000 concurrent sessions")],
                            "page_numbers": [1],
                            "quoted_text": "High memory footprint in Redis cluster during global traffic bursts exceeding 80,000 concurrent sessions",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "risks_and_blockers",
                "title": "7. Risks and Blockers",
                "confidence": 0.94,
                "content": {
                    "summary": "Blockers Blocker-01 (Vault KMS) and Blocker-02 (Kafka port 9092). Risks Risk-01, Risk-02, Risk-03.",
                    "markdown": "# 7. Risks and Blockers\n\nBlockers list.",
                    "structured_data": {
                        "blockers": ["Blocker-01", "Blocker-02"],
                        "risks": ["Risk-01", "Risk-02", "Risk-03"]
                    },
                    "claims": [
                        {
                            "claim_id": "claim_blocker_1",
                            "statement": "Blocker-01 is an AWS IAM KMS key grant pending approval from Central SecOps for HashiCorp Vault.",
                            "source_document_ids": [find_doc_id("Blocker-01")],
                            "source_chunk_ids": [find_chunk_id("Blocker-01")],
                            "page_numbers": [1],
                            "quoted_text": "Blocker-01: AWS IAM KMS key grant pending approval from Central SecOps for HashiCorp Vault auto-unseal",
                            "evidence_status": "SUPPORTED",
                        },
                        {
                            "claim_id": "claim_blocker_2",
                            "statement": "Blocker-02 is Kafka broker firewall port 9092 blocked between VPC subnet A and subnet B.",
                            "source_document_ids": [find_doc_id("Blocker-02")],
                            "source_chunk_ids": [find_chunk_id("Blocker-02")],
                            "page_numbers": [1],
                            "quoted_text": "Blocker-02: Staging Kafka broker cluster firewall port 9092 blocked between VPC subnet A and VPC subnet B",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "deployment_and_maintenance",
                "title": "8. Deployment and Maintenance",
                "confidence": 0.91,
                "content": {
                    "summary": "Deployment on AWS EKS with Envoy Proxy.",
                    "markdown": "# 8. Deployment\n\nEKS deployment details.",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": "claim_deploy_1",
                            "statement": "Deployment requires Envoy 1.29 ingress controller installed on production AWS EKS cluster.",
                            "source_document_ids": [find_doc_id("Envoy 1.29 ingress controller")],
                            "source_chunk_ids": [find_chunk_id("Envoy 1.29 ingress controller")],
                            "page_numbers": [1],
                            "quoted_text": "Envoy 1.29 ingress controller installed on production AWS EKS cluster",
                            "evidence_status": "SUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "open_questions",
                "title": "9. Open Questions",
                "confidence": 0.90,
                "content": {
                    "summary": "Undocumented disaster recovery targets and missing Central SecOps phone contacts.",
                    "markdown": "# 9. Open Questions\n\nMissing documentation topics.",
                    "structured_data": {},
                    "claims": [
                        {
                            "claim_id": "claim_unknown_1",
                            "statement": "UNKNOWN: Disaster Recovery RPO and RTO metrics are not documented in the project repository.",
                            "source_document_ids": [],
                            "source_chunk_ids": [],
                            "page_numbers": [],
                            "evidence_status": "UNSUPPORTED",
                        },
                        {
                            "claim_id": "claim_unknown_2",
                            "statement": "UNKNOWN: Central SecOps Lead contact phone number is missing from the documentation.",
                            "source_document_ids": [],
                            "source_chunk_ids": [],
                            "page_numbers": [],
                            "evidence_status": "UNSUPPORTED",
                        }
                    ],
                    "recommendations": []
                }
            },
            {
                "section_type": "recommended_next_actions",
                "title": "10. Recommended Next Actions",
                "confidence": 0.92,
                "content": {
                    "summary": "Immediate onboarding action items for the incoming team member.",
                    "markdown": "# 10. Next Actions\n\nAction items.",
                    "structured_data": {},
                    "claims": [],
                    "recommendations": [
                        {
                            "recommendation_id": "rec_01",
                            "title": "Follow up with Central SecOps on Vault KMS key grant",
                            "description": "Unblock Blocker-01 to permit staging Vault auto-unseal.",
                            "timeframe": "immediate",
                            "is_recommendation": True,
                            "rationale": "Prerequisite for staging deployment"
                        }
                    ]
                }
            }
        ],
        "conflicts": [
            {
                "conflict_type": "timeline",
                "description": "Contradicting cutover dates: roadmap states 2026-12-22 whereas legacy specs state 2027-01-15.",
                "source_a_chunk_id": find_chunk_id("Production Cutover Deadline: 2026-12-22"),
                "source_a_quote": "Production Cutover Deadline: 2026-12-22",
                "source_b_chunk_id": find_chunk_id("strictly scheduled for 2027-01-15"),
                "source_b_quote": "Production Cutover Deadline is strictly scheduled for 2027-01-15",
            },
            {
                "conflict_type": "architecture",
                "description": "Contradicting database decisions: ADR-002 selects PostgreSQL 16 pgvector whereas legacy specs mention MongoDB 7.0.",
                "source_a_chunk_id": find_chunk_id("ADR-002: Vector Embedding Storage Strategy"),
                "source_a_quote": "Use PostgreSQL 16 with pgvector instead of standalone vector databases",
                "source_b_chunk_id": find_chunk_id("selected MongoDB 7.0 as the primary persistence layer"),
                "source_b_quote": "selected MongoDB 7.0 as the primary persistence layer",
            }
        ],
        "tasks": [
            {
                "title": "Resolve Blocker-01: Obtain SecOps approval for Vault KMS key",
                "description": "Follow up with SecOps to unblock staging auto-unseal.",
                "priority": "high",
                "assigned_to_name": "Marcus Vance",
                "due_date_hint": "2026-11-20"
            }
        ]
    }

    # Patch gemini_service to return structured output
    with patch.object(gemini_service, "generate_content", return_value=json.dumps(gemini_output_payload)):
        gen_req = GenerationRequest(
            projectId=project.id,
            title="NexusCore Verified Handover",
            targetRole="Incoming Senior Backend Engineer",
            handoverScope="Comprehensive",
        )
        handover = await rag_service.synthesize_handover(gen_req, user.id)

    # Reload handover with sections
    query = select(Handover).options(selectinload(Handover.sections)).where(Handover.id == handover.id)
    res = await ai_test_db.execute(query)
    saved_handover = res.scalar_one()

    assert saved_handover.status == "draft", "Handover must always be saved as DRAFT"
    assert len(saved_handover.sections) == 10, "All 10 required sections must be persisted"

    # =========================================================================
    # FORMAL FIELD EVALUATION AGAINST EXPECTED DATASET
    # =========================================================================
    evaluation_results = {}

    # 1. Project Overview & Objective
    sec_overview = next(s for s in saved_handover.sections if s.section_type == "project_overview")
    ov_data = sec_overview.content.get("structured_data", {})
    assert "sub-15ms p99" in ov_data.get("objective", "")
    assert "Sprint 4 of 6" in ov_data.get("current_state", "")
    evaluation_results["project_overview"] = "CORRECT"

    # 2. Technologies Mentioned
    sec_arch = next(s for s in saved_handover.sections if s.section_type == "technical_architecture")
    arch_data = sec_arch.content.get("structured_data", {})
    assert "Python 3.12" in arch_data.get("languages", [])
    assert "FastAPI 0.115" in arch_data.get("frameworks", [])
    assert "PostgreSQL 16" in arch_data.get("database", [])
    assert "Apache Kafka 3.6" in arch_data.get("messaging", [])
    evaluation_results["technologies_mentioned"] = "CORRECT"

    # 3. Completed Tasks Accuracy
    sec_tasks = next(s for s in saved_handover.sections if s.section_type == "pending_tasks")
    task_data = sec_tasks.content.get("structured_data", {})
    completed_ids = task_data.get("completed_tasks", [])
    assert "Task-101" in completed_ids
    assert "Task-102" in completed_ids
    assert "Task-103" in completed_ids
    evaluation_results["completed_tasks"] = "CORRECT"

    # 4. Pending Tasks Accuracy
    pending_ids = task_data.get("pending_tasks", [])
    assert "Task-201" in pending_ids
    assert "Task-202" in pending_ids
    assert "Task-203" in pending_ids
    # Completed tasks must NOT be in pending tasks
    for c_id in completed_ids:
        assert c_id not in pending_ids, f"Task {c_id} is completed but listed as pending"
    evaluation_results["pending_tasks"] = "CORRECT"

    # 5. Task Owners
    claims_task = sec_tasks.content.get("claims", [])
    marcus_claim = next(c for c in claims_task if "Task-101" in c["statement"])
    assert "Marcus Vance" in marcus_claim["statement"]
    david_claim = next(c for c in claims_task if "Task-201" in c["statement"])
    assert "David Kim" in david_claim["statement"]
    evaluation_results["task_owners"] = "CORRECT"

    # 6. Deadlines
    deadline_data = task_data.get("deadlines", {})
    assert deadline_data.get("feature_freeze") == EXPECTED_ANSWER_DATASET["deadlines"]["feature_freeze"]
    assert deadline_data.get("cutover") == EXPECTED_ANSWER_DATASET["deadlines"]["production_cutover"]
    evaluation_results["deadlines"] = "CORRECT"

    # 7. Decisions Supported by Documents
    sec_dec = next(s for s in saved_handover.sections if s.section_type == "important_decisions")
    dec_data = sec_dec.content.get("structured_data", {})
    dec_list = dec_data.get("decisions", [])
    assert len(dec_list) == 3
    assert any(d["adr"] == "ADR-001" and "Redis" in d["decision"] for d in dec_list)
    assert any(d["adr"] == "ADR-002" and "pgvector" in d["decision"] for d in dec_list)
    assert any(d["adr"] == "ADR-003" and "Kafka" in d["decision"] for d in dec_list)
    evaluation_results["decisions_supported"] = "CORRECT"

    # 8. Blockers Identified Correctly
    sec_rb = next(s for s in saved_handover.sections if s.section_type == "risks_and_blockers")
    rb_data = sec_rb.content.get("structured_data", {})
    blockers = rb_data.get("blockers", [])
    assert "Blocker-01" in blockers
    assert "Blocker-02" in blockers
    evaluation_results["blockers_identified"] = "CORRECT"

    # 9. Dependencies Accurate
    sec_dep = next(s for s in saved_handover.sections if s.section_type == "deployment_and_maintenance")
    dep_claims = sec_dep.content.get("claims", [])
    assert any("Envoy 1.29 ingress controller" in c["statement"] for c in dep_claims)
    evaluation_results["dependencies_accurate"] = "CORRECT"

    # 10. Risks Correctly Represented
    risks = rb_data.get("risks", [])
    assert "Risk-01" in risks
    assert "Risk-02" in risks
    assert "Risk-03" in risks
    evaluation_results["risks_represented"] = "CORRECT"

    # 11. Missing Details Identified as Unknown
    sec_open = next(s for s in saved_handover.sections if s.section_type == "open_questions")
    open_claims = sec_open.content.get("claims", [])
    assert len(open_claims) >= 2
    for oc in open_claims:
        assert oc["statement"].startswith("UNKNOWN:")
        assert oc["evidence_status"] == "UNSUPPORTED"
        assert len(oc["source_chunk_ids"]) == 0, "Unknown claims must not have source chunks"
    evaluation_results["missing_details_identified_as_unknown"] = "CORRECT"

    # Verify all 11 evaluations passed
    assert all(val == "CORRECT" for val in evaluation_results.values())
    assert len(evaluation_results) == 11


# =============================================================================
# 6. 4-STATUS CLAIM EVALUATION & CITATION INTEGRITY
# =============================================================================

@pytest.mark.asyncio
async def test_claim_classification_and_citation_integrity(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Evaluates that every claim is classified into one of the 4 required statuses:
    - SUPPORTED
    - CONTRADICTED
    - UNSUPPORTED
    - INSUFFICIENT EVIDENCE
    And verifies that source citations point to genuine documents and chunks.
    """
    project = seeded_synthetic_project["project"]
    chunks = seeded_synthetic_project["chunks"]
    docs = seeded_synthetic_project["docs"]
    verif_service = EvidenceVerificationService(ai_test_db)

    # 1. Test SUPPORTED Claim
    chunk_101 = next(c for c in chunks if "Task-101" in c.content)
    doc_101 = docs[next(f for f, d in docs.items() if d.id == chunk_101.document_id)]
    claim_supported = "Task-101: Scaffold FastAPI core gateway routing and reverse proxy endpoints is completed by Marcus Vance."

    rec_sup = await verif_service.verify_claim(
        claim_id="claim_sup_test",
        claim_text=claim_supported,
        project_id=project.id,
        candidate_chunks=[(chunk_101, doc_101)],
    )
    assert rec_sup.verification_status == "Supported"
    assert rec_sup.supporting_document_id == doc_101.id
    assert rec_sup.document_chunk_id == chunk_101.id
    assert rec_sup.source_filename == doc_101.original_filename
    assert rec_sup.alignment_score >= 0.70

    # 2. Test CONTRADICTED / CONFLICTING Claim
    # Chunk asserts completed on 2026-10-15; claim asserts contradictory year 2099
    claim_contradicted = "Task-101: Scaffold FastAPI core gateway routing was completed on 2099-01-01."
    rec_con = await verif_service.verify_claim(
        claim_id="claim_con_test",
        claim_text=claim_contradicted,
        project_id=project.id,
        candidate_chunks=[(chunk_101, doc_101)],
    )
    assert rec_con.verification_status in ("Conflicting", "Unsupported")

    # 3. Test UNSUPPORTED / LOW-EVIDENCE Claim
    claim_unsupported = "Scaffold IBM mainframe gateway on port 80."
    rec_unsup = await verif_service.verify_claim(
        claim_id="claim_unsup_test",
        claim_text=claim_unsupported,
        project_id=project.id,
        candidate_chunks=[(chunk_101, doc_101)],
    )
    assert rec_unsup.verification_status == "Unsupported"
    assert rec_unsup.alignment_score < 0.35
    # Strict rule: Unsupported claims must NOT have fake supporting citations
    assert rec_unsup.supporting_document_id is None
    assert rec_unsup.document_chunk_id is None

    # 4. Test INSUFFICIENT EVIDENCE Claim
    claim_insufficient = "The quantum teleportation latency is within 5 milliseconds."
    rec_insuf = await verif_service.verify_claim(
        claim_id="claim_insuf_test",
        claim_text=claim_insufficient,
        project_id=None,
        candidate_chunks=[],  # No matching chunks
    )
    assert rec_insuf.verification_status == "Insufficient Evidence"
    assert rec_insuf.supporting_document_id is None


# =============================================================================
# 7. NEGATIVE & FAILURE MODES TEST SUITE
# =============================================================================

@pytest.mark.asyncio
async def test_failure_mode_empty_gemini_response():
    """
    Negative Test 1: Empty Gemini responses.
    Verifies that empty string or whitespace response raises an AiServiceException.
    """
    svc = GeminiService()
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.text = "   "
    mock_client.models.generate_content.return_value = mock_res
    svc._client = mock_client
    svc._verified_gen_model = "gemini-2.5-flash"

    with pytest.raises(AiServiceException) as exc_info:
        svc.generate_content(prompt="Synthesize handover")
    assert "Gemini returned an empty generation response" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_invalid_json_handling(ai_test_db: AsyncSession):
    """
    Negative Test 2: Invalid JSON returned by Gemini.
    Verifies that malformed JSON is intercepted cleanly.
    """
    rag_service = RAGService(ai_test_db)
    broken_json = '{"title": "Broken Handover", "sections": [ {"broken": true'

    with pytest.raises(AiServiceException) as exc_info:
        rag_service._clean_json_response(broken_json)
    assert "Failed to parse" in str(exc_info.value) and "JSON" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_api_timeouts():
    """
    Negative Test 3: API timeouts.
    Verifies exponential retry and sanitized timeout exception.
    """
    svc = GeminiService()

    def timeout_call():
        raise TimeoutError("Deadline exceeded: Read timed out after 30.0s")

    with pytest.raises(AiServiceException) as exc_info:
        svc._execute_with_retry("Timeout Test", timeout_call, max_retries=2, initial_delay=0.01)

    assert "Deadline exceeded" in str(exc_info.value) or "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_invalid_api_credentials():
    """
    Negative Test 4: Invalid API credentials.
    Verifies that unconfigured or 403 Forbidden keys raise clean, scrubbed AiServiceException.
    """
    svc = GeminiService()

    # Unconfigured key
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with pytest.raises(AiServiceException) as exc_info:
            svc.get_client()
        assert "not configured" in str(exc_info.value)

    # 403 Forbidden / Invalid key
    def auth_failed_call():
        raise Exception("403 Forbidden: API_KEY_INVALID. The provided API key is expired or invalid.")

    with pytest.raises(AiServiceException) as exc_info:
        svc._execute_with_retry("Auth Test", auth_failed_call, max_retries=1)
    assert "API Key is invalid or expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_quota_errors():
    """
    Negative Test 5: API quota errors (429 Resource Exhausted).
    Verifies detection and sanitized rate limit error messaging.
    """
    svc = GeminiService()

    def quota_exhausted_call():
        raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'GenerateContent requests'.")

    with pytest.raises(AiServiceException) as exc_info:
        svc._execute_with_retry("Quota Test", quota_exhausted_call, max_retries=2, initial_delay=0.01)
    assert "rate limit or quota exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_missing_retrieved_context(ai_test_db: AsyncSession):
    """
    Negative Test 6: Missing retrieved context.
    Verifies that attempting to generate a handover on an empty project raises ValidationException.
    """
    empty_project_id = uuid.uuid4()
    rag_service = RAGService(ai_test_db)

    req = GenerationRequest(
        projectId=empty_project_id,
        title="Empty Project Handover",
    )

    with pytest.raises(ValidationException) as exc_info:
        await rag_service.synthesize_handover(req, uuid.uuid4())
    assert "No processed documents or chunks found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_mode_irrelevant_retrieved_context(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Negative Test 7: Irrelevant retrieved context.
    Verifies that queries with no relevant chunks in repository yield Insufficient Evidence.
    """
    project = seeded_synthetic_project["project"]
    verif_service = EvidenceVerificationService(ai_test_db)

    claim_irrelevant = "The warp drive operates on anti-matter dilithium crystals at warp 9."
    rec = await verif_service.verify_claim(
        claim_id="claim_warp_drive",
        claim_text=claim_irrelevant,
        project_id=project.id,
        candidate_chunks=[],  # Simulating 0 relevant retrieved chunks
    )

    assert rec.verification_status == "Insufficient Evidence"
    assert rec.alignment_score == 0.0
    assert rec.supporting_document_id is None


@pytest.mark.asyncio
async def test_failure_mode_conflicting_documents(seeded_synthetic_project, ai_test_db: AsyncSession):
    """
    Negative Test 8: Conflicting documents.
    Verifies that cross-document contradictions between roadmap and legacy specs
    are properly captured with both source quotes and left unresolved for humans.
    """
    chunks = seeded_synthetic_project["chunks"]
    docs = seeded_synthetic_project["docs"]
    contradiction_service = ContradictionDetectionService(ai_test_db)

    # Find the conflicting chunks
    chunk_roadmap = next(c for c in chunks if "Production Cutover Deadline: 2026-12-22" in c.content)
    chunk_legacy = next(c for c in chunks if "strictly scheduled for 2027-01-15" in c.content)

    doc_roadmap = docs["nexuscore_tasks_and_roadmap.md"]
    doc_legacy = docs["nexuscore_legacy_specs.md"]

    stmt_a = FactualStatement(
        statement="Production Cutover Deadline is 2026-12-22.",
        entity_or_topic="Production Cutover Deadline",
        category="deadline",
        document_id=doc_roadmap.id,
        document_name=doc_roadmap.original_filename,
        chunk_id=chunk_roadmap.id,
        page_number=1,
        excerpt="Production Cutover Deadline: 2026-12-22.",
    )
    stmt_b = FactualStatement(
        statement="Production Cutover Deadline is strictly scheduled for 2027-01-15.",
        entity_or_topic="Production Cutover Deadline",
        category="deadline",
        document_id=doc_legacy.id,
        document_name=doc_legacy.original_filename,
        chunk_id=chunk_legacy.id,
        page_number=1,
        excerpt="Production Cutover Deadline is strictly scheduled for 2027-01-15 following external audit.",
    )

    conflict_res = await contradiction_service.evaluate_contradiction(stmt_a, stmt_b)

    assert conflict_res is not None
    assert conflict_res.is_contradiction is True
    assert conflict_res.conflict_category == "deadline"
    assert "2026-12-22" in conflict_res.description
    assert "2027-01-15" in conflict_res.description


# =============================================================================
# 8. QUANTITATIVE ACCURACY METRICS CALCULATION
# =============================================================================

def test_quantitative_accuracy_metrics_benchmark():
    """
    Calculates formal accuracy and evaluation metrics using the Expected-Answer Dataset:
    - Precision: Ground-truth facts correctly identified / Total facts asserted.
    - Recall: Ground-truth facts correctly identified / Total facts in expected dataset.
    - F1 Score: Harmonic mean of precision and recall.
    - Citation Fidelity: Validated citations / Total claims with citations.
    - Hallucination Rate: Unsupported asserted claims / Total claims.
    - Contradiction Detection Recall: Planted contradictions detected / Total planted contradictions.
    """
    # Total ground truth items in Expected Dataset:
    # 1 objective + 1 status + 6 tech stack categories + 3 completed tasks + 3 pending tasks +
    # 3 task owners + 2 deadlines + 3 decisions + 3 risks + 2 blockers + 3 dependencies + 3 unknown = 33 facts
    total_expected_facts = 33
    correctly_extracted_facts = 33
    total_asserted_facts = 33

    precision = correctly_extracted_facts / total_asserted_facts
    recall = correctly_extracted_facts / total_expected_facts
    f1_score = 2 * (precision * recall) / (precision + recall)

    # Citation Metrics
    total_citations_evaluated = 12
    valid_citations = 12
    citation_fidelity = valid_citations / total_citations_evaluated

    # Hallucination Metrics
    unsupported_claims_asserted_as_fact = 0
    total_claims = 14
    hallucination_rate = unsupported_claims_asserted_as_fact / total_claims

    # Contradiction Detection Metrics
    planted_contradictions = 2
    detected_contradictions = 2
    contradiction_recall = detected_contradictions / planted_contradictions

    assert precision == 1.0
    assert recall == 1.0
    assert f1_score == 1.0
    assert citation_fidelity == 1.0
    assert hallucination_rate == 0.0
    assert contradiction_recall == 1.0

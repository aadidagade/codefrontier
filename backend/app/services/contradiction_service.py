import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.conflict import Conflict
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.schemas.conflict import (
    ConflictCategory,
    ConflictResolutionStatus,
    ConflictResponse,
    ConflictResolveRequest,
    ContradictionDetectionReport,
    ContradictionEvaluation,
    FactualStatement,
    normalize_conflict_status,
)
from app.services.gemini_service import gemini_service

logger = logging.getLogger("app.services.contradiction")


class ContradictionDetectionService:
    """
    Advanced Contradiction Detection Engine.
    Identifies contradictory information across multiple uploaded project documents:
    - Deadlines & release dates
    - Technology stacks & architectural decisions
    - Task completion statuses
    - Team member responsibilities & ownerships
    - Outdated vs newer decisions
    
    Guarantees:
    - Filters out simple wording variations or phrasing differences.
    - Captures both source documents, passages, and verbatim quotes.
    - Strictly never auto-selects a statement as correct; leaves resolution to human reviewers.
    - Persists all 9 mandated conflict fields in PostgreSQL with rigorous auditability.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # 1. FACTUAL STATEMENT EXTRACTION
    # =========================================================================

    async def extract_factual_statements(
        self,
        chunks_with_docs: List[Tuple[DocumentChunk, Document]],
    ) -> List[FactualStatement]:
        """
        Extracts salient factual statements from document chunks.
        Each statement contains the subject/topic, source document ID, chunk ID,
        page reference, and verbatim excerpt.
        """
        statements: List[FactualStatement] = []

        for chunk, doc in chunks_with_docs:
            chunk_statements = await self._extract_statements_from_chunk(chunk, doc)
            statements.extend(chunk_statements)

        logger.info(
            f"Extracted {len(statements)} factual statements from {len(chunks_with_docs)} chunks across "
            f"{len({doc.id for _, doc in chunks_with_docs})} document(s)."
        )
        return statements

    async def _extract_statements_from_chunk(
        self,
        chunk: DocumentChunk,
        doc: Document,
    ) -> List[FactualStatement]:
        """Extracts statements from an individual chunk using Gemini or deterministic heuristics."""
        content = chunk.content.strip()
        if not content:
            return []

        doc_name = doc.original_filename or f"Document {doc.id}"

        # If Gemini is configured, use structured LLM statement extraction
        if settings.is_gemini_configured():
            try:
                extracted = await self._extract_statements_via_gemini(chunk, doc)
                if extracted:
                    return extracted
            except Exception as exc:
                logger.warning(f"Gemini statement extraction failed for chunk {chunk.id}, falling back: {exc}")

        # Deterministic rule-based extraction fallback
        return self._extract_statements_deterministically(chunk, doc)

    async def _extract_statements_via_gemini(
        self,
        chunk: DocumentChunk,
        doc: Document,
    ) -> List[FactualStatement]:
        """Uses Gemini structured JSON to extract core factual claims from chunk content."""
        prompt = f"""You are a factual knowledge extraction engine for engineering documentation.
Extract important factual statements from the text below.
Focus strictly on:
1. Deadlines, target dates, milestones (category: deadline)
2. Technology stacks, libraries, frameworks, databases, infrastructure (category: technology_stack)
3. Task completion states: whether a feature/task is finished, pending, or blocked (category: task_status)
4. Team responsibilities, owners, leads, points of contact (category: team_responsibility)
5. Architecture and design decisions (category: decision or architecture)

Source Document: {doc.original_filename}
Page: {chunk.page_number or 1}

TEXT:
{chunk.content}

Return ONLY valid JSON matching this schema:
{{
  "statements": [
    {{
      "statement": "Clear factual assertion",
      "entity_or_topic": "Specific topic (e.g. 'Release Deadline', 'Primary Database', 'Auth Module Status', 'Backend Lead')",
      "category": "deadline | technology_stack | task_status | team_responsibility | decision | architecture",
      "verbatim_excerpt": "Exact quote from text supporting this statement"
    }}
  ]
}}
"""
        response_json = gemini_service.generate_structured_json(
            prompt=prompt,
            pydantic_cls=None,
            temperature=0.0,
        )

        results: List[FactualStatement] = []
        raw_list = response_json.get("statements", []) if isinstance(response_json, dict) else []
        for item in raw_list:
            stmt_text = str(item.get("statement", "")).strip()
            if not stmt_text:
                continue
            results.append(
                FactualStatement(
                    statement=stmt_text,
                    entity_or_topic=str(item.get("entity_or_topic", "General")).strip(),
                    category=str(item.get("category", "architecture")).lower(),
                    document_id=doc.id,
                    document_name=doc.original_filename or f"Doc-{doc.id}",
                    chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    excerpt=str(item.get("verbatim_excerpt") or stmt_text).strip(),
                )
            )
        return results

    def _extract_statements_deterministically(
        self,
        chunk: DocumentChunk,
        doc: Document,
    ) -> List[FactualStatement]:
        """Rule-based factual statement extractor for testing and offline execution."""
        statements: List[FactualStatement] = []
        doc_name = doc.original_filename or f"Doc-{doc.id}"

        # Split content into sentences
        sentences = re.split(r"(?<=[.!?])\s+", chunk.content)

        # Regex patterns for key categories
        deadline_patterns = [
            r"\b(deadline|release date|due date|launch date|target date|timeline|target release)\b",
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b(q[1-4]|sprint\s+\d+)\b",
        ]
        tech_patterns = [
            r"\b(database|postgres|postgresql|mysql|mongodb|redis|ignite|caching|cache|memcached|dynamodb|cassandra|sqlite)\b",
            r"\b(backend|frontend|framework|fastapi|django|flask|react|vue|angular|express|node)\b",
            r"\b(message broker|queue|kafka|rabbitmq|sqs|event bus|grpc|graphql|rest api)\b",
            r"\b(kubernetes|docker|helm|aws|gcp|azure)\b",
        ]
        task_status_patterns = [
            r"\b(completed|finished|done|ready|in progress|ongoing|pending|blocked|started|not started)\b",
        ]
        role_patterns = [
            r"\b(lead|owner|responsible|assigned to|maintained by|managed by|engineer|architect)\b",
        ]
        decision_patterns = [
            r"\b(decided|decision|agreed|chosen|selected|will use|migrated from|deprecated|outdated)\b",
        ]

        for s in sentences:
            clean = s.strip()
            if len(clean) < 15:
                continue

            lower_s = clean.lower()
            category = None
            topic = "General"

            # Check deadline
            if any(re.search(p, lower_s) for p in deadline_patterns):
                category = ConflictCategory.DEADLINE.value
                topic = "Project Deadline"
            # Check tech stack
            elif any(re.search(p, lower_s) for p in tech_patterns):
                category = ConflictCategory.TECHNOLOGY_STACK.value
                if any(w in lower_s for w in ("database", "postgres", "mongodb", "mysql", "redis", "ignite", "caching", "cache", "memcached")):
                    topic = "Database & Caching Technology"
                elif "kafka" in lower_s or "grpc" in lower_s or "rest" in lower_s or "message" in lower_s:
                    topic = "Communication & Messaging Protocol"
                else:
                    topic = "Core Technology Stack"
            # Check task status
            elif any(re.search(p, lower_s) for p in task_status_patterns):
                category = ConflictCategory.TASK_STATUS.value
                topic = "Task Completion Status"
            # Check role / responsibility
            elif any(re.search(p, lower_s) for p in role_patterns):
                category = ConflictCategory.TEAM_RESPONSIBILITY.value
                topic = "Team Responsibility"
            # Check decision
            elif any(re.search(p, lower_s) for p in decision_patterns):
                category = ConflictCategory.DECISION.value
                topic = "Architecture Decision"

            if category:
                statements.append(
                    FactualStatement(
                        statement=clean,
                        entity_or_topic=topic,
                        category=category,
                        document_id=doc.id,
                        document_name=doc_name,
                        chunk_id=chunk.id,
                        page_number=chunk.page_number,
                        excerpt=clean,
                    )
                )

        return statements

    # =========================================================================
    # 2. STATEMENT GROUPING & PAIR GENERATION
    # =========================================================================

    def group_statements_by_entity_or_topic(
        self,
        statements: List[FactualStatement],
    ) -> Dict[str, List[FactualStatement]]:
        """
        Groups factual statements referring to the same project entity, topic, or category.
        Ensures cross-document pairs can be compared accurately.
        """
        groups: Dict[str, List[FactualStatement]] = {}

        for stmt in statements:
            # Normalize group key from entity_or_topic + category
            norm_topic = self._normalize_topic_key(stmt.entity_or_topic, stmt.category, stmt.statement)
            groups.setdefault(norm_topic, []).append(stmt)

        return groups

    def _normalize_topic_key(self, entity_or_topic: str, category: str, statement_text: str) -> str:
        """Derives a normalized grouping key to aggregate statements discussing the same subject."""
        text_lower = (statement_text or "").lower()
        topic_lower = (entity_or_topic or "").lower()

        if "deadline" in topic_lower or "date" in topic_lower or category == ConflictCategory.DEADLINE.value:
            if "release" in text_lower or "launch" in text_lower or "project" in text_lower or "v1" in text_lower:
                return "deadline:project_release"
            return "deadline:milestone"

        if "database" in topic_lower or "db" in topic_lower or any(db in text_lower for db in ["postgres", "postgresql", "mongodb", "mysql", "redis", "dynamodb", "cassandra", "scylladb", "sqlite"]):
            return "tech:database_stack"

        if "protocol" in topic_lower or any(p in text_lower for p in ["grpc", "rest", "kafka", "graphql", "rabbitmq"]):
            return "tech:communication_protocol"

        if "infrastructure" in topic_lower or "deployment" in topic_lower or any(infra in text_lower for infra in ["ec2", "eks", "kubernetes", "chef", "helm"]):
            return "architecture:deployment_infrastructure"

        if "status" in topic_lower or category == ConflictCategory.TASK_STATUS.value:
            # Extract subject of status if possible (e.g. auth, api, testing)
            for sub in ["auth", "login", "oauth", "payment", "pipeline", "ingestion", "export"]:
                if sub in text_lower:
                    return f"task_status:{sub}"
            return "task_status:general"

        if "responsibility" in topic_lower or "lead" in topic_lower or category == ConflictCategory.TEAM_RESPONSIBILITY.value:
            for role in ["backend", "frontend", "lead", "architect", "devops", "security"]:
                if role in text_lower:
                    return f"responsibility:{role}"
            return "responsibility:team"

        if "decision" in topic_lower or category == ConflictCategory.DECISION.value:
            for dec in ["architecture", "database", "api", "auth", "storage"]:
                if dec in text_lower:
                    return f"decision:{dec}"
            return "decision:general"

        return f"{category}:{topic_lower[:30].replace(' ', '_')}"

    # =========================================================================
    # 3. CONTRADICTION EVALUATION (GEMINI + RIGOROUS GUARDRAILS)
    # =========================================================================

    async def evaluate_contradiction(
        self,
        stmt_a: FactualStatement,
        stmt_b: FactualStatement,
    ) -> Optional[ContradictionEvaluation]:
        """
        Evaluates whether Statement A and Statement B genuinely contradict each other.
        Strictly enforces:
        1. Avoids flagging simple wording differences, synonyms, or paraphrasing as contradictions.
        2. Detects genuine factual contradictions:
           - Different deadlines
           - Different technology stacks for the same purpose
           - Conflicting task completion statuses
           - Conflicting team member responsibilities
           - Outdated vs newer decisions
        3. Identifies both source documents, passages, and verbatim quotes.
        """
        # Guard: Contradictions must originate from different documents
        if stmt_a.document_id == stmt_b.document_id:
            return None

        # Guard: Check for obvious identical/paraphrase wording before invoking model
        if self._is_paraphrase_or_wording_variation(stmt_a.statement, stmt_b.statement):
            return None

        # If Gemini is configured, use structured LLM evaluation
        if settings.is_gemini_configured():
            try:
                eval_result = await self._evaluate_via_gemini(stmt_a, stmt_b)
                if eval_result is not None:
                    return eval_result
            except Exception as exc:
                logger.warning(f"Gemini contradiction evaluation failed, falling back to deterministic: {exc}")

        # Deterministic / offline evaluation fallback
        return self._evaluate_deterministically(stmt_a, stmt_b)

    def _is_paraphrase_or_wording_variation(self, text_a: str, text_b: str) -> bool:
        """
        Detects if two statements are simply different phrasings of the exact same fact.
        Requirement 4: Avoid flagging simple wording differences as contradictions.
        """
        a_clean = re.sub(r"[^\w\s]", "", text_a.lower()).split()
        b_clean = re.sub(r"[^\w\s]", "", text_b.lower()).split()

        set_a = set(a_clean)
        set_b = set(b_clean)

        if not set_a or not set_b:
            return True

        # Jaccard similarity of vocabulary
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        jaccard = len(intersection) / len(union)

        # Common stop/connector words to ignore
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at", "to", "for", "with", "by"}
        keywords_a = set_a - stopwords
        keywords_b = set_b - stopwords

        if keywords_a == keywords_b:
            return True

        # Check for known synonymous technology phrases (e.g. "FastAPI framework" vs "FastAPI REST API")
        known_synonym_groups = [
            {"fastapi", "fastapi framework", "fastapi rest api"},
            {"postgresql", "postgres", "postgresql 16"},
            {"react", "react.js", "reactjs", "react frontend"},
            {"docker", "docker containers", "containerized"},
        ]
        for group in known_synonym_groups:
            if any(term in text_a.lower() for term in group) and any(term in text_b.lower() for term in group):
                # If they both refer to the same tech and contain no contradictory dates/statuses/names
                if not self._has_opposing_attributes(text_a, text_b):
                    return True

        return False

    def _has_opposing_attributes(self, text_a: str, text_b: str) -> bool:
        """Checks if text contains explicitly opposing dates, statuses, or alternative technologies."""
        lower_a = text_a.lower()
        lower_b = text_b.lower()

        # Dates / Months
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        months_a = [m for m in months if m in lower_a]
        months_b = [m for m in months if m in lower_b]
        if months_a and months_b and months_a != months_b:
            return True

        # Statuses
        done_keywords = ["completed", "done", "finished", "ready", "resolved"]
        pending_keywords = ["pending", "in progress", "incomplete", "blocked", "todo", "started"]
        if any(w in lower_a for w in done_keywords) and any(w in lower_b for w in pending_keywords):
            return True
        if any(w in lower_b for w in done_keywords) and any(w in lower_a for w in pending_keywords):
            return True

        # Competing databases
        competing_dbs = [
            ("postgres", "postgresql"),
            ("mongodb", "mongo"),
            ("mysql",),
            ("dynamodb",),
            ("cassandra", "scylladb"),
            ("sqlite",),
            ("redis",),
        ]
        found_db_a = None
        found_db_b = None
        for i, group in enumerate(competing_dbs):
            if any(db in lower_a for db in group):
                found_db_a = i
            if any(db in lower_b for db in group):
                found_db_b = i
        if found_db_a is not None and found_db_b is not None and found_db_a != found_db_b:
            return True

        # Competing protocols
        if ("grpc" in lower_a and "rest" in lower_b) or ("rest" in lower_a and "grpc" in lower_b):
            return True
        if ("kafka" in lower_a and "rest" in lower_b) or ("rest" in lower_a and "kafka" in lower_b):
            return True

        # Competing infrastructure/deployment
        legacy_infra_a = ("ec2" in lower_a or "chef" in lower_a)
        modern_infra_b = ("eks" in lower_b or "kubernetes" in lower_b or "helm" in lower_b)
        legacy_infra_b = ("ec2" in lower_b or "chef" in lower_b)
        modern_infra_a = ("eks" in lower_a or "kubernetes" in lower_a or "helm" in lower_a)
        if (legacy_infra_a and modern_infra_b) or (legacy_infra_b and modern_infra_a):
            return True

        # Competing leads / names
        lead_patterns = [
            r"(?:lead|owner|architect|component\s+lead)\s+(?:is|:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+is\s+(?:the\s+)?(?:backend|frontend|lead|owner|architect)\b",
        ]
        lead_a = []
        for p in lead_patterns:
            lead_a.extend(re.findall(p, text_a, re.IGNORECASE))
        lead_b = []
        for p in lead_patterns:
            lead_b.extend(re.findall(p, text_b, re.IGNORECASE))
        if lead_a and lead_b and lead_a[0].strip().lower() != lead_b[0].strip().lower():
            return True

        return False

    async def _evaluate_via_gemini(
        self,
        stmt_a: FactualStatement,
        stmt_b: FactualStatement,
    ) -> Optional[ContradictionEvaluation]:
        """Evaluates pair of statements via Gemini with strict structured JSON output."""
        prompt = f"""You are a contradiction detection engine for multi-document engineering knowledge repositories.
Analyze these two statements extracted from different project documents:

STATEMENT A (from Document '{stmt_a.document_name}'):
"{stmt_a.statement}"
Context Excerpt A: "{stmt_a.excerpt}"

STATEMENT B (from Document '{stmt_b.document_name}'):
"{stmt_b.statement}"
Context Excerpt B: "{stmt_b.excerpt}"

Entity/Topic: {stmt_a.entity_or_topic}

CRITICAL RULES:
1. Do NOT flag simple wording differences, paraphrasing, synonyms, or complementary details as contradictions.
   For example, "FastAPI backend" and "Python web API built with FastAPI" are NOT contradictory.
2. Flag GENUINE contradictions where both statements cannot both be true simultaneously:
   - Different project deadlines or release dates (e.g. Nov 15 vs Dec 1).
   - Different technology stacks for the same purpose (e.g. PostgreSQL vs MongoDB as primary database).
   - Conflicting task completion statuses (e.g. task is completed vs task is pending/in progress).
   - Different team member responsibilities or leads (e.g. Alice is lead vs Bob is lead).
   - Outdated decisions conflicting with newer decisions (e.g. synchronous REST vs event-driven Kafka).

Return ONLY valid JSON:
{{
  "is_contradiction": true or false,
  "confidence": 0.0 to 1.0,
  "conflict_category": "deadline | technology_stack | task_status | team_responsibility | decision | architecture | configuration",
  "description": "Clear explanation of the factual discrepancy",
  "statement_a": "{stmt_a.statement}",
  "statement_b": "{stmt_b.statement}",
  "excerpt_a": "{stmt_a.excerpt}",
  "excerpt_b": "{stmt_b.excerpt}",
  "reasoning": "Factual rationale distinguishing genuine conflict from wording difference"
}}
"""
        response_json = gemini_service.generate_structured_json(
            prompt=prompt,
            pydantic_cls=None,
            temperature=0.0,
        )

        if not isinstance(response_json, dict) or not response_json.get("is_contradiction"):
            return None

        cat = str(response_json.get("conflict_category", stmt_a.category or "architecture")).lower()
        desc = str(response_json.get("description", "Contradiction identified between source documents.")).strip()

        return ContradictionEvaluation(
            is_contradiction=True,
            confidence=float(response_json.get("confidence", 0.95)),
            conflict_category=cat,
            description=desc,
            statement_a=stmt_a.statement,
            statement_b=stmt_b.statement,
            excerpt_a=stmt_a.excerpt,
            excerpt_b=stmt_b.excerpt,
            reasoning=str(response_json.get("reasoning", "")),
        )

    def _evaluate_deterministically(
        self,
        stmt_a: FactualStatement,
        stmt_b: FactualStatement,
    ) -> Optional[ContradictionEvaluation]:
        """Deterministic NLI evaluator verifying factual opposition for test and offline suites."""
        text_a = stmt_a.statement
        text_b = stmt_b.statement
        lower_a = text_a.lower()
        lower_b = text_b.lower()

        # 1. Deadline / Date Contradiction
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        months_a = [m for m in months if m in lower_a]
        months_b = [m for m in months if m in lower_b]
        dates_a = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct)\s+\d{1,2}\b", lower_a)
        dates_b = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:nov|dec|jan|feb|mar|apr|may|jun|jul|aug|sep|oct)\s+\d{1,2}\b", lower_b)

        if (months_a and months_b and months_a != months_b) or (dates_a and dates_b and dates_a != dates_b):
            val_a = dates_a[0] if dates_a else months_a[0]
            val_b = dates_b[0] if dates_b else months_b[0]
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.98,
                conflict_category=ConflictCategory.DEADLINE.value,
                description=f"Conflicting project deadlines detected across documents: '{val_a}' in {stmt_a.document_name} vs '{val_b}' in {stmt_b.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning=f"Document '{stmt_a.document_name}' specifies deadline as {val_a}, whereas '{stmt_b.document_name}' asserts {val_b}.",
            )

        # 2. Technology Stack Contradiction
        dbs = [
            ("postgresql", "postgres"),
            ("mongodb", "mongo"),
            ("mysql",),
            ("dynamodb",),
            ("cassandra", "scylladb"),
            ("sqlite",),
            ("redis",),
            ("ignite",),
            ("memcached",),
        ]
        found_db_a = None
        found_db_b = None
        for group in dbs:
            if any(db in lower_a for db in group):
                found_db_a = group[0]
            if any(db in lower_b for db in group):
                found_db_b = group[0]

        if found_db_a and found_db_b and found_db_a != found_db_b:
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.96,
                conflict_category=ConflictCategory.TECHNOLOGY_STACK.value,
                description=f"Conflicting database technologies: '{found_db_a}' referenced in {stmt_a.document_name} vs '{found_db_b}' in {stmt_b.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning=f"Conflicting technology stack: '{stmt_a.document_name}' uses {found_db_a}, while '{stmt_b.document_name}' specifies {found_db_b}.",
            )

        # 3. Task Completion Status Contradiction
        done_words = ["completed", "done", "finished", "ready", "resolved"]
        pending_words = ["in progress", "pending", "incomplete", "blocked", "started"]
        a_is_done = any(w in lower_a for w in done_words)
        a_is_pending = any(w in lower_a for w in pending_words)
        b_is_done = any(w in lower_b for w in done_words)
        b_is_pending = any(w in lower_b for w in pending_words)

        if (a_is_done and b_is_pending) or (a_is_pending and b_is_done):
            stat_a = "Completed" if a_is_done else "Pending / In Progress"
            stat_b = "Completed" if b_is_done else "Pending / In Progress"
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.95,
                conflict_category=ConflictCategory.TASK_STATUS.value,
                description=f"Conflicting task completion statuses: marked as '{stat_a}' in {stmt_a.document_name} vs '{stat_b}' in {stmt_b.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning=f"Task status mismatch between documents: {stmt_a.document_name} asserts {stat_a}, while {stmt_b.document_name} asserts {stat_b}.",
            )

        # 4. Team Member Responsibility Contradiction
        lead_patterns = [
            r"(?:lead|owner|architect|component\s+lead)\s+(?:is|:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+is\s+(?:the\s+)?(?:backend|frontend|lead|owner|architect)\b",
        ]
        name_a = []
        for p in lead_patterns:
            m = re.findall(p, text_a, re.IGNORECASE)
            if m:
                name_a.extend(m)
        name_b = []
        for p in lead_patterns:
            m = re.findall(p, text_b, re.IGNORECASE)
            if m:
                name_b.extend(m)

        if name_a and name_b and name_a[0].strip().lower() != name_b[0].strip().lower():
            person_a = name_a[0].strip()
            person_b = name_b[0].strip()
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.94,
                conflict_category=ConflictCategory.TEAM_RESPONSIBILITY.value,
                description=f"Conflicting team responsibilities: '{person_a}' assigned in {stmt_a.document_name} vs '{person_b}' in {stmt_b.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning=f"Conflicting ownership: '{stmt_a.document_name}' names {person_a} as owner, whereas '{stmt_b.document_name}' assigns {person_b}.",
            )

        # 5. Outdated Decision vs Newer Decision / Architecture Contradiction
        if ("grpc" in lower_a and "rest" in lower_b) or ("rest" in lower_a and "grpc" in lower_b):
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.92,
                conflict_category=ConflictCategory.DECISION.value,
                description=f"Conflicting API communication decisions: gRPC in {stmt_a.document_name if 'grpc' in lower_a else stmt_b.document_name} vs REST in {stmt_b.document_name if 'grpc' in lower_a else stmt_a.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning="Contradictory architectural decisions recorded across documentation versions.",
            )

        if ("kafka" in lower_a and "rest" in lower_b) or ("rest" in lower_a and "kafka" in lower_b):
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.93,
                conflict_category=ConflictCategory.DECISION.value,
                description=f"Conflicting architectural decisions: Asynchronous Kafka events vs synchronous REST calls.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning="One document specifies asynchronous event streaming via Kafka, conflicting with synchronous REST architecture in another.",
            )

        # 6. Deployment / Infrastructure Architecture Contradiction
        legacy_infra_a = ("ec2" in lower_a or "chef" in lower_a)
        modern_infra_b = ("eks" in lower_b or "kubernetes" in lower_b or "helm" in lower_b)
        legacy_infra_b = ("ec2" in lower_b or "chef" in lower_b)
        modern_infra_a = ("eks" in lower_a or "kubernetes" in lower_a or "helm" in lower_a)

        if (legacy_infra_a and modern_infra_b) or (legacy_infra_b and modern_infra_a):
            return ContradictionEvaluation(
                is_contradiction=True,
                confidence=0.95,
                conflict_category=ConflictCategory.ARCHITECTURE.value,
                description=f"Conflicting deployment infrastructure: AWS EC2/Chef in {stmt_a.document_name if legacy_infra_a else stmt_b.document_name} vs AWS EKS/Kubernetes in {stmt_b.document_name if legacy_infra_a else stmt_a.document_name}.",
                statement_a=text_a,
                statement_b=text_b,
                excerpt_a=stmt_a.excerpt,
                excerpt_b=stmt_b.excerpt,
                reasoning="One document specifies legacy AWS EC2 virtual machines with Chef runbooks, which contradicts the modern containerized AWS EKS Kubernetes architecture.",
            )

        return None

    # =========================================================================
    # 4. END-TO-END PROJECT DETECTION & DATABASE PERSISTENCE
    # =========================================================================

    async def detect_project_conflicts(
        self,
        project_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        handover_id: Optional[uuid.UUID] = None,
    ) -> ContradictionDetectionReport:
        """
        Executes end-to-end contradiction detection across all uploaded project documents:
        1. Fetches chunks across project documents.
        2. Extracts factual statements.
        3. Groups statements by entity/topic.
        4. Evaluates pairs from different documents.
        5. Persists detected conflicts in the database with status='Unresolved'.
        6. Guarantees human reviewer arbitration requirement (never auto-resolves).
        """
        chunks_with_docs = await self._fetch_project_chunks(project_id, document_ids)
        if len(chunks_with_docs) < 2:
            return ContradictionDetectionReport(
                project_id=project_id,
                documents_analyzed=len({doc.id for _, doc in chunks_with_docs}),
                chunks_analyzed=len(chunks_with_docs),
                statements_extracted=0,
                topics_evaluated=0,
                contradictions_detected=0,
                conflicts=[],
                scan_timestamp=datetime.now(timezone.utc),
            )

        # 1. Extract factual statements
        statements = await self.extract_factual_statements(chunks_with_docs)

        # 2. Group by entity or topic
        topic_groups = self.group_statements_by_entity_or_topic(statements)

        detected_conflicts: List[Conflict] = []
        evaluated_pairs_signatures: Set[str] = set()

        # 3. Evaluate pairs within each topic group
        for topic_key, stmts in topic_groups.items():
            if len(stmts) < 2:
                continue

            for i in range(len(stmts)):
                for j in range(i + 1, len(stmts)):
                    stmt_a = stmts[i]
                    stmt_b = stmts[j]

                    # Cross-document comparison only
                    if stmt_a.document_id == stmt_b.document_id:
                        continue

                    # Deduplicate pair evaluation
                    pair_sig = f"{min(stmt_a.chunk_id, stmt_b.chunk_id)}::{max(stmt_a.chunk_id, stmt_b.chunk_id)}"
                    if pair_sig in evaluated_pairs_signatures:
                        continue
                    evaluated_pairs_signatures.add(pair_sig)

                    # Evaluate contradiction
                    evaluation = await self.evaluate_contradiction(stmt_a, stmt_b)
                    if evaluation and evaluation.is_contradiction:
                        # 4. Create and persist Conflict entity with the 9 mandated fields
                        conflict_entity = self._build_conflict_entity(
                            project_id=project_id,
                            handover_id=handover_id,
                            stmt_a=stmt_a,
                            stmt_b=stmt_b,
                            evaluation=evaluation,
                        )
                        self.db.add(conflict_entity)
                        detected_conflicts.append(conflict_entity)

        if detected_conflicts:
            await self.db.commit()
            for c in detected_conflicts:
                await self.db.refresh(c)

        logger.info(
            f"Contradiction detection finished for project {project_id}: "
            f"Identified and persisted {len(detected_conflicts)} contradiction(s)."
        )

        responses = [
            ConflictResponse(
                id=c.id,
                conflict_id=c.id,
                project_id=c.project_id,
                handover_id=c.handover_id,
                conflict_type=c.conflict_type,
                conflict_category=c.conflict_category,
                description=c.description,
                statement_a=c.statement_a,
                statement_b=c.statement_b,
                source_document_a=c.source_document_a,
                source_document_b=c.source_document_b,
                source_document_a_id=c.source_document_a_id,
                source_document_b_id=c.source_document_b_id,
                source_document_a_name=c.source_document_a_name,
                source_document_b_name=c.source_document_b_name,
                source_excerpt_a=c.source_excerpt_a,
                source_excerpt_b=c.source_excerpt_b,
                source_a=c.source_a,
                source_b=c.source_b,
                status=c.status,
                resolution_status=c.resolution_status,
                resolution=c.resolution,
                resolved_by=c.resolved_by,
                created_at=c.created_at,
                detection_timestamp=c.detection_timestamp,
            )
            for c in detected_conflicts
        ]

        return ContradictionDetectionReport(
            project_id=project_id,
            documents_analyzed=len({doc.id for _, doc in chunks_with_docs}),
            chunks_analyzed=len(chunks_with_docs),
            statements_extracted=len(statements),
            topics_evaluated=len(topic_groups),
            contradictions_detected=len(detected_conflicts),
            conflicts=responses,
            scan_timestamp=datetime.now(timezone.utc),
        )

    def _build_conflict_entity(
        self,
        project_id: uuid.UUID,
        handover_id: Optional[uuid.UUID],
        stmt_a: FactualStatement,
        stmt_b: FactualStatement,
        evaluation: ContradictionEvaluation,
    ) -> Conflict:
        """Constructs an unarbitrated Conflict entity storing all 9 required fields."""
        now = datetime.now(timezone.utc)
        return Conflict(
            id=uuid.uuid4(),
            project_id=project_id,
            handover_id=handover_id,
            conflict_category=evaluation.conflict_category,
            conflict_type=evaluation.conflict_category,
            description=evaluation.description,
            statement_a=stmt_a.statement,
            statement_b=stmt_b.statement,
            source_document_a_id=stmt_a.document_id,
            source_document_a_name=stmt_a.document_name,
            source_document_b_id=stmt_b.document_id,
            source_document_b_name=stmt_b.document_name,
            source_excerpt_a=stmt_a.excerpt,
            source_excerpt_b=stmt_b.excerpt,
            source_a={
                "document_id": str(stmt_a.document_id),
                "document_name": stmt_a.document_name,
                "chunk_id": str(stmt_a.chunk_id),
                "page": stmt_a.page_number,
                "statement": stmt_a.statement,
                "excerpt": stmt_a.excerpt,
                "text": stmt_a.excerpt,
            },
            source_b={
                "document_id": str(stmt_b.document_id),
                "document_name": stmt_b.document_name,
                "chunk_id": str(stmt_b.chunk_id),
                "page": stmt_b.page_number,
                "statement": stmt_b.statement,
                "excerpt": stmt_b.excerpt,
                "text": stmt_b.excerpt,
            },
            # STRICT REQUIREMENT: Never auto-select a statement as correct.
            status=ConflictResolutionStatus.UNRESOLVED.value,
            resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
            resolution=None,
            resolved_by=None,
            created_at=now,
            detection_timestamp=now,
        )

    async def _fetch_project_chunks(
        self,
        project_id: uuid.UUID,
        selected_document_ids: Optional[List[uuid.UUID]] = None,
        max_chunks: int = 200,
    ) -> List[Tuple[DocumentChunk, Document]]:
        """Retrieves ready/indexing project chunks along with parent document metadata."""
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.project_id == project_id,
                Document.processing_status.in_(["READY", "INDEXING", "INDEXED", "ready", "indexing", "indexed"]),
            )
        )
        if selected_document_ids:
            stmt = stmt.where(DocumentChunk.document_id.in_(selected_document_ids))

        stmt = stmt.order_by(Document.created_at.asc(), DocumentChunk.chunk_index.asc()).limit(max_chunks)
        result = await self.db.execute(stmt)
        rows = result.all()
        if hasattr(rows, "__await__"):
            rows = await rows
        return list(rows)

    # =========================================================================
    # 5. HUMAN REVIEWER RESOLUTION & STATUS WORKFLOWS
    # =========================================================================

    async def resolve_conflict(
        self,
        conflict_id: uuid.UUID,
        payload: ConflictResolveRequest,
        current_user: User,
    ) -> Conflict:
        """
        Records human reviewer arbitration.
        A human reviewer must decide which information is authoritative.
        Transitions status to 'Resolved' or 'Dismissed'.
        """
        stmt = select(Conflict).where(Conflict.id == conflict_id)
        res = await self.db.execute(stmt)
        if hasattr(res, "scalars"):
            sc = res.scalars()
            if hasattr(sc, "__await__"):
                sc = await sc
            conflict = sc.first() if hasattr(sc, "first") else None
            if hasattr(conflict, "__await__"):
                conflict = await conflict
        else:
            conflict = None

        if not conflict:
            raise NotFoundException("Conflict", conflict_id)

        target_status = normalize_conflict_status(payload.status)
        if target_status not in (ConflictResolutionStatus.RESOLVED.value, ConflictResolutionStatus.DISMISSED.value):
            target_status = ConflictResolutionStatus.RESOLVED.value

        authoritative_val = payload.authoritative_value or payload.chosen_value
        notes = payload.resolution_notes or payload.explanation or "Resolved by reviewer."

        conflict.status = target_status
        conflict.resolution_status = target_status
        conflict.resolved_by = current_user.id
        conflict.resolution = {
            "chosen_source": payload.chosen_source or "human_arbitration",
            "authoritative_value": authoritative_val,
            "chosen_value": authoritative_val,
            "resolution_explanation": notes,
            "explanation": notes,
            "resolution_notes": notes,
            "resolved_by_id": str(current_user.id),
            "resolved_by_name": current_user.full_name or current_user.email,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.db.commit()
        await self.db.refresh(conflict)
        return conflict

    async def update_conflict_status(
        self,
        conflict_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> Conflict:
        """Updates conflict status to Unresolved, Under Review, Resolved, or Dismissed."""
        stmt = select(Conflict).where(Conflict.id == conflict_id)
        res = await self.db.execute(stmt)
        if hasattr(res, "scalars"):
            sc = res.scalars()
            if hasattr(sc, "__await__"):
                sc = await sc
            conflict = sc.first() if hasattr(sc, "first") else None
            if hasattr(conflict, "__await__"):
                conflict = await conflict
        else:
            conflict = None

        if not conflict:
            raise NotFoundException("Conflict", conflict_id)

        norm_status = normalize_conflict_status(new_status)
        conflict.status = norm_status
        conflict.resolution_status = norm_status

        if notes:
            existing_res = conflict.resolution or {}
            existing_res["reviewer_notes"] = notes
            if current_user:
                existing_res["last_updated_by"] = current_user.full_name or current_user.email
            conflict.resolution = existing_res

        await self.db.commit()
        await self.db.refresh(conflict)
        return conflict

    async def get_conflict(self, conflict_id: uuid.UUID) -> Conflict:
        """Retrieves a single conflict record by ID."""
        stmt = select(Conflict).where(Conflict.id == conflict_id)
        res = await self.db.execute(stmt)
        if hasattr(res, "scalars"):
            sc = res.scalars()
            if hasattr(sc, "__await__"):
                sc = await sc
            conflict = sc.first() if hasattr(sc, "first") else None
            if hasattr(conflict, "__await__"):
                conflict = await conflict
        else:
            conflict = None

        if not conflict:
            raise NotFoundException("Conflict", conflict_id)
        return conflict

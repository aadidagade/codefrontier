import enum
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditActionType, AuditEntityType, AuditLog

logger = logging.getLogger("app.services.audit")

# Keys that indicate confidential credentials, passwords, or tokens
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|passwd|secret|token|api_?key|private_?key|auth(orization)?|credential|jwt|bearer|signature)",
    re.IGNORECASE,
)

# Keys that may contain raw document or file bodies which shouldn't be fully logged
CONTENT_KEY_PATTERNS = re.compile(
    r"^(content|raw_content|text|raw_text|full_text|body|file_data|document_text|extracted_text|binary_data)$",
    re.IGNORECASE,
)


def sanitize_metadata(data: Any, max_depth: int = 5) -> Any:
    """
    Recursively scrubs metadata dictionaries to protect against confidential leakage:
    1. Redacts passwords, API keys, bearer tokens, and secrets.
    2. Omits / abstracts full document text content while preserving structural metadata.
    3. Converts non-serializable objects (UUIDs, enums, datetimes) safely.
    """
    if max_depth <= 0:
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_str = str(key)

            # Check if key implies sensitive credential
            if SENSITIVE_KEY_PATTERNS.search(key_str):
                # Don't redact safe non-credential keys like 'token_type' or 'token_id' unless secret
                if key_str.lower() in ("token_type", "token_name"):
                    sanitized[key_str] = str(value) if value is not None else None
                else:
                    sanitized[key_str] = "[REDACTED]"
                continue

            # Check if key contains raw document body/content
            if CONTENT_KEY_PATTERNS.search(key_str):
                if isinstance(value, str):
                    sanitized[f"{key_str}_length"] = len(value)
                    sanitized[key_str] = f"[CONTENT_OMITTED: {len(value)} characters]"
                elif value is not None:
                    sanitized[key_str] = "[DOCUMENT_CONTENT_OMITTED]"
                continue

            sanitized[key_str] = sanitize_metadata(value, max_depth - 1)
        return sanitized

    elif isinstance(data, (list, tuple, set)):
        return [sanitize_metadata(item, max_depth - 1) for item in data]

    elif isinstance(data, uuid.UUID):
        return str(data)

    elif isinstance(data, datetime):
        return data.isoformat()

    elif isinstance(data, enum.Enum):
        return data.value

    elif isinstance(data, (str, int, float, bool)) or data is None:
        if isinstance(data, str):
            # Check string value for common token prefixes
            if data.startswith("Bearer ") or data.startswith("AIzaSy"):
                return "[REDACTED_SECRET]"
        return data

    else:
        return str(data)


def extract_request_context(request: Optional[Request]) -> Dict[str, Any]:
    """
    Extracts HTTP network and client context from the active FastAPI Request.
    """
    if not request:
        return {}

    context: Dict[str, Any] = {}

    # 1. Client IP address (considers proxy headers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        context["ip_address"] = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        context["ip_address"] = request.client.host
    else:
        context["ip_address"] = "unknown"

    # 2. User Agent
    user_agent = request.headers.get("user-agent")
    if user_agent:
        context["user_agent"] = user_agent[:255]

    # 3. HTTP Method & Request Path
    context["method"] = request.method
    context["path"] = request.url.path

    # 4. Correlation / Request ID
    req_id = request.headers.get("x-request-id") or getattr(request.state, "request_id", None)
    if req_id:
        context["request_id"] = str(req_id)

    return context


class AuditService:
    """
    Central service for recording and retrieving immutable audit trail logs.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        action: Union[AuditActionType, str],
        entity_type: Union[AuditEntityType, str],
        entity_id: Optional[Union[uuid.UUID, str]],
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        change_metadata: Optional[Dict[str, Any]] = None,
        request_context: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        commit: bool = True,
    ) -> Optional[AuditLog]:
        """
        Records an immutable audit trail entry server-side.
        Never exposes passwords, API keys, or raw confidential document bodies.
        """
        try:
            # 1. Normalize strings
            action_str = str(action.value if hasattr(action, "value") else action)
            entity_type_str = str(entity_type.value if hasattr(entity_type, "value") else entity_type)
            entity_id_str = str(entity_id) if entity_id is not None else None

            # 2. Extract and merge request context
            req_ctx = extract_request_context(request)
            if request_context:
                req_ctx.update(request_context)

            # 3. Sanitize metadata
            safe_metadata = sanitize_metadata(change_metadata or {})

            # 4. Construct AuditLog ORM entry
            audit_entry = AuditLog(
                user_id=user_id,
                project_id=project_id,
                action=action_str,
                entity_type=entity_type_str,
                entity_id=entity_id_str,
                timestamp=datetime.now(timezone.utc),
                change_metadata=safe_metadata,
                request_context=req_ctx,
            )

            add_res = self.db.add(audit_entry)
            if hasattr(add_res, "__await__"):
                await add_res
            if commit:
                await self.db.commit()
                await self.db.refresh(audit_entry)

            logger.info(
                f"[AUDIT] action={action_str} entity={entity_type_str}:{entity_id_str} "
                f"user={user_id} project={project_id}"
            )
            return audit_entry

        except Exception as exc:
            logger.error(f"Failed to record audit event: {exc}", exc_info=True)
            # Never let audit logging failure crash the primary business logic
            return None

    async def log_event(
        self,
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        action_type: Union[AuditActionType, str] = AuditActionType.HANDOVER_MODIFIED,
        entity_type: Union[AuditEntityType, str] = AuditEntityType.HANDOVER,
        entity_id: Optional[Union[uuid.UUID, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        commit: bool = True,
    ) -> Optional[AuditLog]:
        """Convenience alias for recording audit events with alternative keyword arguments."""
        return await self.record_event(
            action=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            project_id=project_id,
            change_metadata=details,
            request=request,
            commit=commit,
        )

    async def list_project_audit_logs(
        self,
        project_id: uuid.UUID,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """
        Queries project-scoped audit logs with filtering and pagination.
        Restricted to authorized project roles with VIEW_AUDIT_LOGS permission.
        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .options(selectinload(AuditLog.user))
        )
        count_stmt = select(func.count(AuditLog.id)).where(AuditLog.project_id == project_id)

        # Filters
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
            count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)

        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == str(entity_id))
            count_stmt = count_stmt.where(AuditLog.entity_id == str(entity_id))

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)

        if start_time:
            stmt = stmt.where(AuditLog.timestamp >= start_time)
            count_stmt = count_stmt.where(AuditLog.timestamp >= start_time)

        if end_time:
            stmt = stmt.where(AuditLog.timestamp <= end_time)
            count_stmt = count_stmt.where(AuditLog.timestamp <= end_time)

        # Total count
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one_or_none() or 0

        # Pagination & ordering
        stmt = stmt.order_by(AuditLog.timestamp.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def list_audit_logs(
        self,
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuditLog], int]:
        """
        Queries system or user-specific audit logs.
        """
        stmt = select(AuditLog).options(selectinload(AuditLog.user))
        count_stmt = select(func.count(AuditLog.id))

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)

        if project_id:
            stmt = stmt.where(AuditLog.project_id == project_id)
            count_stmt = count_stmt.where(AuditLog.project_id == project_id)

        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
            count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)

        if start_time:
            stmt = stmt.where(AuditLog.timestamp >= start_time)
            count_stmt = count_stmt.where(AuditLog.timestamp >= start_time)

        if end_time:
            stmt = stmt.where(AuditLog.timestamp <= end_time)
            count_stmt = count_stmt.where(AuditLog.timestamp <= end_time)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one_or_none() or 0

        stmt = stmt.order_by(AuditLog.timestamp.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_audit_log(self, audit_id: uuid.UUID) -> Optional[AuditLog]:
        """Retrieves a single audit log entry by ID."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.id == audit_id)
            .options(selectinload(AuditLog.user), selectinload(AuditLog.project))
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

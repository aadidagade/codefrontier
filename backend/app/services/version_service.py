import difflib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.models.audit_log import AuditActionType, AuditEntityType
from app.models.handover import (
    Handover,
    HandoverAuditLog,
    HandoverSection,
    HandoverVersion,
)
from app.models.user import User
from app.schemas.handover import (
    ContentChangeType,
    ComparisonSummary,
    HandoverStatus,
    HandoverVersionResponse,
    ResponsibilityDiff,
    SectionDiff,
    TaskDiff,
    VersionDiffResponse,
)
from app.services.audit_service import AuditService

logger = logging.getLogger("app.services.version")

CANONICAL_CATEGORIES: Dict[str, List[str]] = {
    "project_overview": ["project_overview", "overview", "project_summary", "1. project overview"],
    "technical_architecture": ["technical_architecture", "architecture", "system_architecture", "tech_stack", "2. technical architecture"],
    "key_decisions": ["important_decisions", "key_decisions", "decisions", "architectural_decisions", "4. important decisions"],
    "pending_tasks": ["pending_tasks", "tasks", "action_items", "next_steps", "5. pending tasks"],
    "risks_and_blockers": ["risks_and_blockers", "risks", "blockers", "known_issues", "7. risks and blockers"],
    "dependencies": ["dependencies", "setup_and_installation", "external_integrations", "system_dependencies", "3. setup and installation"],
    "team_responsibilities": ["team_responsibilities", "responsibilities", "roles", "roles_and_responsibilities"],
    "recommendations": ["recommended_next_actions", "recommendations", "next_actions", "best_practices", "10. recommended next actions"],
}


def resolve_canonical_category(section_type: str, title: str = "") -> Optional[str]:
    """Maps a section type or title to one of the 8 canonical handover categories."""
    st = (section_type or "").lower().strip()
    t = (title or "").lower().strip()
    for canon, aliases in CANONICAL_CATEGORIES.items():
        if st in aliases:
            return canon
        for alias in aliases:
            if alias.replace("_", " ") in t:
                return canon
    return None


def extract_section_text(section_data: Optional[Dict[str, Any]]) -> str:
    """Extracts a clean, deterministic textual representation from a section dict."""
    if not section_data:
        return ""
    content = section_data.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        if content.get("markdown"):
            return str(content["markdown"]).strip()
        elif content.get("summary"):
            s = str(content["summary"]).strip()
            if content.get("structured_data"):
                s += "\n" + json.dumps(content["structured_data"], indent=2)
            return s
        return json.dumps(content, indent=2)
    return str(content).strip()


def increment_version(version_str: str) -> str:
    """
    Increments a version string (e.g. 'v1.0' -> 'v1.1', '1.0' -> '1.1', 'v1' -> 'v1.1').
    """
    prefix = "v" if version_str.lower().startswith("v") else ""
    clean = version_str.lstrip("vV").strip()
    parts = clean.split(".")
    try:
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            major = parts[0]
            minor = int(parts[1]) + 1
            return f"{prefix}{major}.{minor}"
        elif len(parts) == 1 and parts[0].isdigit():
            return f"{prefix}{parts[0]}.1"
    except (ValueError, TypeError):
        pass
    return f"{prefix}{clean}.1"


def build_handover_snapshot(
    handover: Handover,
    user_or_sections: Union[Optional[uuid.UUID], Optional[List[Any]]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Constructs an immutable, self-contained snapshot representation of a handover
    including title, version, status, recipient, metadata, and all chapter sections.
    """
    if isinstance(user_or_sections, list):
        sec_list = user_or_sections
        actual_user_id = user_id
    else:
        sec_list = getattr(handover, "sections", None) or []
        actual_user_id = user_or_sections or user_id

    sections_data = []
    for s in sorted(sec_list, key=lambda x: getattr(x, "sort_order", None) if getattr(x, "sort_order", None) is not None else getattr(x, "section_order", 0)):
        sections_data.append(
            {
                "id": str(s.id),
                "section_type": getattr(s, "section_type", "general"),
                "title": getattr(s, "title", None) or getattr(s, "section_title", "Section"),
                "content": s.content,
                "confidence": getattr(s, "confidence", None),
                "review_status": getattr(s, "review_status", "pending"),
                "sort_order": getattr(s, "sort_order", None) if getattr(s, "sort_order", None) is not None else getattr(s, "section_order", 0),
                "evidence_references": [
                    {
                        "id": str(ev.id),
                        "document_id": str(ev.document_id) if getattr(ev, "document_id", None) else None,
                        "document_chunk_id": str(ev.document_chunk_id) if getattr(ev, "document_chunk_id", None) else None,
                        "quoted_text": getattr(ev, "quoted_text", ""),
                        "page_number": getattr(ev, "page_number", None),
                        "relevance_score": getattr(ev, "relevance_score", 1.0),
                        "verification_status": getattr(ev, "verification_status", "Supported"),
                    }
                    for ev in (getattr(s, "evidence_references", None) or [])
                ],
            }
        )

    conflicts_data = [
        {
            "id": str(c.id),
            "conflict_type": c.conflict_type,
            "description": c.description,
            "status": c.status,
            "resolution": c.resolution,
        }
        for c in (getattr(handover, "conflicts", None) or [])
    ]

    tasks_data = [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "status": t.status,
            "assigned_to": str(t.assigned_to) if t.assigned_to else None,
        }
        for t in (getattr(handover, "tasks", None) or [])
    ]

    return {
        "id": str(handover.id),
        "handover_id": str(handover.id),
        "project_id": str(handover.project_id),
        "title": handover.title,
        "version": handover.version,
        "status": (handover.status or "").upper(),
        "created_by": str(handover.created_by) if handover.created_by else None,
        "approved_by": str(actual_user_id) if actual_user_id else None,
        "assigned_to": str(handover.assigned_to) if handover.assigned_to else None,
        "generated_at": handover.generated_at.isoformat() if handover.generated_at else None,
        "approved_at": handover.approved_at.isoformat() if handover.approved_at else None,
        "shared_at": handover.shared_at.isoformat() if handover.shared_at else None,
        "snapshot_created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_created_by": str(actual_user_id) if actual_user_id else None,
        "sections": sections_data,
        "conflicts": conflicts_data,
        "tasks": tasks_data,
    }


class HandoverVersionService:
    """
    Service responsible for maintaining immutable handover snapshots,
    version lineage, revision submissions, separate approval statuses,
    and non-destructive restoration workflows.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_full_handover(self, handover_id: uuid.UUID) -> Optional[Handover]:
        """Loads handover with eagerly loaded sections, evidence references, conflicts, and tasks."""
        stmt = (
            select(Handover)
            .where(Handover.id == handover_id)
            .options(
                selectinload(Handover.sections).selectinload(HandoverSection.evidence_references),
                selectinload(Handover.conflicts),
                selectinload(Handover.tasks),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    def to_response(self, v: HandoverVersion) -> HandoverVersionResponse:
        """Serializes a HandoverVersion ORM model into a HandoverVersionResponse schema."""
        return HandoverVersionResponse(
            id=v.id,
            handover_id=v.handover_id,
            version_number=v.version_number,
            version_description=v.version_description,
            approval_status=v.approval_status or "DRAFT",
            parent_version_id=v.parent_version_id,
            is_latest=bool(v.is_latest),
            created_by=v.created_by,
            creator_name=v.creator.full_name if getattr(v, "creator", None) and v.creator else None,
            created_at=v.created_at,
            snapshot=v.snapshot or {},
        )

    async def create_version_snapshot(
        self,
        handover_id: uuid.UUID,
        user_id: uuid.UUID,
        version_number: Optional[str] = None,
        version_description: Optional[str] = None,
        approval_status: str = "DRAFT",
        parent_version_id: Optional[uuid.UUID] = None,
        mark_as_latest: bool = True,
    ) -> HandoverVersion:
        """
        Creates an immutable historical snapshot for a handover revision.
        Tracks creator, approval status, parent lineage, and latest version flag.
        """
        handover = await self.fetch_full_handover(handover_id)
        if not handover:
            raise NotFoundException("Handover", handover_id)

        target_version_number = version_number or handover.version or "v1.0"
        now = datetime.now(timezone.utc)

        # If parent_version_id is not specified, resolve it to current latest version
        if not parent_version_id:
            latest_v = await self.get_latest_version(handover_id)
            if latest_v:
                parent_version_id = latest_v.id

        # Mark all prior versions as is_latest=False if new version is latest
        if mark_as_latest:
            unmark_stmt = (
                update(HandoverVersion)
                .where(HandoverVersion.handover_id == handover_id)
                .values(is_latest=False)
            )
            await self.db.execute(unmark_stmt)

        snapshot = build_handover_snapshot(handover, user_id)

        version_record = HandoverVersion(
            id=uuid.uuid4(),
            handover_id=handover.id,
            version_number=target_version_number,
            snapshot=snapshot,
            version_description=version_description or f"Revision {target_version_number}",
            approval_status=approval_status,
            parent_version_id=parent_version_id,
            is_latest=mark_as_latest,
            created_by=user_id,
            created_at=now,
        )
        self.db.add(version_record)

        # Audit event
        db_audit = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=handover.id,
            user_id=user_id,
            action="version_created",
            details={
                "version_id": str(version_record.id),
                "version_number": target_version_number,
                "approval_status": approval_status,
                "description": version_description,
                "parent_version_id": str(parent_version_id) if parent_version_id else None,
            },
        )
        self.db.add(db_audit)

        audit_svc = AuditService(self.db)
        await audit_svc.record_event(
            action=AuditActionType.HANDOVER_MODIFIED,
            entity_type=AuditEntityType.HANDOVER_VERSION,
            entity_id=version_record.id,
            user_id=user_id,
            project_id=handover.project_id,
            change_metadata={
                "version_number": target_version_number,
                "approval_status": approval_status,
                "version_description": version_description,
                "parent_version_id": str(parent_version_id) if parent_version_id else None,
            },
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(version_record)
        return version_record

    async def list_versions(self, handover_id: uuid.UUID) -> List[HandoverVersionResponse]:
        """
        Retrieves all historical version records for a handover, ordered newest to oldest.
        """
        stmt = (
            select(HandoverVersion)
            .where(HandoverVersion.handover_id == handover_id)
            .options(selectinload(HandoverVersion.creator))
            .order_by(HandoverVersion.created_at.desc())
        )
        res = await self.db.execute(stmt)
        versions = res.scalars().all()

        return [self.to_response(v) for v in versions]

    async def get_version(self, handover_id: uuid.UUID, version_id: uuid.UUID) -> HandoverVersion:
        """
        Fetches an individual historical version snapshot.
        """
        stmt = (
            select(HandoverVersion)
            .where(
                HandoverVersion.id == version_id,
                HandoverVersion.handover_id == handover_id,
            )
            .options(selectinload(HandoverVersion.creator))
        )
        res = await self.db.execute(stmt)
        version = res.scalars().first()
        if not version:
            raise NotFoundException("HandoverVersion", version_id)
        return version

    async def get_latest_version(self, handover_id: uuid.UUID) -> Optional[HandoverVersion]:
        """
        Identifies and retrieves the latest active version snapshot for a handover.
        """
        stmt = (
            select(HandoverVersion)
            .where(
                HandoverVersion.handover_id == handover_id,
                HandoverVersion.is_latest == True,
            )
            .options(selectinload(HandoverVersion.creator))
            .order_by(HandoverVersion.created_at.desc())
        )
        res = await self.db.execute(stmt)
        version = res.scalars().first()
        if not version:
            # Fallback to most recent created version
            fallback_stmt = (
                select(HandoverVersion)
                .where(HandoverVersion.handover_id == handover_id)
                .options(selectinload(HandoverVersion.creator))
                .order_by(HandoverVersion.created_at.desc())
            )
            res_fallback = await self.db.execute(fallback_stmt)
            version = res_fallback.scalars().first()
        return version

    async def restore_version(
        self,
        handover_id: uuid.UUID,
        version_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Tuple[Handover, HandoverVersion]:
        """
        Requirement 7 & 8:
        Supports restoration of an earlier version by creating a new revision based on it.
        NEVER deletes historical approved versions during restoration.
        """
        handover = await self.fetch_full_handover(handover_id)
        if not handover:
            raise NotFoundException("Handover", handover_id)

        target_version = await self.get_version(handover_id, version_id)
        snapshot = target_version.snapshot or {}

        old_version = handover.version
        new_version = increment_version(old_version)

        # 1. Update current handover entity state
        if "title" in snapshot and snapshot["title"]:
            handover.title = snapshot["title"]
        handover.version = new_version
        handover.status = HandoverStatus.DRAFT.value
        handover.approved_at = None

        # 2. Restore sections from target snapshot
        snap_sections = snapshot.get("sections", [])
        existing_sections = {s.section_type: s for s in (handover.sections or [])}

        for s_data in snap_sections:
            sec_type = s_data.get("section_type")
            if sec_type in existing_sections:
                sec = existing_sections[sec_type]
                sec.title = s_data.get("title", sec.title)
                sec.content = s_data.get("content", sec.content)
                sec.review_status = "draft"
            else:
                new_sec = HandoverSection(
                    id=uuid.uuid4(),
                    handover_id=handover.id,
                    section_type=sec_type or "general",
                    title=s_data.get("title", "Section"),
                    content=s_data.get("content", ""),
                    sort_order=s_data.get("sort_order", 0),
                    review_status="draft",
                )
                self.db.add(new_sec)

        # 3. Mark all existing versions as is_latest=False
        unmark_stmt = (
            update(HandoverVersion)
            .where(HandoverVersion.handover_id == handover.id)
            .values(is_latest=False)
        )
        await self.db.execute(unmark_stmt)

        # 4. Create NEW revision based on the restored snapshot (preserving all historical snapshots)
        restored_snapshot = build_handover_snapshot(handover, user_id)
        restore_description = (
            reason
            or f"Restored revision based on earlier version {target_version.version_number}"
        )

        new_version_record = HandoverVersion(
            id=uuid.uuid4(),
            handover_id=handover.id,
            version_number=new_version,
            snapshot=restored_snapshot,
            version_description=restore_description,
            approval_status=HandoverStatus.DRAFT.value,
            parent_version_id=target_version.id,
            is_latest=True,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(new_version_record)

        # 5. Record HandoverAuditLog
        db_audit = HandoverAuditLog(
            id=uuid.uuid4(),
            handover_id=handover.id,
            user_id=user_id,
            action="version_restored",
            details={
                "restored_from_version": target_version.version_number,
                "version_snapshot_id": str(target_version.id),
                "from_version": old_version,
                "new_version": new_version,
                "new_version_id": str(new_version_record.id),
                "reason": restore_description,
            },
        )
        self.db.add(db_audit)

        # 6. Record AuditService compliance log
        audit_svc = AuditService(self.db)
        await audit_svc.record_event(
            action=AuditActionType.VERSION_RESTORED,
            entity_type=AuditEntityType.HANDOVER,
            entity_id=handover.id,
            user_id=user_id,
            project_id=handover.project_id,
            change_metadata={
                "restored_from_version": target_version.version_number,
                "source_version_id": str(target_version.id),
                "new_version": new_version,
                "new_version_id": str(new_version_record.id),
                "reason": restore_description,
            },
            commit=False,
        )

        await self.db.commit()
        await self.db.refresh(handover)
        await self.db.refresh(new_version_record)

        logger.info(
            f"Handover {handover.id} restored to new version {new_version} based on {target_version.version_number}."
        )
        return handover, new_version_record

    async def get_version_by_number(self, handover_id: uuid.UUID, version_number: str) -> HandoverVersion:
        """
        Retrieves a historical version snapshot by its version number string (e.g. 'v1.0').
        """
        stmt = (
            select(HandoverVersion)
            .where(
                HandoverVersion.handover_id == handover_id,
                HandoverVersion.version_number == version_number,
            )
            .options(selectinload(HandoverVersion.creator))
        )
        res = await self.db.execute(stmt)
        ver = res.scalars().first()
        if not ver:
            raise NotFoundException("HandoverVersion", version_number)
        return ver

    async def resolve_version(
        self,
        handover_id: uuid.UUID,
        version_id_or_number: Union[uuid.UUID, str],
    ) -> HandoverVersion:
        """Resolves a version snapshot by UUID or version number string (e.g. 'v1.0')."""
        if isinstance(version_id_or_number, uuid.UUID):
            return await self.get_version(handover_id, version_id_or_number)

        try:
            val_uuid = uuid.UUID(str(version_id_or_number))
            return await self.get_version(handover_id, val_uuid)
        except (ValueError, TypeError, AttributeError):
            return await self.get_version_by_number(handover_id, str(version_id_or_number))

    async def compare_versions(
        self,
        handover_id: uuid.UUID,
        from_version_id_or_num: Union[uuid.UUID, str],
        to_version_id_or_num: Union[uuid.UUID, str],
    ) -> VersionDiffResponse:
        """
        Industrial-grade Version Comparison Engine:
        Compares actual stored snapshots for:
        - Project overview
        - Technical architecture
        - Key decisions
        - Pending tasks
        - Risks and blockers
        - Dependencies
        - Team responsibilities
        - Recommendations
        Identifies:
        - Added content
        - Removed content
        - Modified content
        - Changed task statuses
        - Changed responsibilities
        """
        from_ver = await self.resolve_version(handover_id, from_version_id_or_num)
        to_ver = await self.resolve_version(handover_id, to_version_id_or_num)

        from_snap = from_ver.snapshot or {}
        to_snap = to_ver.snapshot or {}

        from_sections = {
            s["section_type"]: s
            for s in (from_snap.get("sections") or [])
            if isinstance(s, dict) and s.get("section_type")
        }
        to_sections = {
            s["section_type"]: s
            for s in (to_snap.get("sections") or [])
            if isinstance(s, dict) and s.get("section_type")
        }

        all_sec_types = list(
            dict.fromkeys(list(from_sections.keys()) + list(to_sections.keys()))
        )

        section_diffs: List[SectionDiff] = []
        category_status: Dict[str, str] = {c: "UNCHANGED" for c in CANONICAL_CATEGORIES}

        for st in all_sec_types:
            s_old = from_sections.get(st)
            s_new = to_sections.get(st)

            title = (s_new.get("title") if s_new else None) or (
                s_old.get("title") if s_old else st
            )

            if s_old is None and s_new is not None:
                # Added content
                new_c = extract_section_text(s_new)
                added_lines = [line for line in new_c.splitlines() if line.strip()]
                sec_diff = SectionDiff(
                    section_type=st,
                    title=title,
                    has_changed=True,
                    change_type=ContentChangeType.ADDED.value,
                    old_content=None,
                    new_content=new_c,
                    added_lines=added_lines,
                    removed_lines=[],
                    diff_summary=f"Chapter '{title}' added with {len(added_lines)} lines.",
                )
            elif s_new is None and s_old is not None:
                # Removed content
                old_c = extract_section_text(s_old)
                removed_lines = [line for line in old_c.splitlines() if line.strip()]
                sec_diff = SectionDiff(
                    section_type=st,
                    title=title,
                    has_changed=True,
                    change_type=ContentChangeType.REMOVED.value,
                    old_content=old_c,
                    new_content=None,
                    added_lines=[],
                    removed_lines=removed_lines,
                    diff_summary=f"Chapter '{title}' removed ({len(removed_lines)} lines).",
                )
            else:
                old_c = extract_section_text(s_old)
                new_c = extract_section_text(s_new)
                has_changed = old_c != new_c

                if has_changed:
                    # Modified content
                    diff_matcher = list(difflib.ndiff(old_c.splitlines(), new_c.splitlines()))
                    added = [l[2:] for l in diff_matcher if l.startswith("+ ")]
                    removed = [l[2:] for l in diff_matcher if l.startswith("- ")]

                    sec_diff = SectionDiff(
                        section_type=st,
                        title=title,
                        has_changed=True,
                        change_type=ContentChangeType.MODIFIED.value,
                        old_content=old_c,
                        new_content=new_c,
                        added_lines=added,
                        removed_lines=removed,
                        diff_summary=f"Chapter '{title}' modified ({len(added)} lines added, {len(removed)} lines removed).",
                    )
                else:
                    sec_diff = SectionDiff(
                        section_type=st,
                        title=title,
                        has_changed=False,
                        change_type=ContentChangeType.UNCHANGED.value,
                        old_content=old_c,
                        new_content=new_c,
                        added_lines=[],
                        removed_lines=[],
                        diff_summary="Content identical across versions.",
                    )

            section_diffs.append(sec_diff)

            # Map to canonical category
            canon = resolve_canonical_category(st, title)
            if canon:
                category_status[canon] = sec_diff.change_type

        # =========================================================================
        # TASK COMPARISON: Changed task statuses & responsibilities
        # =========================================================================
        from_tasks = from_snap.get("tasks") or []
        to_tasks = to_snap.get("tasks") or []

        from_tasks_map = {}
        for t in from_tasks:
            if isinstance(t, dict):
                key = str(t.get("id")) if t.get("id") else t.get("title", "").strip().lower()
                from_tasks_map[key] = t

        to_tasks_map = {}
        for t in to_tasks:
            if isinstance(t, dict):
                key = str(t.get("id")) if t.get("id") else t.get("title", "").strip().lower()
                to_tasks_map[key] = t

        task_diffs: List[TaskDiff] = []
        responsibility_diffs: List[ResponsibilityDiff] = []

        # Check added and modified tasks
        for key, new_t in to_tasks_map.items():
            task_title = new_t.get("title", "Task")
            new_status = new_t.get("status")
            new_assignee = str(new_t.get("assigned_to")) if new_t.get("assigned_to") else None
            new_priority = new_t.get("priority")
            new_desc = new_t.get("description")

            if key in from_tasks_map:
                old_t = from_tasks_map[key]
                old_status = old_t.get("status")
                old_assignee = str(old_t.get("assigned_to")) if old_t.get("assigned_to") else None
                old_priority = old_t.get("priority")
                old_desc = old_t.get("description")

                status_changed = (old_status != new_status)
                assignee_changed = (old_assignee != new_assignee)
                priority_changed = (old_priority != new_priority)
                desc_changed = (old_desc != new_desc)
                has_changed = status_changed or assignee_changed or priority_changed or desc_changed

                task_diffs.append(
                    TaskDiff(
                        task_id=str(new_t.get("id")) if new_t.get("id") else None,
                        title=task_title,
                        change_type=ContentChangeType.MODIFIED.value if has_changed else ContentChangeType.UNCHANGED.value,
                        status_changed=status_changed,
                        old_status=old_status,
                        new_status=new_status,
                        assignee_changed=assignee_changed,
                        old_assignee=old_assignee,
                        new_assignee=new_assignee,
                        priority_changed=priority_changed,
                        old_priority=old_priority,
                        new_priority=new_priority,
                        description_changed=desc_changed,
                    )
                )

                if assignee_changed:
                    c_type = "REASSIGNED" if old_assignee and new_assignee else ("ASSIGNED" if new_assignee else "UNASSIGNED")
                    responsibility_diffs.append(
                        ResponsibilityDiff(
                            entity_type="task",
                            entity_id=str(new_t.get("id")) if new_t.get("id") else None,
                            entity_name=task_title,
                            change_type=c_type,
                            old_assignee=old_assignee,
                            new_assignee=new_assignee,
                            details=f"Task '{task_title}' responsibility changed from {old_assignee or 'Unassigned'} to {new_assignee or 'Unassigned'}.",
                        )
                    )
            else:
                # Added task
                task_diffs.append(
                    TaskDiff(
                        task_id=str(new_t.get("id")) if new_t.get("id") else None,
                        title=task_title,
                        change_type=ContentChangeType.ADDED.value,
                        status_changed=False,
                        old_status=None,
                        new_status=new_status,
                        assignee_changed=bool(new_assignee),
                        old_assignee=None,
                        new_assignee=new_assignee,
                        priority_changed=False,
                        old_priority=None,
                        new_priority=new_priority,
                        description_changed=False,
                    )
                )
                if new_assignee:
                    responsibility_diffs.append(
                        ResponsibilityDiff(
                            entity_type="task",
                            entity_id=str(new_t.get("id")) if new_t.get("id") else None,
                            entity_name=task_title,
                            change_type="ASSIGNED",
                            old_assignee=None,
                            new_assignee=new_assignee,
                            details=f"New task '{task_title}' assigned to {new_assignee}.",
                        )
                    )

        # Check removed tasks
        for key, old_t in from_tasks_map.items():
            if key not in to_tasks_map:
                task_title = old_t.get("title", "Task")
                old_assignee = str(old_t.get("assigned_to")) if old_t.get("assigned_to") else None
                task_diffs.append(
                    TaskDiff(
                        task_id=str(old_t.get("id")) if old_t.get("id") else None,
                        title=task_title,
                        change_type=ContentChangeType.REMOVED.value,
                        status_changed=False,
                        old_status=old_t.get("status"),
                        new_status=None,
                        assignee_changed=bool(old_assignee),
                        old_assignee=old_assignee,
                        new_assignee=None,
                        priority_changed=False,
                        old_priority=old_t.get("priority"),
                        new_priority=None,
                        description_changed=False,
                    )
                )
                if old_assignee:
                    responsibility_diffs.append(
                        ResponsibilityDiff(
                            entity_type="task",
                            entity_id=str(old_t.get("id")) if old_t.get("id") else None,
                            entity_name=task_title,
                            change_type="UNASSIGNED",
                            old_assignee=old_assignee,
                            new_assignee=None,
                            details=f"Task '{task_title}' previously assigned to {old_assignee} was removed.",
                        )
                    )

        # Overall Handover Assignment check
        old_h_assigned = str(from_snap.get("assigned_to")) if from_snap.get("assigned_to") else None
        new_h_assigned = str(to_snap.get("assigned_to")) if to_snap.get("assigned_to") else None
        if old_h_assigned != new_h_assigned:
            c_type = "REASSIGNED" if old_h_assigned and new_h_assigned else ("ASSIGNED" if new_h_assigned else "UNASSIGNED")
            responsibility_diffs.append(
                ResponsibilityDiff(
                    entity_type="handover",
                    entity_id=str(handover_id),
                    entity_name="Handover Lead Assignee",
                    change_type=c_type,
                    old_assignee=old_h_assigned,
                    new_assignee=new_h_assigned,
                    details=f"Overall handover ownership changed from {old_h_assigned or 'Unassigned'} to {new_h_assigned or 'Unassigned'}.",
                )
            )

        # Reflect task & responsibility changes in canonical categories
        if any(t.change_type != ContentChangeType.UNCHANGED.value for t in task_diffs):
            if category_status.get("pending_tasks") == "UNCHANGED":
                category_status["pending_tasks"] = "MODIFIED"

        if len(responsibility_diffs) > 0:
            if category_status.get("team_responsibilities") == "UNCHANGED":
                category_status["team_responsibilities"] = "MODIFIED"

        # Compute summary
        added_sec = sum(1 for s in section_diffs if s.change_type == ContentChangeType.ADDED.value)
        rem_sec = sum(1 for s in section_diffs if s.change_type == ContentChangeType.REMOVED.value)
        mod_sec = sum(1 for s in section_diffs if s.change_type == ContentChangeType.MODIFIED.value)
        unch_sec = sum(1 for s in section_diffs if s.change_type == ContentChangeType.UNCHANGED.value)

        added_t = sum(1 for t in task_diffs if t.change_type == ContentChangeType.ADDED.value)
        rem_t = sum(1 for t in task_diffs if t.change_type == ContentChangeType.REMOVED.value)
        status_chg = sum(1 for t in task_diffs if t.status_changed)
        resp_chg = len(responsibility_diffs)

        has_diff = (added_sec + rem_sec + mod_sec + added_t + rem_t + status_chg + resp_chg) > 0

        summary = ComparisonSummary(
            total_sections_compared=len(section_diffs),
            added_sections_count=added_sec,
            removed_sections_count=rem_sec,
            modified_sections_count=mod_sec,
            unchanged_sections_count=unch_sec,
            total_tasks_compared=len(task_diffs),
            added_tasks_count=added_t,
            removed_tasks_count=rem_t,
            task_status_changes_count=status_chg,
            responsibility_changes_count=resp_chg,
            has_differences=has_diff,
            category_status=category_status,
        )

        return VersionDiffResponse(
            from_version_id=from_ver.id,
            from_version_number=from_ver.version_number,
            to_version_id=to_ver.id,
            to_version_number=to_ver.version_number,
            summary=summary,
            section_diffs=section_diffs,
            task_diffs=task_diffs,
            responsibility_diffs=responsibility_diffs,
        )

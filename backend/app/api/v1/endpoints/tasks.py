import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_task_access, require_project_membership
from app.models.user import User
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskDependency
from app.schemas.common import ApiResponse
from app.schemas.task import (
    TaskResponse,
    TaskCreate,
    TaskUpdate,
    TaskDependencyCreate,
    TaskDependencyItem,
    TaskDependencyListResponse,
    ProgressNoteCreate,
)
from app.services.notification_service import NotificationService
from app.core.exceptions import NotFoundException, ForbiddenException, BadRequestException

logger = logging.getLogger("app.api.tasks")

# Router mounted at /tasks
router = APIRouter()

# Router mounted at /projects for RESTful /projects/{project_id}/tasks
project_tasks_router = APIRouter()


# =============================================================================
# HELPER FUNCTIONS: CYCLE DETECTION & BLOCKING STATUS
# =============================================================================

async def would_create_cycle(task_id: uuid.UUID, depends_on_task_id: uuid.UUID, db: AsyncSession) -> bool:
    """
    Checks if adding a directed dependency (task_id depends on depends_on_task_id)
    would create a cycle in the task graph.
    Cycles occur if depends_on_task_id can already reach task_id transitively.
    """
    if task_id == depends_on_task_id:
        return True

    visited = set()
    queue = [depends_on_task_id]

    while queue:
        curr = queue.pop(0)
        if curr == task_id:
            return True
        if curr in visited:
            continue
        visited.add(curr)

        stmt = select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == curr)
        res = await db.execute(stmt)
        prereqs = res.scalars().all()
        for p in prereqs:
            if p not in visited:
                queue.append(p)

    return False


async def get_task_counts_and_blocked(task_id: uuid.UUID, db: AsyncSession):
    """Computes prerequisites count, dependents count, and whether task is currently blocked."""
    # Prerequisites
    prereq_stmt = (
        select(Task.status)
        .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
        .where(TaskDependency.task_id == task_id)
    )
    p_res = await db.execute(prereq_stmt)
    p_statuses = p_res.scalars().all()
    dependencies_count = len(p_statuses)
    is_blocked = any(s != "completed" for s in p_statuses)

    # Dependents
    dep_stmt = select(TaskDependency.id).where(TaskDependency.depends_on_task_id == task_id)
    d_res = await db.execute(dep_stmt)
    dependents_count = len(d_res.scalars().all())

    return dependencies_count, dependents_count, is_blocked


# =============================================================================
# PROJECT-SCOPED TASK ENDPOINTS (/projects/{project_id}/tasks)
# =============================================================================

@project_tasks_router.post(
    "/{project_id}/tasks",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Project Continuation Task",
    description="Creates a transition responsibility linked to the project or a handover chapter.",
)
async def create_project_task(
    project_id: uuid.UUID,
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership()(project_id=project_id, current_user=current_user, db=db)

    # Validate assignee is a member of the project
    assigned_user_id = payload.assigned_to or current_user.id
    member_check = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == assigned_user_id,
    )
    m_res = await db.execute(member_check)
    if not m_res.scalars().first():
        raise BadRequestException(f"Assigned user '{assigned_user_id}' is not a member of this project.")

    task = Task(
        id=uuid.uuid4(),
        project_id=project_id,
        handover_id=payload.handover_id,
        title=payload.title,
        description=payload.description,
        assigned_to=assigned_user_id,
        priority=payload.priority,
        status=payload.status,
        due_date=payload.due_date,
    )
    db.add(task)
    await db.flush()

    # Dispatch assignment notification if assigned to another user
    if assigned_user_id and assigned_user_id != current_user.id:
        notif_svc = NotificationService(db)
        await notif_svc.notify_task_assigned(
            assigned_to=assigned_user_id,
            project_id=project_id,
            task_id=task.id,
            task_title=task.title,
            assigned_by_name=current_user.full_name or current_user.email,
        )

    await db.commit()
    await db.refresh(task)

    return ApiResponse(
        data=TaskResponse(
            id=task.id,
            project_id=task.project_id,
            handover_id=task.handover_id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            dependencies_count=0,
            dependents_count=0,
            is_blocked=False,
        ),
        message="Continuation task created successfully.",
    )


@project_tasks_router.get(
    "/{project_id}/tasks",
    response_model=ApiResponse[List[TaskResponse]],
    summary="List Project Tasks",
    description="Retrieves assigned project transition tasks with priority and blocking status.",
)
async def list_project_tasks(
    project_id: uuid.UUID,
    handoverId: Optional[uuid.UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    assigned_to: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership()(project_id=project_id, current_user=current_user, db=db)

    stmt = select(Task).where(Task.project_id == project_id)
    if handoverId:
        stmt = stmt.where(Task.handover_id == handoverId)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if assigned_to:
        stmt = stmt.where(Task.assigned_to == assigned_to)

    stmt = stmt.order_by(Task.created_at.desc())
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    items = []
    for t in tasks:
        deps_count, dependents_count, is_blocked = await get_task_counts_and_blocked(t.id, db)
        items.append(
            TaskResponse(
                id=t.id,
                project_id=t.project_id,
                handover_id=t.handover_id,
                title=t.title,
                description=t.description,
                assigned_to=t.assigned_to,
                priority=t.priority,
                status=t.status,
                due_date=t.due_date,
                created_at=t.created_at,
                updated_at=t.updated_at,
                dependencies_count=deps_count,
                dependents_count=dependents_count,
                is_blocked=is_blocked,
            )
        )

    return ApiResponse(
        data=items,
        message=f"Retrieved {len(items)} task(s) for project.",
    )


# =============================================================================
# GLOBAL TASK MANAGEMENT ENDPOINTS (/tasks/...)
# =============================================================================

@router.get(
    "",
    response_model=ApiResponse[List[TaskResponse]],
    summary="List Continuation Tasks (Global)",
)
async def list_tasks_global(
    projectId: Optional[uuid.UUID] = None,
    handoverId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not projectId:
        return ApiResponse(data=[], message="Project ID parameter 'projectId' is required.")

    return await list_project_tasks(
        project_id=projectId,
        handoverId=handoverId,
        current_user=current_user,
        db=db,
    )


@router.post(
    "",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Continuation Task (Body projectId)",
)
async def create_task_global(
    projectId: uuid.UUID,
    payload: TaskCreate,
    handoverId: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload.handover_id = payload.handover_id or handoverId
    return await create_project_task(
        project_id=projectId,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/{task_id}",
    response_model=ApiResponse[TaskResponse],
    summary="Get Task Details (IDOR Protected)",
)
async def get_task(
    task: Task = Depends(require_task_access),
    db: AsyncSession = Depends(get_db),
):
    deps_count, dependents_count, is_blocked = await get_task_counts_and_blocked(task.id, db)

    return ApiResponse(
        data=TaskResponse(
            id=task.id,
            project_id=task.project_id,
            handover_id=task.handover_id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            dependencies_count=deps_count,
            dependents_count=dependents_count,
            is_blocked=is_blocked,
        ),
        message="Task retrieved successfully.",
    )


@router.patch(
    "/{task_id}",
    response_model=ApiResponse[TaskResponse],
    summary="Update Task Attributes and Status (IDOR Protected)",
)
async def update_task(
    payload: TaskUpdate,
    task: Task = Depends(require_task_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    old_status = task.status
    old_assignee = task.assigned_to

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_date is not None:
        task.due_date = payload.due_date

    # Assignee validation
    if payload.assigned_to is not None:
        m_check = select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == payload.assigned_to,
        )
        m_res = await db.execute(m_check)
        if not m_res.scalars().first():
            raise BadRequestException(f"Assigned user '{payload.assigned_to}' is not a member of this project.")
        task.assigned_to = payload.assigned_to

        # Notify new assignee
        if payload.assigned_to != current_user.id and payload.assigned_to != old_assignee:
            notif_svc = NotificationService(db)
            await notif_svc.notify_task_assigned(
                assigned_to=payload.assigned_to,
                project_id=task.project_id,
                task_id=task.id,
                task_title=task.title,
                assigned_by_name=current_user.full_name or current_user.email,
            )

    # Status update & unblocking dependent tasks
    if payload.status is not None:
        task.status = payload.status
        if payload.status == "completed" and old_status != "completed":
            # Check all tasks that depend on this task
            dep_stmt = (
                select(Task)
                .join(TaskDependency, TaskDependency.task_id == Task.id)
                .where(TaskDependency.depends_on_task_id == task.id)
            )
            d_res = await db.execute(dep_stmt)
            dependent_tasks = d_res.scalars().all()

            notif_svc = NotificationService(db)
            for d_task in dependent_tasks:
                if d_task.assigned_to:
                    # Check if all other prerequisites are also completed
                    _, _, still_blocked = await get_task_counts_and_blocked(d_task.id, db)
                    if not still_blocked:
                        await notif_svc.notify_task_unblocked(
                            assigned_to=d_task.assigned_to,
                            project_id=d_task.project_id,
                            task_id=d_task.id,
                            task_title=d_task.title,
                            prerequisite_title=task.title,
                        )

    await db.commit()
    await db.refresh(task)

    deps_count, dependents_count, is_blocked = await get_task_counts_and_blocked(task.id, db)

    return ApiResponse(
        data=TaskResponse(
            id=task.id,
            project_id=task.project_id,
            handover_id=task.handover_id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            dependencies_count=deps_count,
            dependents_count=dependents_count,
            is_blocked=is_blocked,
        ),
        message="Task updated successfully.",
    )


@router.delete(
    "/{task_id}",
    response_model=ApiResponse[dict],
    summary="Delete Task (ADMIN / LEAD Only)",
)
async def delete_task(
    task: Task = Depends(require_task_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_project_membership(
        allowed_roles=[ProjectMemberRole.ADMIN, ProjectMemberRole.LEAD]
    )(project_id=task.project_id, current_user=current_user, db=db)

    await db.delete(task)
    await db.commit()

    return ApiResponse(
        data={"taskId": str(task.id), "deleted": True},
        message="Task deleted successfully.",
    )


# =============================================================================
# TASK DEPENDENCIES & CIRCULAR DEPENDENCY PREVENTION
# =============================================================================

@router.post(
    "/{task_id}/dependencies",
    response_model=ApiResponse[TaskDependencyItem],
    status_code=status.HTTP_201_CREATED,
    summary="Add Task Prerequisite Dependency (Cycle Protected)",
    description="Declares that task_id requires depends_on_task_id to be resolved first. Prevents circular dependencies.",
)
async def add_task_dependency(
    payload: TaskDependencyCreate,
    task: Task = Depends(require_task_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. No self-dependency
    if payload.depends_on_task_id == task.id:
        raise BadRequestException("Self-dependency is invalid: a task cannot depend on itself.")

    # 2. Prerequisite task must exist and belong to the same project
    prereq_stmt = select(Task).where(Task.id == payload.depends_on_task_id)
    p_res = await db.execute(prereq_stmt)
    prereq_task = p_res.scalars().first()
    if not prereq_task:
        raise NotFoundException("Prerequisite Task", payload.depends_on_task_id)

    if prereq_task.project_id != task.project_id:
        raise BadRequestException("Cross-project dependencies are not allowed. Both tasks must belong to the same project.")

    # 3. Check for existing dependency
    existing_stmt = select(TaskDependency).where(
        TaskDependency.task_id == task.id,
        TaskDependency.depends_on_task_id == payload.depends_on_task_id,
    )
    ex_res = await db.execute(existing_stmt)
    existing_dep = ex_res.scalars().first()
    if existing_dep:
        return ApiResponse(
            data=TaskDependencyItem(
                id=existing_dep.id,
                task_id=existing_dep.task_id,
                depends_on_task_id=existing_dep.depends_on_task_id,
                depends_on_title=prereq_task.title,
                depends_on_status=prereq_task.status,
                is_resolved=(prereq_task.status == "completed"),
            ),
            message="Dependency already exists.",
        )

    # 4. Strict Circular Dependency Prevention:
    # Does adding task.id -> payload.depends_on_task_id create a cycle?
    if await would_create_cycle(task_id=task.id, depends_on_task_id=payload.depends_on_task_id, db=db):
        raise BadRequestException(
            "Circular dependency detected: declaring this prerequisite would introduce a cycle in the task graph."
        )

    dep = TaskDependency(
        id=uuid.uuid4(),
        task_id=task.id,
        depends_on_task_id=payload.depends_on_task_id,
    )
    db.add(dep)
    await db.commit()
    await db.refresh(dep)

    return ApiResponse(
        data=TaskDependencyItem(
            id=dep.id,
            task_id=dep.task_id,
            depends_on_task_id=dep.depends_on_task_id,
            depends_on_title=prereq_task.title,
            depends_on_status=prereq_task.status,
            is_resolved=(prereq_task.status == "completed"),
        ),
        message=f"Dependency established: '{task.title}' now requires '{prereq_task.title}' to be resolved first.",
    )


@router.get(
    "/{task_id}/dependencies",
    response_model=ApiResponse[TaskDependencyListResponse],
    summary="Get Task Prerequisites and Dependents",
    description="Returns list of tasks this task depends on (blocking it) and tasks waiting on it.",
)
async def get_task_dependencies(
    task: Task = Depends(require_task_access),
    db: AsyncSession = Depends(get_db),
):
    # Query prerequisites (tasks this task depends on)
    prereq_stmt = (
        select(TaskDependency, Task)
        .join(Task, TaskDependency.depends_on_task_id == Task.id)
        .where(TaskDependency.task_id == task.id)
    )
    prereq_res = await db.execute(prereq_stmt)
    prereq_rows = prereq_res.all()

    prerequisites = [
        TaskDependencyItem(
            id=dep.id,
            task_id=dep.task_id,
            depends_on_task_id=dep.depends_on_task_id,
            depends_on_title=t.title,
            depends_on_status=t.status,
            is_resolved=(t.status == "completed"),
        )
        for dep, t in prereq_rows
    ]

    # Query dependents (tasks waiting on this task)
    dep_stmt = (
        select(TaskDependency, Task)
        .join(Task, TaskDependency.task_id == Task.id)
        .where(TaskDependency.depends_on_task_id == task.id)
    )
    dep_res = await db.execute(dep_stmt)
    dep_rows = dep_res.all()

    dependents = [
        TaskDependencyItem(
            id=dep.id,
            task_id=dep.task_id,
            depends_on_task_id=dep.depends_on_task_id,
            depends_on_title=t.title,
            depends_on_status=t.status,
            is_resolved=(task.status == "completed"),
        )
        for dep, t in dep_rows
    ]

    is_blocked = any(not item.is_resolved for item in prerequisites)

    return ApiResponse(
        data=TaskDependencyListResponse(
            task_id=task.id,
            task_title=task.title,
            task_status=task.status,
            is_blocked=is_blocked,
            prerequisites=prerequisites,
            dependents=dependents,
        ),
        message=f"Retrieved dependencies: {len(prerequisites)} prerequisite(s), {len(dependents)} dependent(s).",
    )


@router.delete(
    "/{task_id}/dependencies/{depends_on_task_id}",
    response_model=ApiResponse[dict],
    summary="Remove Task Dependency",
)
async def remove_task_dependency(
    depends_on_task_id: uuid.UUID,
    task: Task = Depends(require_task_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        delete(TaskDependency)
        .where(
            TaskDependency.task_id == task.id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
    )
    res = await db.execute(stmt)
    await db.commit()

    return ApiResponse(
        data={"taskId": str(task.id), "removedDependency": str(depends_on_task_id)},
        message="Dependency removed successfully.",
    )


@router.post(
    "/{task_id}/notes",
    response_model=ApiResponse[dict],
    summary="Add Progress Note to Task",
)
async def add_task_progress_note(
    payload: ProgressNoteCreate,
    task: Task = Depends(require_task_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    author = current_user.full_name or current_user.email
    new_entry = f"\n\n---\n**Progress Note ({timestamp} by {author}):**\n{payload.text}"

    task.description = (task.description or "") + new_entry
    await db.commit()

    return ApiResponse(
        data={"taskId": str(task.id), "noteAdded": True},
        message="Progress note added to task.",
    )

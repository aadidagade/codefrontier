import uuid
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task, TaskDependency
from app.core.exceptions import ValidationException


class TaskRepository:
    """
    Project-scoped Task repository with circular dependency prevention.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def would_create_cycle(self, task_id: uuid.UUID, depends_on_task_id: uuid.UUID) -> bool:
        """
        Detects whether adding (task_id -> depends_on_task_id) would introduce a cycle.
        A cycle occurs if depends_on_task_id already depends (directly or indirectly) on task_id.
        Traverses the directed graph using Breadth-First Search (BFS).
        """
        if task_id == depends_on_task_id:
            return True

        visited: Set[uuid.UUID] = set()
        queue: List[uuid.UUID] = [depends_on_task_id]

        while queue:
            current = queue.pop(0)
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            # Find all tasks that 'current' depends on
            stmt = select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == current)
            result = await self.db.execute(stmt)
            next_dependencies = result.scalars().all()
            for dep_id in next_dependencies:
                if dep_id not in visited:
                    queue.append(dep_id)

        return False

    async def add_dependency(self, task_id: uuid.UUID, depends_on_task_id: uuid.UUID) -> TaskDependency:
        """Adds a verified, non-circular task dependency."""
        if await self.would_create_cycle(task_id, depends_on_task_id):
            raise ValidationException(
                message="Cannot add task dependency: a circular dependency cycle would be created.",
                details={"task_id": str(task_id), "depends_on_task_id": str(depends_on_task_id)},
            )

        dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
        self.db.add(dep)
        await self.db.commit()
        await self.db.refresh(dep)
        return dep

    async def list_by_project(self, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """Project-scoped task query pattern."""
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.due_date.asc().nulls_last())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

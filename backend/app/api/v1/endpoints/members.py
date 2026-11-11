import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.authorization import require_project_membership
from app.models.project import ProjectMember, ProjectMemberRole
from app.services.project_service import ProjectService
from app.schemas.common import ApiResponse
from app.schemas.project import (
    MemberAdd,
    MemberUpdateRole,
    ProjectMemberResponse,
)

router = APIRouter()


@router.post(
    "/{project_id}/members",
    response_model=ApiResponse[ProjectMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Invite / Add Member to Project (ADMIN Only)",
    description="Invites an existing registered user to the project workspace with an assigned role (ADMIN, OUTGOING, INCOMING, LEAD). Restricted to ADMIN.",
)
async def add_project_member(
    project_id: uuid.UUID,
    payload: MemberAdd,
    member: ProjectMember = Depends(require_project_membership(allowed_roles=[ProjectMemberRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    from app.services.notification_service import NotificationService

    service = ProjectService(db)
    new_member = await service.add_member(project_id, payload)

    notif_svc = NotificationService(db)
    await notif_svc.notify_project_invitation(
        user_id=new_member.user_id,
        project_id=project_id,
        project_name="Project Workspace",
        invited_by_name="Project Admin",
        role=new_member.role,
    )
    await db.commit()

    return ApiResponse(
        data=new_member,
        message=f"Member '{new_member.email}' assigned role '{new_member.role}' in project workspace.",
    )


@router.get(
    "/{project_id}/members",
    response_model=ApiResponse[List[ProjectMemberResponse]],
    summary="List Project Members",
    description="Retrieves the list of authorized team members in this project. Protected by project membership check.",
)
async def list_project_members(
    project_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    members = await service.list_members(project_id)
    return ApiResponse(
        data=members,
        message="Project members retrieved successfully.",
    )


@router.patch(
    "/{project_id}/members/{member_id}",
    response_model=ApiResponse[ProjectMemberResponse],
    summary="Update Member Role (ADMIN Only)",
    description="Changes a member's role (ADMIN, OUTGOING, INCOMING, LEAD). Automatically prevents demoting the last ADMIN.",
)
async def update_project_member_role(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    payload: MemberUpdateRole,
    member: ProjectMember = Depends(require_project_membership(allowed_roles=[ProjectMemberRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    updated = await service.update_member_role(project_id, member_id, payload)
    return ApiResponse(
        data=updated,
        message=f"Member role updated to '{updated.role}'.",
    )


@router.delete(
    "/{project_id}/members/{member_id}",
    response_model=ApiResponse[bool],
    summary="Remove Member from Project (ADMIN Only)",
    description="Removes a member from the project. Automatically prevents removing the last ADMIN.",
)
async def remove_project_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership(allowed_roles=[ProjectMemberRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    await service.remove_member(project_id, member_id)
    return ApiResponse(
        data=True,
        message="Member removed from project workspace.",
    )

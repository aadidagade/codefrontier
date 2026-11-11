import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.common import ApiResponse
from app.schemas.notification import NotificationResponse
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[List[NotificationResponse]],
    summary="List Authenticated User Notifications",
    description="Retrieves database-backed in-app alerts with optional unread filter.",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    notifications = result.scalars().all()

    items = [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            project_id=n.project_id,
            title=n.title,
            message=n.message,
            notification_type=n.notification_type,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]

    return ApiResponse(
        data=items,
        message=f"Retrieved {len(items)} notification(s).",
    )


@router.patch(
    "/{notification_id}/read",
    response_model=ApiResponse[NotificationResponse],
    summary="Mark Notification as Read",
)
@router.post(
    "/{notification_id}/read",
    response_model=ApiResponse[NotificationResponse],
    summary="Mark Notification as Read (POST alias)",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    notif = result.scalars().first()
    if not notif:
        raise NotFoundException("Notification", notification_id)

    notif.is_read = True
    await db.commit()
    await db.refresh(notif)

    return ApiResponse(
        data=NotificationResponse(
            id=notif.id,
            user_id=notif.user_id,
            project_id=notif.project_id,
            title=notif.title,
            message=notif.message,
            notification_type=notif.notification_type,
            is_read=notif.is_read,
            created_at=notif.created_at,
        ),
        message="Notification marked as read.",
    )


@router.post(
    "/read-all",
    response_model=ApiResponse[dict],
    summary="Mark All Notifications as Read",
    description="Bulk marks all pending unread notifications for current user as read.",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    res = await db.execute(stmt)
    await db.commit()

    count = res.rowcount if hasattr(res, "rowcount") else 0
    return ApiResponse(
        data={"markedReadCount": count},
        message=f"Marked {count} notification(s) as read.",
    )

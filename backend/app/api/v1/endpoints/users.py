import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.core.exceptions import NotFoundException

router = APIRouter()


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    profile_image: Optional[str] = None
    is_active: bool


@router.get(
    "",
    response_model=ApiResponse[List[UserSummary]],
    summary="List Team Members",
    description="Retrieves registered users for handover assignment and project membership.",
)
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.is_active == True).order_by(User.full_name.asc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    return ApiResponse(
        data=[UserSummary.model_validate(u) for u in users],
        message="Users listed successfully.",
    )


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserSummary],
    summary="Get User Profile",
)
async def get_user_profile(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise NotFoundException("User", user_id)

    return ApiResponse(
        data=UserSummary.model_validate(user),
        message="User profile retrieved.",
    )

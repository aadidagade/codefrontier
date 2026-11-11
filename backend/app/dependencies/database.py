from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

# Re-export get_db dependency for clean imports across routers
__all__ = ["get_db", "AsyncSession"]

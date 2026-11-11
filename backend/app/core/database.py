from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

# SQLAlchemy 2.0 Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Rolls back transaction automatically if an unhandled exception occurs.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> dict:
    """
    Executes health checks against PostgreSQL:
    1. SELECT 1 ping.
    2. pgvector extension detection.
    """
    try:
        async with engine.connect() as conn:
            # Basic connectivity
            result = await conn.execute(text("SELECT version();"))
            db_version = result.scalar()

            # pgvector verification
            ext_result = await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
            )
            vector_version = ext_result.scalar()

            return {
                "status": "connected",
                "database": "PostgreSQL",
                "version": db_version,
                "pgvector_enabled": vector_version is not None,
                "pgvector_version": vector_version,
            }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "pgvector_enabled": False,
        }

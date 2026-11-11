from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import check_database_health
from app.services.ai_service import ai_service
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get(
    "/health",
    summary="Overall System Health",
    description="Returns aggregate health status for API, PostgreSQL database, and Google Gemini AI services.",
)
async def get_overall_health():
    db_health = await check_database_health()
    ai_health = await ai_service.check_ai_health()

    db_ok = db_health.get("status") == "connected"
    ai_ok = ai_health.get("status") == "connected"

    if db_ok and ai_ok:
        overall_status = "healthy"
        status_code = status.HTTP_200_OK
    elif db_ok or ai_ok:
        overall_status = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    content = {
        "success": overall_status != "unhealthy",
        "status": overall_status,
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "services": {
            "database": db_health,
            "ai": ai_health,
        },
    }
    return JSONResponse(status_code=status_code, content=content)


@router.get(
    "/health/database",
    summary="Database & pgvector Health Check",
    description="Performs an actual real-time query against PostgreSQL and tests pgvector extension availability.",
)
async def get_database_health():
    db_health = await check_database_health()
    is_ok = db_health.get("status") == "connected"

    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": is_ok,
            "data": db_health,
            "message": "Database is operational." if is_ok else "Database connection failed.",
        },
    )


@router.get(
    "/health/ai",
    summary="Google Gemini AI Health Check",
    description="Performs an actual real-time API call to Google Gemini to verify model responsiveness without exposing the API key.",
)
async def get_ai_health():
    ai_health = await ai_service.check_ai_health()
    is_ok = ai_health.get("status") == "connected"

    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "success": is_ok,
            "data": ai_health,
            "message": "Google Gemini AI is operational." if is_ok else "Google Gemini check failed or unconfigured.",
        },
    )

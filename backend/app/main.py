import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import check_database_health, engine
from app.core.exceptions import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.api.v1.api import api_router
from app.utils.logger import configure_logging

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle management context for startup diagnostics and graceful shutdown.
    Disposes database connection pools cleanly on exit.
    """
    # 1. Startup phase
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode.")
    logger.info(f"Frontend integration CORS origin: {settings.FRONTEND_URL}")

    # Check database connectivity during startup
    db_status = await check_database_health()
    if db_status.get("status") == "connected":
        logger.info(
            f"PostgreSQL connection verified. Version: {db_status.get('version', '').split(',')[0]} "
            f"| pgvector: {db_status.get('pgvector_enabled')}"
        )
    else:
        logger.warning(f"Initial database connection check: {db_status.get('error')}")

    # Yield control to the application
    yield

    # 2. Shutdown phase
    logger.info("Disposing database connection pool...")
    await engine.dispose()
    logger.info("Application shutdown complete.")


# OpenAPI tags metadata for structured documentation
openapi_tags = [
    {"name": "Health", "description": "Liveness, database, and Google Gemini AI connectivity diagnostics."},
    {"name": "Authentication", "description": "JWT authentication, registration, session refresh, and user tokens."},
    {"name": "Users", "description": "Team member profiles, skills, and directory."},
    {"name": "Projects", "description": "Isolated project handover workspaces and permissions."},
    {"name": "Project Members", "description": "Authorized member assignment and role governance."},
    {"name": "Documents", "description": "Multi-format knowledge document ingestion (PDF, DOCX, TXT, MD)."},
    {"name": "Document Processing", "description": "OCR, text extraction, semantic chunking, and embedding pipeline."},
    {"name": "Knowledge Handovers", "description": "AI-assisted handover synthesis, review workflow, and approval."},
    {"name": "Evidence & Citations", "description": "Traceable attribution linking AI claims directly to source passages."},
    {"name": "Knowledge Conflicts", "description": "Contradictory and missing information detection and resolution."},
    {"name": "Continuation Tasks", "description": "Incoming responsibilities, progress notes, and execution tracking."},
    {"name": "Notifications", "description": "In-app alerts, review requests, and transition deadlines."},
    {"name": "Exports", "description": "Formal handover packages exported to PDF, Markdown, and JSON."},
]

# FastAPI Application Factory
app = FastAPI(
    title=settings.APP_NAME,
    description="""
# AI-Powered Knowledge Handover Platform API

Production backend providing structured knowledge continuity during team transitions.

### Core Architecture Capabilities
- **Document Ingestion & AST Parsing**: Extracts text from PDF, DOCX, TXT, and Markdown files.
- **pgvector Vector Storage**: High-dimensional dense embeddings generated via Google Gemini.
- **RAG & Handover Synthesis**: Context-aware transition package generation.
- **Strict Evidence Attribution**: Every AI-generated claim is mapped to verified source chunks.
- **Human-in-the-Loop Approval**: Multi-stage review workflow (Draft -> Awaiting Review -> Approved).
- **Continuation & Task Governance**: Transition accountability and acknowledgement tracking.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# 1. Custom Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Register Centralized Exception Handlers
register_exception_handlers(app)

# 4. Mount API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
async def root():
    """Root platform health ping."""
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }

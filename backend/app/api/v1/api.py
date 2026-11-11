from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    users,
    projects,
    members,
    documents,
    handovers,
    evidence,
    conflicts,
    tasks,
    notifications,
    exports,
)

api_router = APIRouter()

# Core System & Health
api_router.include_router(health.router, tags=["Health"])

# Identity, Authentication & Members
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(members.router, prefix="/projects", tags=["Project Members"])

# Project Management & Workspaces
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

# Document Ingestion & Pipeline Processing
api_router.include_router(documents.project_documents_router, prefix="/projects", tags=["Project Documents"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Knowledge Handover Synthesis & Verification
api_router.include_router(handovers.project_handovers_router, prefix="/projects", tags=["Project Knowledge Handovers"])
api_router.include_router(handovers.router, prefix="/handovers", tags=["Knowledge Handovers"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence & Citations"])
api_router.include_router(conflicts.project_conflicts_router, prefix="/projects", tags=["Project Knowledge Conflicts"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["Knowledge Conflicts"])

# Continuation Tasks, Notifications & Exports
api_router.include_router(tasks.project_tasks_router, prefix="/projects", tags=["Project Tasks"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Continuation Tasks"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports"])

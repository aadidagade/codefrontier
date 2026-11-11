import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.authorization import require_project_membership
from app.models.user import User
from app.models.project import ProjectMember, ProjectMemberRole
from app.services.project_service import ProjectService
from app.schemas.common import ApiResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectOverviewResponse,
)
from app.schemas.search import ProjectSearchRequest, ProjectSearchResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Project Workspace",
    description="Initializes a new project workspace and automatically assigns the creator as ADMIN.",
)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.create_project(payload, current_user.id)
    return ApiResponse(
        data=project,
        message="Project workspace created successfully with ADMIN role assigned.",
    )


@router.get(
    "",
    response_model=ApiResponse[List[ProjectResponse]],
    summary="List User Projects",
    description="Retrieves all projects where the authenticated user is an authorized member.",
)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    projects = await service.list_user_projects(current_user.id)
    return ApiResponse(
        data=projects,
        message="Accessible projects retrieved.",
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectResponse],
    summary="Get Project Details",
    description="Retrieves project details. Protected by IDOR project membership check.",
)
async def get_project(
    project_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    return ApiResponse(
        data=project,
        message="Project details retrieved.",
    )


@router.get(
    "/{project_id}/overview",
    response_model=ApiResponse[ProjectOverviewResponse],
    summary="Get Project Overview & Live Metrics",
    description="Returns live statistics queried directly from PostgreSQL: documents, processing counts, handovers, reviews, conflicts, tasks, and members.",
)
async def get_project_overview(
    project_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    overview = await service.get_project_overview(project_id)
    return ApiResponse(
        data=overview,
        message="Project overview and live metrics retrieved.",
    )


@router.patch(
    "/{project_id}",
    response_model=ApiResponse[ProjectResponse],
    summary="Update Project Details (ADMIN Only)",
    description="Updates project metadata. Restricted strictly to project ADMIN members.",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    member: ProjectMember = Depends(require_project_membership(allowed_roles=[ProjectMemberRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    updated = await service.update_project(project_id, payload)
    return ApiResponse(
        data=updated,
        message="Project details updated.",
    )


@router.delete(
    "/{project_id}",
    response_model=ApiResponse[bool],
    summary="Delete Project Workspace (ADMIN Only)",
    description="Permanently deletes the project workspace and cascades to documents, handovers, and tasks. Restricted to ADMIN.",
)
async def delete_project(
    project_id: uuid.UUID,
    member: ProjectMember = Depends(require_project_membership(allowed_roles=[ProjectMemberRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    await service.delete_project(project_id)
    return ApiResponse(
        data=True,
        message="Project workspace deleted successfully.",
    )


@router.post(
    "/{project_id}/search",
    response_model=ApiResponse[ProjectSearchResponse],
    summary="Hybrid Semantic & Keyword Knowledge Search",
    description="Executes project-isolated hybrid retrieval combining Gemini embeddings, pgvector cosine similarity, and PostgreSQL full-text search with Reciprocal Rank Fusion.",
)
async def search_project(
    project_id: uuid.UUID,
    payload: ProjectSearchRequest,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    service = RAGService(db)
    chunks = await service.retrieve_evidence(
        project_id=project_id,
        query=payload.query,
        limit=payload.limit or 10,
        document_ids=payload.document_ids,
        similarity_threshold=payload.similarity_threshold,
        search_mode=payload.search_mode or "hybrid",
    )

    doc_names = sorted(list(set(ch.document_name for ch in chunks)))

    return ApiResponse(
        data=ProjectSearchResponse(
            query=payload.query,
            total_results=len(chunks),
            chunks=chunks,
            source_documents=doc_names,
        ),
        message=f"Retrieved {len(chunks)} relevant evidence chunk(s).",
    )


@router.post(
    "/{project_id}/qa",
    response_model=ApiResponse[dict],
    summary="Ask Question Grounded in Project Documentation",
    description="Answers questions strictly using project documentation evidence with source citations.",
)
async def ask_project_question(
    project_id: uuid.UUID,
    payload: dict,
    member: ProjectMember = Depends(require_project_membership()),
    db: AsyncSession = Depends(get_db),
):
    question = payload.get("question", "").strip()
    if not question:
        return ApiResponse(data={}, message="Question string 'question' is required.")

    service = RAGService(db)
    result = await service.answer_question(
        project_id=project_id,
        question=question,
        limit=payload.get("limit", 5),
        document_ids=payload.get("document_ids"),
    )
    return ApiResponse(
        data=result,
        message="Knowledge base answer generated with citations.",
    )


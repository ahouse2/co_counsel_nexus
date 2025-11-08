from fastapi import APIRouter, Depends

from ..models.api import (
    KnowledgeBookmarkRequest,
    KnowledgeBookmarkResponse,
    KnowledgeLessonDetailResponse,
    KnowledgeLessonListResponse,
    KnowledgeProgressUpdateRequest,
    KnowledgeProgressUpdateResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ..services.knowledge import KnowledgeService, get_knowledge_service
from ..security.authz import Principal
from ..security.dependencies import (
    authorize_knowledge_read,
    authorize_knowledge_write,
)

router = APIRouter()

@router.get("/knowledge/lessons", response_model=KnowledgeLessonListResponse)
def list_knowledge_lessons(
    _principal: Principal = Depends(authorize_knowledge_read),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeLessonListResponse:
    return service.list_lessons()


@router.get("/knowledge/lessons/{lesson_id}", response_model=KnowledgeLessonDetailResponse)
def get_knowledge_lesson(
    lesson_id: str,
    _principal: Principal = Depends(authorize_knowledge_read),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeLessonDetailResponse:
    return service.get_lesson(lesson_id)


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    request: KnowledgeSearchRequest,
    _principal: Principal = Depends(authorize_knowledge_read),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    return service.search(request.query)


@router.post("/knowledge/bookmarks", response_model=KnowledgeBookmarkResponse)
def add_knowledge_bookmark(
    request: KnowledgeBookmarkRequest,
    _principal: Principal = Depends(authorize_knowledge_write),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeBookmarkResponse:
    return service.add_bookmark(request.lesson_id)


@router.delete("/knowledge/bookmarks/{lesson_id}", response_model=KnowledgeBookmarkResponse)
def remove_knowledge_bookmark(
    lesson_id: str,
    _principal: Principal = Depends(authorize_knowledge_write),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeBookmarkResponse:
    return service.remove_bookmark(lesson_id)


@router.put("/knowledge/progress", response_model=KnowledgeProgressUpdateResponse)
def update_knowledge_progress(
    request: KnowledgeProgressUpdateRequest,
    _principal: Principal = Depends(authorize_knowledge_write),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeProgressUpdateResponse:
    return service.update_progress(request.lesson_id, request.progress)

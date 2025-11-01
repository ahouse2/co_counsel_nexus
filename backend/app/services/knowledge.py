from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Callable, Dict, Iterable, List, Sequence

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..config import get_settings
from ..services.graph import GraphService, get_graph_service
from ..security.authz import Principal
from ..storage.knowledge_store import KnowledgeProfileStore
from backend.ingestion.llama_index_factory import (
    configure_global_settings,
    create_embedding_model,
)
from backend.ingestion.settings import build_runtime_config


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_knowledge_search_counter = _meter.create_counter(
    "knowledge_search_total",
    unit="1",
    description="Knowledge hub searches executed",
)
_knowledge_search_duration = _meter.create_histogram(
    "knowledge_search_duration_ms",
    unit="ms",
    description="Latency of knowledge hub searches",
)
_knowledge_lessons_counter = _meter.create_counter(
    "knowledge_lessons_views_total",
    unit="1",
    description="Lesson listings and detail views",
)
_knowledge_bookmarks_counter = _meter.create_counter(
    "knowledge_bookmarks_total",
    unit="1",
    description="Bookmark toggles within the knowledge hub",
)
_knowledge_progress_counter = _meter.create_counter(
    "knowledge_progress_updates_total",
    unit="1",
    description="Knowledge progress updates",
)

try:  # pragma: no cover - optional dependency guard
    from llama_index.core import Document, VectorStoreIndex
except ModuleNotFoundError:  # pragma: no cover - fallback when llama-index missing
    Document = None  # type: ignore
    VectorStoreIndex = None  # type: ignore


@dataclass(frozen=True)
class KnowledgeLessonSection:
    id: str
    title: str
    markdown: str


@dataclass(frozen=True)
class KnowledgeLesson:
    lesson_id: str
    title: str
    summary: str
    tags: List[str]
    difficulty: str
    estimated_minutes: int
    jurisdictions: List[str]
    media: List[Dict[str, str]]
    sections: List[KnowledgeLessonSection]


@dataclass(frozen=True)
class KnowledgeSearchHit:
    lesson_id: str
    lesson_title: str
    section_id: str
    section_title: str
    snippet: str
    score: float
    tags: List[str]
    difficulty: str
    media: List[Dict[str, str]]


class KnowledgeService:
    """Expose curated legal playbooks via LlamaIndex-backed search."""

    def __init__(
        self,
        *,
        profile_store: KnowledgeProfileStore | None = None,
        graph_service: GraphService | None = None,
        graph_service_factory: Callable[[], GraphService] | None = None,
    ) -> None:
        self.settings = get_settings()
        self.profile_store = profile_store or KnowledgeProfileStore(self.settings.knowledge_progress_path)
        self._lessons = self._load_lessons()
        self._filters = self._compute_filters(self._lessons.values())
        self._runtime = build_runtime_config(self.settings)
        configure_global_settings(self._runtime)
        self._embedding_model = create_embedding_model(self._runtime.embedding)
        self._index_lock = Lock()
        self._index = self._build_index(self._lessons)
        self._graph_service: GraphService | None = graph_service
        if graph_service_factory is None and graph_service is None:
            graph_service_factory = get_graph_service
        self._graph_service_factory: Callable[[], GraphService] | None = graph_service_factory

    @staticmethod
    def _slugify(value: str) -> str:
        base = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
        return base or "section"

    def _resolve_graph_service(self) -> GraphService | None:
        if self._graph_service is not None:
            return self._graph_service
        if self._graph_service_factory is None:
            return None
        try:
            service = self._graph_service_factory()
        except Exception:  # pragma: no cover - optional dependency guard
            self._graph_service_factory = None
            return None
        self._graph_service = service
        return service

    @property
    def graph_service(self) -> GraphService | None:
        return self._resolve_graph_service()

    def _load_lessons(self) -> Dict[str, KnowledgeLesson]:
        catalog_path = Path(self.settings.knowledge_catalog_path)
        if not catalog_path.exists():
            raise FileNotFoundError(f"Knowledge catalog {catalog_path} missing")
        catalog_payload = json.loads(catalog_path.read_text())
        lessons_payload = catalog_payload.get("lessons", [])
        if not isinstance(lessons_payload, Sequence):
            raise ValueError("Knowledge catalog malformed: `lessons` must be a list")
        lessons: Dict[str, KnowledgeLesson] = {}
        catalog_dir = catalog_path.parent
        for entry in lessons_payload:
            if not isinstance(entry, dict):
                continue
            lesson_id = str(entry.get("id", "")).strip()
            if not lesson_id:
                raise ValueError("Lesson entry missing `id`")
            title = str(entry.get("title", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            tags = [str(tag).strip() for tag in entry.get("tags", []) if str(tag).strip()]
            difficulty = str(entry.get("difficulty", "")).strip() or "unspecified"
            estimated_minutes = int(entry.get("estimated_minutes", 0) or 0)
            jurisdictions = [str(j).strip() for j in entry.get("jurisdictions", []) if str(j).strip()]
            media_payload = entry.get("media", [])
            media: List[Dict[str, str]] = []
            if isinstance(media_payload, Iterable):
                for item in media_payload:
                    if not isinstance(item, dict):
                        continue
                    media.append(
                        {
                            "type": str(item.get("type", "link")),
                            "title": str(item.get("title", "")),
                            "url": str(item.get("url", "")),
                            "provider": str(item.get("provider", "")),
                        }
                    )
            content_path_value = str(entry.get("content_path", "")).strip()
            if not content_path_value:
                raise ValueError(f"Lesson {lesson_id} missing `content_path`")
            content_path = Path(content_path_value)
            if not content_path.is_absolute():
                content_path = (catalog_dir / content_path).resolve()
            if not content_path.exists():
                raise FileNotFoundError(f"Lesson content not found at {content_path}")
            sections = self._parse_markdown_sections(content_path.read_text(encoding="utf-8"))
            lessons[lesson_id] = KnowledgeLesson(
                lesson_id=lesson_id,
                title=title or lesson_id.replace("-", " ").title(),
                summary=summary,
                tags=tags,
                difficulty=difficulty,
                estimated_minutes=estimated_minutes,
                jurisdictions=jurisdictions,
                media=media,
                sections=sections,
            )
        return lessons

    def _parse_markdown_sections(self, markdown_text: str) -> List[KnowledgeLessonSection]:
        header_pattern = re.compile(r"^## +(.+)$", re.MULTILINE)
        matches = list(header_pattern.finditer(markdown_text))
        sections: List[KnowledgeLessonSection] = []
        if not matches:
            section_id = self._slugify("Overview")
            sections.append(KnowledgeLessonSection(section_id, "Overview", markdown_text.strip()))
            return sections
        for index, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
            body = markdown_text[start:end].strip()
            section_id = self._slugify(title)
            sections.append(KnowledgeLessonSection(section_id, title, body))
        return sections

    def _build_index(self, lessons: Dict[str, KnowledgeLesson]):
        if Document is None or VectorStoreIndex is None:
            return None
        documents: List[Document] = []
        for lesson in lessons.values():
            for section in lesson.sections:
                metadata = {
                    "lesson_id": lesson.lesson_id,
                    "lesson_title": lesson.title,
                    "section_id": section.id,
                    "section_title": section.title,
                    "tags": lesson.tags,
                    "difficulty": lesson.difficulty,
                    "media_types": sorted({item.get("type", "link") for item in lesson.media}),
                }
                documents.append(
                    Document(
                        text=section.markdown,
                        metadata=metadata,
                        id_=f"{lesson.lesson_id}::{section.id}",
                    )
                )
        if not documents:
            return None
        return VectorStoreIndex.from_documents(documents, embed_model=self._embedding_model)

    @staticmethod
    def _compute_filters(lessons: Iterable[KnowledgeLesson]) -> Dict[str, List[str]]:
        tags: set[str] = set()
        difficulties: set[str] = set()
        media_types: set[str] = set()
        for lesson in lessons:
            tags.update(lesson.tags)
            difficulties.add(lesson.difficulty)
            media_types.update(item.get("type", "link") for item in lesson.media)
        return {
            "tags": sorted(tags),
            "difficulty": sorted(difficulties),
            "media_types": sorted(media_types),
        }

    def _user_key(self, principal: Principal) -> str:
        return f"{principal.tenant_id}:{principal.subject}".lower()

    def _profile(self, principal: Principal):
        return self.profile_store.get_profile(self._user_key(principal))

    @staticmethod
    def _snippet(text: str, query: str, length: int = 320) -> str:
        if not text:
            return ""
        lowered = text.lower()
        query_tokens = [token for token in re.split(r"\W+", query.lower()) if token]
        best_index = 0
        for token in query_tokens:
            idx = lowered.find(token)
            if idx != -1:
                best_index = idx
                break
        start = max(best_index - length // 4, 0)
        end = min(start + length, len(text))
        snippet = text[start:end].strip()
        return snippet or text[:length].strip()

    def list_lessons(self, principal: Principal):
        with _tracer.start_as_current_span("knowledge.list_lessons") as span:
            if principal and principal.tenant_id:
                span.set_attribute("knowledge.tenant_id", principal.tenant_id)
            profile = self._profile(principal)
            lessons_payload: List[Dict[str, object]] = []
            for lesson in self._lessons.values():
                progress_record = profile.progress.get(lesson.lesson_id)
                completed_sections = (
                    sorted(progress_record.completed_sections) if progress_record else []
                )
                total_sections = len(lesson.sections)
                percent = 0.0
                if total_sections:
                    percent = min(1.0, len(completed_sections) / total_sections)
                last_viewed = (
                    progress_record.last_viewed_at.isoformat()
                    if progress_record and progress_record.last_viewed_at
                    else None
                )
                lessons_payload.append(
                    {
                        "lesson_id": lesson.lesson_id,
                        "title": lesson.title,
                        "summary": lesson.summary,
                        "tags": lesson.tags,
                        "difficulty": lesson.difficulty,
                        "estimated_minutes": lesson.estimated_minutes,
                        "jurisdictions": lesson.jurisdictions,
                        "media": lesson.media,
                        "progress": {
                            "completed_sections": completed_sections,
                            "total_sections": total_sections,
                            "percent_complete": percent,
                            "last_viewed_at": last_viewed,
                        },
                        "bookmarked": lesson.lesson_id in profile.bookmarks,
                    }
                )
            payload = {
                "lessons": sorted(lessons_payload, key=lambda item: item["title"]),
                "filters": self._filters,
            }
            _knowledge_lessons_counter.add(1, attributes={"action": "list"})
            span.set_attribute("knowledge.lessons", len(payload["lessons"]))
            span.set_status(Status(StatusCode.OK))
            return payload
    def get_lesson(self, lesson_id: str, principal: Principal) -> Dict[str, object]:
        with _tracer.start_as_current_span("knowledge.get_lesson") as span:
            span.set_attribute("knowledge.lesson_id", lesson_id)
            if principal and principal.tenant_id:
                span.set_attribute("knowledge.tenant_id", principal.tenant_id)
            lesson = self._lessons.get(lesson_id)
            if not lesson:
                span.set_status(Status(StatusCode.ERROR, description="Lesson not found"))
                raise KeyError(f"Lesson {lesson_id} not found")
            profile = self._profile(principal)
            progress_record = profile.progress.get(lesson_id)
            completed_sections = progress_record.completed_sections if progress_record else set()
            total_sections = len(lesson.sections)
            percent = 0.0
            if total_sections:
                percent = min(1.0, len(completed_sections) / total_sections)
            last_viewed = (
                progress_record.last_viewed_at.isoformat()
                if progress_record and progress_record.last_viewed_at
                else None
            )
            payload = {
                "lesson_id": lesson.lesson_id,
                "title": lesson.title,
                "summary": lesson.summary,
                "tags": lesson.tags,
                "difficulty": lesson.difficulty,
                "estimated_minutes": lesson.estimated_minutes,
                "jurisdictions": lesson.jurisdictions,
                "media": lesson.media,
                "sections": [
                    {
                        "id": section.id,
                        "title": section.title,
                        "content": section.markdown,
                        "completed": section.id in completed_sections,
                    }
                    for section in lesson.sections
                ],
                "progress": {
                    "completed_sections": sorted(completed_sections),
                    "total_sections": total_sections,
                    "percent_complete": percent,
                    "last_viewed_at": last_viewed,
                },
                "bookmarked": lesson_id in profile.bookmarks,
            }
            payload["strategy_brief"] = None
            focus_candidates = [lesson.lesson_id, *lesson.tags, *lesson.jurisdictions]
            graph_service = self._resolve_graph_service()
            if graph_service is not None:
                try:
                    strategy_brief = graph_service.synthesize_strategy_brief(focus_candidates)
                    payload["strategy_brief"] = strategy_brief.to_dict()
                except Exception:  # pragma: no cover - defensive guard for optional graph features
                    payload["strategy_brief"] = None
            _knowledge_lessons_counter.add(1, attributes={"action": "detail"})
            span.set_attribute("knowledge.sections", len(lesson.sections))
            span.set_status(Status(StatusCode.OK))
            return payload
    def record_progress(self, lesson_id: str, section_id: str, completed: bool, principal: Principal) -> Dict[str, object]:
        with _tracer.start_as_current_span("knowledge.record_progress") as span:
            span.set_attribute("knowledge.lesson_id", lesson_id)
            span.set_attribute("knowledge.section_id", section_id)
            span.set_attribute("knowledge.completed", completed)
            if principal and principal.tenant_id:
                span.set_attribute("knowledge.tenant_id", principal.tenant_id)
            if lesson_id not in self._lessons:
                span.set_status(Status(StatusCode.ERROR, description="Lesson not found"))
                raise KeyError(f"Lesson {lesson_id} not found")
            lesson = self._lessons[lesson_id]
            valid_sections = {section.id for section in lesson.sections}
            if section_id not in valid_sections:
                span.set_status(Status(StatusCode.ERROR, description="Section not found"))
                raise KeyError(f"Section {section_id} not part of lesson {lesson_id}")
            record = self.profile_store.record_progress(
                self._user_key(principal),
                lesson_id,
                section_id,
                completed=completed,
            )
            total_sections = len(lesson.sections)
            percent = 0.0
            if total_sections:
                percent = min(1.0, len(record.completed_sections) / total_sections)
            payload = {
                "lesson_id": lesson_id,
                "section_id": section_id,
                "completed_sections": sorted(record.completed_sections),
                "total_sections": total_sections,
                "percent_complete": percent,
                "last_viewed_at": record.last_viewed_at.isoformat() if record.last_viewed_at else None,
            }
            _knowledge_progress_counter.add(
                1,
                attributes={
                    "action": "progress",
                    "completed": bool(completed),
                },
            )
            span.set_status(Status(StatusCode.OK))
            return payload
    def set_bookmark(self, lesson_id: str, bookmarked: bool, principal: Principal) -> Dict[str, object]:
        with _tracer.start_as_current_span("knowledge.set_bookmark") as span:
            span.set_attribute("knowledge.lesson_id", lesson_id)
            span.set_attribute("knowledge.bookmarked", bookmarked)
            if principal and principal.tenant_id:
                span.set_attribute("knowledge.tenant_id", principal.tenant_id)
            if lesson_id not in self._lessons:
                span.set_status(Status(StatusCode.ERROR, description="Lesson not found"))
                raise KeyError(f"Lesson {lesson_id} not found")
            bookmarks = self.profile_store.set_bookmark(
                self._user_key(principal), lesson_id, bookmarked
            )
            payload = {
                "lesson_id": lesson_id,
                "bookmarked": lesson_id in bookmarks,
                "bookmarks": sorted(bookmarks),
            }
            _knowledge_bookmarks_counter.add(
                1,
                attributes={
                    "action": "bookmark",
                    "bookmarked": bool(bookmarked),
                },
            )
            span.set_status(Status(StatusCode.OK))
            return payload

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: Dict[str, Sequence[str]] | None = None,
        principal: Principal | None = None,
    ) -> Dict[str, object]:
        if not query.strip():
            return {"results": [], "elapsed_ms": 0.0}

        with _tracer.start_as_current_span("knowledge.search") as span:
            span.set_attribute("knowledge.query_length", len(query))
            span.set_attribute("knowledge.limit", limit)
            if principal and principal.tenant_id:
                span.set_attribute("knowledge.tenant_id", principal.tenant_id)

            start = perf_counter()
            applied_filters = {
                key: {value.lower() for value in values}
                for key, values in (filters or {}).items()
                if values
            }
            hits: List[KnowledgeSearchHit] = []
            if self._index is not None:
                with self._index_lock:
                    retriever = self._index.as_retriever(similarity_top_k=max(5, limit * 2))
                    retrieved = retriever.retrieve(query)
                for node in retrieved:
                    metadata = getattr(node, "metadata", {}) or {}
                    lesson_id = metadata.get("lesson_id")
                    section_id = metadata.get("section_id")
                    if not lesson_id or not section_id:
                        continue
                    if not self._match_filters(metadata, applied_filters):
                        continue
                    lesson = self._lessons.get(lesson_id)
                    if not lesson:
                        continue
                    section = next((item for item in lesson.sections if item.id == section_id), None)
                    if section is None:
                        continue
                    score = float(getattr(node, "score", 0.0) or 0.0)
                    hits.append(
                        KnowledgeSearchHit(
                            lesson_id=lesson.lesson_id,
                            lesson_title=lesson.title,
                            section_id=section.id,
                            section_title=section.title,
                            snippet=self._snippet(section.markdown, query),
                            score=score,
                            tags=lesson.tags,
                            difficulty=lesson.difficulty,
                            media=lesson.media,
                        )
                    )
                    if len(hits) >= limit:
                        break
            else:
                query_tokens = [token for token in re.split(r"\W+", query.lower()) if token]
                for lesson in self._lessons.values():
                    for section in lesson.sections:
                        metadata = {
                            "tags": [tag.lower() for tag in lesson.tags],
                            "difficulty": lesson.difficulty.lower(),
                            "media_types": [item.get("type", "link").lower() for item in lesson.media],
                        }
                        if not self._match_filters(metadata, applied_filters):
                            continue
                        text = section.markdown.lower()
                        overlap = sum(text.count(token) for token in query_tokens) or 0
                        if overlap == 0:
                            continue
                        hits.append(
                            KnowledgeSearchHit(
                                lesson_id=lesson.lesson_id,
                                lesson_title=lesson.title,
                                section_id=section.id,
                                section_title=section.title,
                                snippet=self._snippet(section.markdown, query),
                                score=float(overlap),
                                tags=lesson.tags,
                                difficulty=lesson.difficulty,
                                media=lesson.media,
                            )
                        )

            elapsed = (perf_counter() - start) * 1000.0
            hits.sort(key=lambda hit: hit.score, reverse=True)
            trimmed = hits[:limit]
            attributes = {"has_index": self._index is not None, "filters": bool(filters)}
            _knowledge_search_duration.record(elapsed, attributes=attributes)
            _knowledge_search_counter.add(1, attributes=attributes)
            span.set_attribute("knowledge.elapsed_ms", elapsed)
            span.set_attribute("knowledge.results", len(trimmed))
            span.set_status(Status(StatusCode.OK))

        results = [
            {
                "lesson_id": hit.lesson_id,
                "lesson_title": hit.lesson_title,
                "section_id": hit.section_id,
                "section_title": hit.section_title,
                "snippet": hit.snippet,
                "score": hit.score,
                "tags": hit.tags,
                "difficulty": hit.difficulty,
                "media": hit.media,
            }
            for hit in trimmed
        ]
        return {"results": results, "elapsed_ms": elapsed, "applied_filters": applied_filters}
    @staticmethod
    def _match_filters(metadata: Dict[str, object], filters: Dict[str, set[str]]) -> bool:
        if not filters:
            return True
        for key, values in filters.items():
            if not values:
                continue
            if key == "tags":
                tags = {str(tag).lower() for tag in metadata.get("tags", [])}
                if not tags & values:
                    return False
            elif key == "difficulty":
                difficulty = str(metadata.get("difficulty", "")).lower()
                if difficulty not in values:
                    return False
            elif key == "media_types":
                media_types = {str(item).lower() for item in metadata.get("media_types", [])}
                if not media_types & values:
                    return False
        return True


@lru_cache(maxsize=1)
def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService()

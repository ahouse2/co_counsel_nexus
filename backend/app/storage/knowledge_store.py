from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, MutableMapping, Set

from ..utils.storage import atomic_write_json, read_json


@dataclass(frozen=True)
class LessonProgressRecord:
    lesson_id: str
    completed_sections: Set[str]
    last_viewed_at: datetime | None


@dataclass(frozen=True)
class KnowledgeProfile:
    user_key: str
    progress: Dict[str, LessonProgressRecord]
    bookmarks: Set[str]


class KnowledgeProfileStore:
    """File-backed persistence for lesson progress and bookmarks."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        if not self.path.exists():
            atomic_write_json(
                self.path,
                {
                    "version": 1,
                    "users": {},
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    def _load_state(self) -> MutableMapping[str, object]:
        if not self.path.exists():
            return {"version": 1, "users": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
        try:
            payload = read_json(self.path)
        except (OSError, ValueError):
            return {"version": 1, "users": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
        if not isinstance(payload, dict):
            return {"version": 1, "users": {}, "updated_at": datetime.now(timezone.utc).isoformat()}
        payload.setdefault("users", {})
        return payload

    def _write_state(self, payload: MutableMapping[str, object]) -> None:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(self.path, payload)

    @staticmethod
    def _normalise_key(user_key: str) -> str:
        return user_key.strip().lower()

    def get_profile(self, user_key: str) -> KnowledgeProfile:
        key = self._normalise_key(user_key)
        with self._lock:
            payload = self._load_state()
            users = payload.get("users", {})
            user_state = users.get(key, {}) if isinstance(users, dict) else {}
            progress_map: Dict[str, LessonProgressRecord] = {}
            progress_payload = user_state.get("progress", {}) if isinstance(user_state, dict) else {}
            if isinstance(progress_payload, dict):
                for lesson_id, lesson_payload in progress_payload.items():
                    if not isinstance(lesson_payload, dict):
                        continue
                    completed = lesson_payload.get("completed_sections", [])
                    sections: Set[str] = set()
                    if isinstance(completed, Iterable):
                        sections = {str(section) for section in completed}
                    last_viewed = lesson_payload.get("last_viewed_at")
                    viewed_at = None
                    if isinstance(last_viewed, str):
                        try:
                            viewed_at = datetime.fromisoformat(last_viewed)
                        except ValueError:
                            viewed_at = None
                    progress_map[lesson_id] = LessonProgressRecord(
                        lesson_id=lesson_id,
                        completed_sections=sections,
                        last_viewed_at=viewed_at,
                    )
            bookmarks_payload = user_state.get("bookmarks", []) if isinstance(user_state, dict) else []
            bookmarks: Set[str] = set()
            if isinstance(bookmarks_payload, Iterable):
                bookmarks = {str(entry) for entry in bookmarks_payload}
            return KnowledgeProfile(user_key=key, progress=progress_map, bookmarks=bookmarks)

    def record_progress(
        self,
        user_key: str,
        lesson_id: str,
        section_id: str,
        *,
        completed: bool,
    ) -> LessonProgressRecord:
        key = self._normalise_key(user_key)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            payload = self._load_state()
            users = payload.setdefault("users", {})
            if not isinstance(users, dict):
                users = {}
                payload["users"] = users
            user_state = users.setdefault(key, {"progress": {}, "bookmarks": []})
            if not isinstance(user_state, dict):
                user_state = {"progress": {}, "bookmarks": []}
                users[key] = user_state
            progress_payload = user_state.setdefault("progress", {})
            if not isinstance(progress_payload, dict):
                progress_payload = {}
                user_state["progress"] = progress_payload
            entry = progress_payload.setdefault(
                lesson_id,
                {"completed_sections": [], "last_viewed_at": now},
            )
            if not isinstance(entry, dict):
                entry = {"completed_sections": [], "last_viewed_at": now}
                progress_payload[lesson_id] = entry
            completed_sections = entry.setdefault("completed_sections", [])
            if not isinstance(completed_sections, list):
                completed_sections = []
                entry["completed_sections"] = completed_sections
            section_id = str(section_id)
            if completed and section_id not in completed_sections:
                completed_sections.append(section_id)
            if not completed:
                entry["completed_sections"] = [value for value in completed_sections if value != section_id]
            entry["last_viewed_at"] = now
            self._write_state(payload)
            return LessonProgressRecord(
                lesson_id=lesson_id,
                completed_sections=set(entry["completed_sections"]),
                last_viewed_at=datetime.fromisoformat(now),
            )

    def set_bookmark(self, user_key: str, lesson_id: str, bookmarked: bool) -> Set[str]:
        key = self._normalise_key(user_key)
        with self._lock:
            payload = self._load_state()
            users = payload.setdefault("users", {})
            if not isinstance(users, dict):
                users = {}
                payload["users"] = users
            user_state = users.setdefault(key, {"progress": {}, "bookmarks": []})
            if not isinstance(user_state, dict):
                user_state = {"progress": {}, "bookmarks": []}
                users[key] = user_state
            bookmarks_payload = user_state.setdefault("bookmarks", [])
            if not isinstance(bookmarks_payload, list):
                bookmarks_payload = []
                user_state["bookmarks"] = bookmarks_payload
            lesson_id = str(lesson_id)
            if bookmarked and lesson_id not in bookmarks_payload:
                bookmarks_payload.append(lesson_id)
            if not bookmarked:
                user_state["bookmarks"] = [value for value in bookmarks_payload if value != lesson_id]
            self._write_state(payload)
            final = user_state.get("bookmarks", [])
            if isinstance(final, list):
                return {str(entry) for entry in final}
            return set()

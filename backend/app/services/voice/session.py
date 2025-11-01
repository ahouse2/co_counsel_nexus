from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Literal

from ...utils.storage import atomic_write_json, read_json, sanitise_identifier


@dataclass(slots=True)
class VoiceTurn:
    """Voice conversation turn persisted alongside agent state."""

    speaker: str
    text: str
    sentiment: float
    sentiment_label: str
    pace: float
    created_at: datetime

    def to_json(self) -> Dict[str, object]:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "sentiment": self.sentiment,
            "sentiment_label": self.sentiment_label,
            "pace": self.pace,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, object]) -> "VoiceTurn":
        created_at_raw = payload.get("created_at")
        if not isinstance(created_at_raw, str):
            raise ValueError("Voice turn payload missing created_at")
        created_at = datetime.fromisoformat(created_at_raw)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return cls(
            speaker=str(payload.get("speaker", "assistant")),
            text=str(payload.get("text", "")),
            sentiment=float(payload.get("sentiment", 0.0)),
            sentiment_label=str(payload.get("sentiment_label", "neutral")),
            pace=float(payload.get("pace", 1.0)),
            created_at=created_at,
        )


@dataclass(slots=True)
class VoiceSession:
    """Persisted voice session metadata."""

    session_id: str
    thread_id: str
    case_id: str
    persona_id: str
    transcript: str
    sentiment_label: str
    sentiment_score: float
    pace: float
    persona_directive: Dict[str, object] = field(default_factory=dict)
    sentiment_arc: List[Dict[str, object]] = field(default_factory=list)
    persona_shifts: List[Dict[str, object]] = field(default_factory=list)
    translation: Dict[str, object] = field(default_factory=dict)
    segments: List[Dict[str, object]] = field(default_factory=list)
    turns: List[VoiceTurn] = field(default_factory=list)
    input_audio_path: Path | None = None
    response_audio_path: Path | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> Dict[str, object]:
        return {
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "case_id": self.case_id,
            "persona_id": self.persona_id,
            "transcript": self.transcript,
            "sentiment_label": self.sentiment_label,
            "sentiment_score": self.sentiment_score,
            "pace": self.pace,
            "persona_directive": dict(self.persona_directive),
            "sentiment_arc": list(self.sentiment_arc),
            "persona_shifts": list(self.persona_shifts),
            "translation": dict(self.translation),
            "segments": list(self.segments),
            "turns": [turn.to_json() for turn in self.turns],
            "input_audio_path": str(self.input_audio_path) if self.input_audio_path else None,
            "response_audio_path": str(self.response_audio_path) if self.response_audio_path else None,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "updated_at": self.updated_at.astimezone(timezone.utc).isoformat(),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, object]) -> "VoiceSession":
        created_at = cls._parse_ts(payload.get("created_at"))
        updated_at = cls._parse_ts(payload.get("updated_at"))
        turns_payload = payload.get("turns", [])
        if not isinstance(turns_payload, list):
            raise ValueError("Voice session turns must be a list")
        turns = [VoiceTurn.from_json(entry) for entry in turns_payload]
        segments_payload = payload.get("segments", [])
        if not isinstance(segments_payload, list):
            raise ValueError("Voice session segments must be a list")
        input_path = payload.get("input_audio_path")
        response_path = payload.get("response_audio_path")
        return cls(
            session_id=str(payload.get("session_id")),
            thread_id=str(payload.get("thread_id")),
            case_id=str(payload.get("case_id")),
            persona_id=str(payload.get("persona_id")),
            transcript=str(payload.get("transcript", "")),
            sentiment_label=str(payload.get("sentiment_label", "neutral")),
            sentiment_score=float(payload.get("sentiment_score", 0.0)),
            pace=float(payload.get("pace", 1.0)),
            persona_directive=dict(payload.get("persona_directive", {})),
            sentiment_arc=[dict(entry) for entry in payload.get("sentiment_arc", [])],
            persona_shifts=[dict(entry) for entry in payload.get("persona_shifts", [])],
            translation=dict(payload.get("translation", {})),
            segments=[dict(segment) for segment in segments_payload],
            turns=turns,
            input_audio_path=Path(input_path) if input_path else None,
            response_audio_path=Path(response_path) if response_path else None,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _parse_ts(value: object) -> datetime:
        if not isinstance(value, str):
            return datetime.now(timezone.utc)
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class VoiceSessionStore:
    """Filesystem-backed persistence for voice sessions."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        safe_id = sanitise_identifier(session_id)
        root_resolved = self.root.resolve()
        path = (root_resolved / safe_id).resolve()
        if not str(path).startswith(str(root_resolved)):
            raise ValueError("Session path escapes root")
        return path

    def _ensure_session_dir(self, session_id: str) -> Path:
        path = self._session_path(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(
        self,
        session: VoiceSession,
        *,
        input_audio: bytes,
        response_audio: bytes,
    ) -> VoiceSession:
        session_dir = self._ensure_session_dir(session.session_id)
        input_path = session_dir / "input.wav"
        response_path = session_dir / "response.wav"
        input_path.write_bytes(input_audio)
        response_path.write_bytes(response_audio)
        session.input_audio_path = Path("input.wav")
        session.response_audio_path = Path("response.wav")
        session.updated_at = datetime.now(timezone.utc)
        atomic_write_json(session_dir / "session.json", session.to_json())
        return session

    def load(self, session_id: str) -> VoiceSession:
        session_dir = self._session_path(session_id)
        payload = read_json(session_dir / "session.json")
        return VoiceSession.from_json(payload)

    def update_metadata(self, session: VoiceSession) -> None:
        session_dir = self._ensure_session_dir(session.session_id)
        session.updated_at = datetime.now(timezone.utc)
        atomic_write_json(session_dir / "session.json", session.to_json())

    def stream_audio(
        self, session_id: str, kind: Literal["input", "response"], *, chunk_size: int = 4096
    ) -> Iterator[bytes]:
        session = self.load(session_id)
        path_fragment: Path | None
        if kind == "input":
            path_fragment = session.input_audio_path
        else:
            path_fragment = session.response_audio_path
        if path_fragment is None:
            raise FileNotFoundError(f"Session {session_id} has no {kind} audio payload")
        file_path = self._session_path(session_id) / path_fragment
        with file_path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                yield chunk


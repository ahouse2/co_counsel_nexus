from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import numpy as np
import pytest

from backend.app.config import Settings
from backend.app.services.voice.adapters import TranscriptionResult, TranscriptionSegment
from backend.app.services.voice.sentiment import SentimentResult
from backend.app.services.voice.service import VoiceService
from backend.app.services.voice.session import VoiceSessionStore
from backend.app.storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord


class StubTranscriber:
    def __init__(self, text: str) -> None:
        self._result = TranscriptionResult(
            text=text,
            language="en",
            duration=1.0,
            segments=(
                TranscriptionSegment(start=0.0, end=1.0, text=text, confidence=0.99),
            ),
        )

    def transcribe(self, audio_payload: bytes, *, language: str | None = None) -> TranscriptionResult:
        assert audio_payload, "audio payload must not be empty"
        return self._result


class StubSentiment:
    def analyse(self, text: str) -> SentimentResult:
        return SentimentResult(label="positive", score=0.82, pace=1.08)


class StubSynthesizer:
    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate

    def available_speakers(self):
        return ("p273", "p270")

    def synthesize(self, text: str, *, speaker_id: str | None, speed: float, sample_rate: int | None = None) -> bytes:
        assert text
        sr = sample_rate or self.sample_rate
        duration = 0.05
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        buffer = BytesIO()
        import soundfile as sf

        sf.write(buffer, tone, sr, format="WAV")
        return buffer.getvalue()


class StubAgentsService:
    def __init__(self, memory_store: AgentMemoryStore) -> None:
        self.memory_store = memory_store
        self._last_payload: Dict[str, Any] | None = None

    def run_case(self, *, case_id: str, question: str, principal=None) -> Dict[str, Any]:
        thread_id = f"thread-{uuid4().hex}"
        payload = {
            "thread_id": thread_id,
            "case_id": case_id,
            "question": question,
            "final_answer": f"Summary for: {question}",
            "turns": [
                {
                    "role": "research",
                    "output": {"answer": f"Summary for: {question}"},
                }
            ],
            "memory": {},
            "telemetry": {},
        }
        record = AgentThreadRecord(thread_id=thread_id, payload=payload)
        self.memory_store.write(record)
        self._last_payload = payload
        return payload

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        return self.memory_store.read(thread_id)


@pytest.fixture()
def voice_service(tmp_path: Path) -> VoiceService:
    settings = Settings()
    settings.voice_sessions_dir = tmp_path / "voice_sessions"
    settings.voice_cache_dir = tmp_path / "voice_cache"
    settings.agent_threads_dir = tmp_path / "threads"
    settings.document_store_dir = tmp_path / "docs"
    settings.job_store_dir = tmp_path / "jobs"
    settings.billing_usage_path = tmp_path / "billing" / "usage.json"
    settings.audit_log_path = tmp_path / "audit.log"
    settings.prepare_directories()
    memory_store = AgentMemoryStore(settings.agent_threads_dir)
    session_store = VoiceSessionStore(settings.voice_sessions_dir)
    service = VoiceService(
        settings=settings,
        transcriber=StubTranscriber("How is the compliance case progressing?"),
        synthesizer=StubSynthesizer(settings.voice_sample_rate),
        sentiment=StubSentiment(),
        session_store=session_store,
        agents_service=StubAgentsService(memory_store),
    )
    return service


def test_voice_service_round_trip(voice_service: VoiceService) -> None:
    payload = b"synthetic audio"
    outcome = voice_service.create_session(
        case_id="CASE-001",
        audio_payload=payload,
        persona_id="aurora",
        principal=None,
    )
    session = outcome.session
    assert session.transcript.startswith("How is the compliance")
    assert session.persona_id == "aurora"
    assert session.sentiment_label == "positive"
    assert pytest.approx(session.sentiment_score, rel=1e-3) == 0.82
    assert session.input_audio_path == Path("input.wav")
    stored_session = voice_service.sessions.load(session.session_id)
    assert stored_session.response_audio_path == Path("response.wav")
    stream = list(voice_service.stream_response_audio(session.session_id))
    assert stream, "Streamed audio should contain chunks"
    thread_payload = voice_service.agents_service.get_thread(session.thread_id)
    voice_memory = thread_payload["memory"]["voice_sessions"][session.session_id]
    assert voice_memory["persona_id"] == "aurora"
    assert voice_memory["sentiment_label"] == "positive"
    assert voice_memory["segments"][0]["text"].startswith("How is the")

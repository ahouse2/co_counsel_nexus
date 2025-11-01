from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import MethodType
from typing import Any, Dict
from uuid import uuid4

import numpy as np
import pytest

from backend.app.config import Settings
from backend.app.services.voice.adapters import TranscriptionResult, TranscriptionSegment
from backend.app.services.voice.sentiment import SentimentResult
from backend.app.services.voice.service import TranslationResult, VoiceService
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
        self.last_text: str | None = None

    def available_speakers(self):
        return ("p273", "p270")

    def synthesize(self, text: str, *, speaker_id: str | None, speed: float, sample_rate: int | None = None) -> bytes:
        assert text
        self.last_text = text
        sr = sample_rate or self.sample_rate
        duration = 0.05
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        buffer = BytesIO()
        import soundfile as sf

        sf.write(buffer, tone, sr, format="WAV")
        return buffer.getvalue()


class StubTranslator:
    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def translate(
        self,
        text: str,
        *,
        source_language: str,
        target_language: str,
        glossary: Dict[str, str] | None = None,
    ) -> TranslationResult:
        payload = {
            "text": text,
            "source": source_language,
            "target": target_language,
            "glossary": dict(glossary or {}),
        }
        self.calls.append(payload)
        translated = text
        applied: Dict[str, str] = {}
        for key, value in (glossary or {}).items():
            if key.lower() in translated.lower():
                translated = translated.replace(key, value)
                applied[key] = value
        if target_language != source_language:
            translated_text = f"{translated} [{target_language}]"
            bilingual = f"{translated_text} / {text}"
        else:
            translated_text = translated
            bilingual = translated
        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            translated_text=translated_text,
            bilingual_text=bilingual,
            applied_glossary=applied,
        )


class StubGlossary:
    def resolve(self, *, case_id: str, persona_id: str) -> Dict[str, str]:
        return {
            "compliance": "cumplimiento",
            "case": "caso",
        }


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
    settings.voice_personas["aurora"].update(
        {
            "bilingual": True,
            "secondary_language": "es",
            "glossary": {"compliance": "cumplimiento"},
        }
    )
    translator = StubTranslator()
    glossary = StubGlossary()
    service = VoiceService(
        settings=settings,
        transcriber=StubTranscriber("How is the compliance case progressing?"),
        synthesizer=StubSynthesizer(settings.voice_sample_rate),
        sentiment=StubSentiment(),
        session_store=session_store,
        agents_service=StubAgentsService(memory_store),
        translator=translator,
        glossary=glossary,
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
    assert session.translation["target_language"] == "es"
    assert "cumplimiento" in session.translation["translated_text"]
    assert len(session.persona_shifts) >= 2
    assert session.persona_directive["tone"].lower() in {"celebratory", "reassuring", "analytical"}
    assert session.input_audio_path == Path("input.wav")
    stored_session = voice_service.sessions.load(session.session_id)
    assert stored_session.response_audio_path == Path("response.wav")
    stream = list(voice_service.stream_response_audio(session.session_id))
    assert stream, "Streamed audio should contain chunks"
    assert isinstance(voice_service.translator, StubTranslator)
    translator_calls = voice_service.translator.calls  # type: ignore[attr-defined]
    assert translator_calls and translator_calls[0]["target"] == "es"
    assert voice_service.synthesizer.last_text is not None  # type: ignore[attr-defined]
    assert voice_service.synthesizer.last_text.endswith("[es]")  # type: ignore[attr-defined]
    thread_payload = voice_service.agents_service.get_thread(session.thread_id)
    voice_memory = thread_payload["memory"]["voice_sessions"][session.session_id]
    assert voice_memory["persona_id"] == "aurora"
    assert voice_memory["sentiment_label"] == "positive"
    assert voice_memory["segments"][0]["text"].startswith("How is the")
    assert voice_memory["translation"]["glossary"]["compliance"] == "cumplimiento"


def test_voice_service_persona_transitions(voice_service: VoiceService) -> None:
    outcome = voice_service.create_session(
        case_id="CASE-INTL-002",
        audio_payload=b"audio",
        persona_id="aurora",
        principal=None,
    )
    assert len(outcome.sentiment_arc) >= 1
    assert len(outcome.persona_shifts) >= 2
    last_shift = outcome.persona_shifts[-1]
    assert last_shift["language"] == "es"
    assert "sentiment" in last_shift["trigger"].lower()
    assert outcome.translation.target_language == "es"


def test_voice_session_handles_missing_thread_id(
    voice_service: VoiceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    agents_service = voice_service.agents_service
    original_run_case = agents_service.run_case

    def run_case_without_thread(self, *, case_id: str, question: str, principal=None):
        payload = original_run_case(case_id=case_id, question=question, principal=principal)
        scrubbed = dict(payload)
        scrubbed.pop("thread_id", None)
        return scrubbed

    monkeypatch.setattr(
        agents_service,
        "run_case",
        MethodType(run_case_without_thread, agents_service),
    )

    outcome = voice_service.create_session(
        case_id="CASE-DETACHED-003",
        audio_payload=b"audio",
        persona_id="aurora",
        principal=None,
    )

    assert outcome.session.thread_id is None
    assert "None" not in agents_service.memory_store.list_threads()


def test_voice_session_uses_provided_thread_id_when_missing_from_payload(
    voice_service: VoiceService, monkeypatch: pytest.MonkeyPatch
) -> None:
    agents_service = voice_service.agents_service
    original_run_case = agents_service.run_case

    def run_case_without_thread(self, *, case_id: str, question: str, principal=None):
        payload = original_run_case(case_id=case_id, question=question, principal=principal)
        scrubbed = dict(payload)
        scrubbed.pop("thread_id", None)
        return scrubbed

    monkeypatch.setattr(
        agents_service,
        "run_case",
        MethodType(run_case_without_thread, agents_service),
    )

    provided_thread_id = "thread-manual-123"
    outcome = voice_service.create_session(
        case_id="CASE-DETACHED-004",
        audio_payload=b"audio",
        persona_id="aurora",
        principal=None,
        thread_id=provided_thread_id,
    )

    assert outcome.session.thread_id == provided_thread_id
    stored_thread = agents_service.get_thread(provided_thread_id)
    voice_metadata = stored_thread["memory"]["voice_sessions"][outcome.session.session_id]
    assert voice_metadata["source_thread_id"] == provided_thread_id

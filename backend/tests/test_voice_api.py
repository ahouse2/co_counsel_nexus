from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Iterable
from uuid import uuid4

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.models.api import VoicePersonaListResponse
from backend.app.services.voice.adapters import TranscriptionResult, TranscriptionSegment
from backend.app.services.voice.sentiment import SentimentResult
from backend.app.services.voice.service import (
    PersonaDirective,
    TranslationResult,
    VoiceServiceError,
    VoiceSessionOutcome,
)
from backend.app.services.voice.session import VoiceSession, VoiceTurn
from backend.app.services.voice import get_voice_service


class ApiStubVoiceService:
    def __init__(self) -> None:
        self.personas = [
            {
                "persona_id": "aurora",
                "label": "Aurora",
                "description": "Warm cadence",
                "speaker_id": "p273",
            }
        ]
        self._sessions: Dict[str, VoiceSessionOutcome] = {}
        self.agents_service = _StubAgentsService()

    def list_personas(self) -> Iterable[Dict[str, str]]:
        return list(self.personas)

    def create_session(
        self,
        *,
        case_id: str,
        audio_payload: bytes,
        persona_id: str,
        principal,
        thread_id: str | None = None,
    ) -> VoiceSessionOutcome:
        if not audio_payload:
            raise VoiceServiceError("empty audio")
        created_at = datetime.now(timezone.utc)
        session_id = uuid4().hex
        session = VoiceSession(
            session_id=session_id,
            thread_id="thread-stub",
            case_id=case_id,
            persona_id=persona_id,
            transcript="Transcribed question",
            sentiment_label="neutral",
            sentiment_score=0.5,
            pace=1.0,
            segments=[{"start": 0.0, "end": 1.0, "text": "Transcribed question", "confidence": 0.9}],
            turns=[
                VoiceTurn(
                    speaker="user",
                    text="Transcribed question",
                    sentiment=0.5,
                    sentiment_label="neutral",
                    pace=1.0,
                    created_at=created_at,
                ),
                VoiceTurn(
                    speaker="assistant",
                    text="Assistant reply",
                    sentiment=0.5,
                    sentiment_label="neutral",
                    pace=1.0,
                    created_at=created_at,
                ),
            ],
            created_at=created_at,
            updated_at=created_at,
        )
        outcome = VoiceSessionOutcome(
            session=session,
            transcript=TranscriptionResult(
                text="Transcribed question",
                language="en",
                duration=1.0,
                segments=(TranscriptionSegment(start=0.0, end=1.0, text="Transcribed question", confidence=0.9),),
            ),
            sentiment=SentimentResult(label="neutral", score=0.5, pace=1.0),
            assistant_text="Assistant reply",
            thread_payload=self.agents_service.persist_thread(session.thread_id, session.case_id, session.transcript),
            persona_directive=PersonaDirective(
                persona_id=session.persona_id,
                speaker_id=None,
                tone="analytical",
                language="en",
                pace=1.0,
                glossary={},
                rationale="Stub directive",
            ),
            translation=TranslationResult(
                source_language="en",
                target_language="en",
                translated_text="Assistant reply",
                bilingual_text="Assistant reply",
                applied_glossary={},
            ),
            sentiment_arc=(
                {"offset": 0.0, "score": 0.5, "label": "neutral"},
            ),
            persona_shifts=(
                {
                    "at": 0.0,
                    "persona_id": session.persona_id,
                    "tone": "listening",
                    "language": "en",
                    "pace": 1.0,
                    "trigger": "user sentiment intake",
                },
            ),
        )
        self._sessions[session_id] = outcome
        return outcome

    def get_session(self, session_id: str) -> VoiceSession:
        return self._sessions[session_id].session

    def stream_response_audio(self, session_id: str, *, chunk_size: int = 4096):
        frequency = 880
        sr = 22050
        duration = 0.05
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        waveform = (0.2 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
        buffer = BytesIO()
        import soundfile as sf

        sf.write(buffer, waveform, sr, format="WAV")
        data = buffer.getvalue()
        for start in range(0, len(data), chunk_size):
            yield data[start : start + chunk_size]


class _StubAgentsService:
    def __init__(self) -> None:
        self.memory_store: Dict[str, Dict[str, Any]] = {}

    def persist_thread(self, thread_id: str, case_id: str, question: str) -> Dict[str, Any]:
        payload = {
            "thread_id": thread_id,
            "case_id": case_id,
            "question": question,
            "memory": {"voice_sessions": {}},
            "telemetry": {},
        }
        self.memory_store[thread_id] = payload
        return payload

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        return self.memory_store[thread_id]


@pytest.fixture()
def voice_api_stub() -> ApiStubVoiceService:
    return ApiStubVoiceService()


@pytest.fixture()
def voice_client(client: TestClient, voice_api_stub: ApiStubVoiceService) -> TestClient:
    app: FastAPI = client.app
    app.dependency_overrides[get_voice_service] = lambda: voice_api_stub
    return client


def _audio_blob() -> bytes:
    sr = 16000
    duration = 0.05
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buffer = BytesIO()
    import soundfile as sf

    sf.write(buffer, tone, sr, format="WAV")
    return buffer.getvalue()


def test_list_personas(voice_client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory(scopes=["agents:run"], roles=["ResearchAnalyst"], audience=["co-counsel.agents"])
    response = voice_client.get("/voice/personas", headers=headers)
    assert response.status_code == 200
    payload = VoicePersonaListResponse(**response.json())
    assert payload.personas[0].persona_id == "aurora"


def test_create_voice_session_round_trip(voice_client: TestClient, auth_headers_factory) -> None:
    headers = auth_headers_factory(scopes=["agents:run"], roles=["ResearchAnalyst"], audience=["co-counsel.agents"])
    audio_bytes = _audio_blob()
    response = voice_client.post(
        "/voice/sessions",
        headers=headers,
        files={"audio": ("audio.wav", audio_bytes, "audio/wav")},
        data={"case_id": "CASE-77", "persona_id": "aurora"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["transcript"] == "Transcribed question"
    assert payload["assistant_text"] == "Assistant reply"
    audio_response = voice_client.get(payload["audio_url"], headers=auth_headers_factory(
        scopes=["agents:read"], roles=["ResearchAnalyst"], audience=["co-counsel.agents"]
    ))
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/wav"
    assert len(audio_response.content) > 100
    session_id = payload["session_id"]
    detail_response = voice_client.get(
        f"/voice/sessions/{session_id}",
        headers=auth_headers_factory(scopes=["agents:read"], roles=["ResearchAnalyst"], audience=["co-counsel.agents"]),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["sentiment"]["label"] == "neutral"
    assert detail_payload["persona_id"] == "aurora"

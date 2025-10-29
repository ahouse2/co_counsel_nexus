from __future__ import annotations

from dataclasses import dataclass
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ...config import Settings
from ...security.authz import Principal
from ...storage.agent_memory_store import AgentThreadRecord
from ..agents import AgentsService
from ..errors import WorkflowAbort
from ..costs import get_cost_tracking_service
from .adapters import CoquiSynthesizer, TranscriptionResult, WhisperTranscriber
from .sentiment import SentimentAnalyser, SentimentResult
from .session import VoiceSession, VoiceSessionStore, VoiceTurn


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_voice_sessions_counter = _meter.create_counter(
    "voice_sessions_total",
    unit="1",
    description="Voice sessions processed",
)
_voice_session_duration = _meter.create_histogram(
    "voice_session_duration_ms",
    unit="ms",
    description="End-to-end voice session duration",
)
_voice_transcription_latency = _meter.create_histogram(
    "voice_transcription_latency_ms",
    unit="ms",
    description="Latency of whisper transcription",
)
_voice_tts_latency = _meter.create_histogram(
    "voice_tts_duration_ms",
    unit="ms",
    description="Latency of TTS synthesis",
)
_voice_sentiment_score = _meter.create_histogram(
    "voice_sentiment_score",
    unit="1",
    description="Sentiment scores observed across sessions",
)


@dataclass(slots=True)
class VoiceSessionOutcome:
    """Result bundle returned after processing a voice request."""

    session: VoiceSession
    transcript: TranscriptionResult
    sentiment: SentimentResult
    assistant_text: str
    thread_payload: Dict[str, Any]


class VoiceServiceError(RuntimeError):
    """Raised when the voice pipeline encounters an unrecoverable error."""


class VoiceService:
    """Coordinates STT, sentiment, agents orchestration, and TTS."""

    def __init__(
        self,
        *,
        settings: Settings,
        transcriber: WhisperTranscriber,
        synthesizer: CoquiSynthesizer,
        sentiment: SentimentAnalyser,
        session_store: VoiceSessionStore,
        agents_service: AgentsService,
    ) -> None:
        self.settings = settings
        self.transcriber = transcriber
        self.synthesizer = synthesizer
        self.sentiment = sentiment
        self.sessions = session_store
        self.agents_service = agents_service

    def list_personas(self) -> Iterable[Dict[str, str]]:
        personas = []
        available_speakers = set(self._safe_available_speakers())
        for persona_id, payload in self.settings.voice_personas.items():
            entry = {
                "persona_id": persona_id,
                "label": payload.get("label", persona_id.title()),
                "description": payload.get("description", ""),
                "speaker_id": payload.get("speaker_id"),
            }
            if entry["speaker_id"] and available_speakers and entry["speaker_id"] not in available_speakers:
                entry["speaker_id"] = None
            personas.append(entry)
        return personas

    def create_session(
        self,
        *,
        case_id: str,
        audio_payload: bytes,
        persona_id: str,
        principal: Principal | None,
        thread_id: str | None = None,
    ) -> VoiceSessionOutcome:
        if not self.settings.voice_enabled:
            raise VoiceServiceError("Voice experience is disabled via configuration")
        persona = self.settings.voice_personas.get(persona_id)
        if not persona:
            raise VoiceServiceError(f"Persona '{persona_id}' is not defined")

        tenant_id = principal.tenant_id if principal else None
        session_started = time.perf_counter()
        cost_service = get_cost_tracking_service()

        with _tracer.start_as_current_span("voice.create_session") as span:
            span.set_attribute("voice.case_id", case_id)
            span.set_attribute("voice.persona", persona_id)
            if tenant_id:
                span.set_attribute("voice.tenant_id", tenant_id)
            try:
                transcription_started = time.perf_counter()
                transcript = self.transcriber.transcribe(audio_payload)
                transcription_latency = (time.perf_counter() - transcription_started) * 1000.0
                _voice_transcription_latency.record(
                    transcription_latency,
                    attributes={"model": getattr(self.transcriber, "model_id", "unknown")},
                )
                transcribe_device = getattr(self.transcriber, "device", "unknown")
                span.set_attribute("voice.transcription_latency_ms", transcription_latency)
                span.set_attribute("voice.transcription_device", transcribe_device)
                if transcribe_device == "cuda":
                    cost_service.record_gpu_utilisation(
                        tenant_id=tenant_id,
                        device="voice-transcription",
                        duration_ms=transcription_latency,
                        utilisation_percent=85.0,
                        metadata={"model": getattr(self.transcriber, "model_id", "unknown")},
                    )

                sentiment = self.sentiment.analyse(transcript.text)
                _voice_sentiment_score.record(sentiment.score, attributes={"persona": persona_id})

                speaker_id = self._resolve_speaker(persona.get("speaker_id"))
                agent_started = time.perf_counter()
                thread_payload = self.agents_service.run_case(
                    case_id=case_id,
                    question=transcript.text,
                    principal=principal,
                )
                agent_latency = (time.perf_counter() - agent_started) * 1000.0
                span.set_attribute("voice.agent_latency_ms", agent_latency)

                assistant_text = self._resolve_assistant_text(thread_payload)
                tts_started = time.perf_counter()
                response_audio = self.synthesizer.synthesize(
                    assistant_text,
                    speaker_id=speaker_id,
                    speed=sentiment.pace,
                    sample_rate=self.settings.voice_sample_rate,
                )
                tts_latency = (time.perf_counter() - tts_started) * 1000.0
                _voice_tts_latency.record(
                    tts_latency,
                    attributes={"model": getattr(self.synthesizer, "model_id", "unknown")},
                )
                synth_device = getattr(self.synthesizer, "device", "unknown")
                span.set_attribute("voice.tts_device", synth_device)
                span.set_attribute("voice.tts_latency_ms", tts_latency)
                if synth_device == "cuda":
                    cost_service.record_gpu_utilisation(
                        tenant_id=tenant_id,
                        device="voice-tts",
                        duration_ms=tts_latency,
                        utilisation_percent=90.0,
                        metadata={"model": getattr(self.synthesizer, "model_id", "unknown")},
                    )

                session_id = uuid4().hex
                now = datetime.now(timezone.utc)
                session = VoiceSession(
                    session_id=session_id,
                    thread_id=str(thread_payload.get("thread_id")),
                    case_id=case_id,
                    persona_id=persona_id,
                    transcript=transcript.text,
                    sentiment_label=sentiment.label,
                    sentiment_score=sentiment.score,
                    pace=sentiment.pace,
                    segments=[
                        {
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text,
                            "confidence": segment.confidence,
                        }
                        for segment in transcript.segments
                    ],
                    turns=[
                        VoiceTurn(
                            speaker="user",
                            text=transcript.text,
                            sentiment=sentiment.score,
                            sentiment_label=sentiment.label,
                            pace=1.0,
                            created_at=now,
                        ),
                        VoiceTurn(
                            speaker="assistant",
                            text=assistant_text,
                            sentiment=sentiment.score,
                            sentiment_label=sentiment.label,
                            pace=sentiment.pace,
                            created_at=now,
                        ),
                    ],
                    created_at=now,
                    updated_at=now,
                )
                session = self.sessions.save(
                    session,
                    input_audio=audio_payload,
                    response_audio=response_audio,
                )
                self._persist_thread_voice_metadata(
                    thread_payload,
                    session,
                    sentiment,
                    source_thread_id=thread_id,
                )
                duration_ms = (time.perf_counter() - session_started) * 1000.0
                _voice_session_duration.record(duration_ms, attributes={"persona": persona_id})
                _voice_sessions_counter.add(
                    1, attributes={"persona": persona_id, "status": "completed"}
                )
                span.set_attribute("voice.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.OK))
                return VoiceSessionOutcome(
                    session=session,
                    transcript=transcript,
                    sentiment=sentiment,
                    assistant_text=assistant_text,
                    thread_payload=thread_payload,
                )
            except VoiceServiceError as exc:
                _voice_sessions_counter.add(
                    1, attributes={"persona": persona_id, "status": "failed"}
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise
            except WorkflowAbort as exc:  # pragma: no cover - orchestrator level errors
                _voice_sessions_counter.add(
                    1, attributes={"persona": persona_id, "status": "failed"}
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise
            except Exception as exc:  # pragma: no cover - defensive safety net
                _voice_sessions_counter.add(
                    1, attributes={"persona": persona_id, "status": "failed"}
                )
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise VoiceServiceError(f"Agents orchestration failed: {exc}") from exc

    def get_session(self, session_id: str) -> VoiceSession:
        return self.sessions.load(session_id)

    def stream_response_audio(self, session_id: str, *, chunk_size: int = 4096):
        yield from self.sessions.stream_audio(session_id, "response", chunk_size=chunk_size)

    def stream_input_audio(self, session_id: str, *, chunk_size: int = 4096):
        yield from self.sessions.stream_audio(session_id, "input", chunk_size=chunk_size)

    def _resolve_assistant_text(self, payload: Dict[str, Any]) -> str:
        answer = str(payload.get("final_answer", "")).strip()
        if answer:
            return answer
        turns = payload.get("turns", [])
        if isinstance(turns, list) and turns:
            last = turns[-1]
            if isinstance(last, dict):
                output = last.get("output", {})
                if isinstance(output, dict):
                    answer_candidate = output.get("answer") or output.get("summary")
                    if isinstance(answer_candidate, str) and answer_candidate.strip():
                        return answer_candidate.strip()
                text_candidate = last.get("text")
                if isinstance(text_candidate, str) and text_candidate.strip():
                    return text_candidate.strip()
        return "I have recorded your request. Please review the case timeline for further detail."

    def _resolve_speaker(self, speaker_id: str | None) -> str | None:
        if speaker_id:
            return speaker_id
        available = list(self._safe_available_speakers())
        if available:
            return available[0]
        return None

    def _safe_available_speakers(self) -> Iterable[str]:
        try:
            return self.synthesizer.available_speakers()
        except Exception:  # pragma: no cover - optional capability
            return ()

    def _persist_thread_voice_metadata(
        self,
        payload: Dict[str, Any],
        session: VoiceSession,
        sentiment: SentimentResult,
        *,
        source_thread_id: str | None = None,
    ) -> None:
        voice_memory = payload.setdefault("memory", {}).setdefault("voice_sessions", {})
        voice_memory[session.session_id] = {
            "transcript": session.transcript,
            "persona_id": session.persona_id,
            "sentiment_label": sentiment.label,
            "sentiment_score": sentiment.score,
            "pace": sentiment.pace,
            "segments": session.segments,
            "created_at": session.created_at.isoformat(),
        }
        if source_thread_id:
            voice_memory[session.session_id]["source_thread_id"] = source_thread_id
        payload.setdefault("telemetry", {}).setdefault("voice", {})[session.session_id] = {
            "sentiment": sentiment.label,
            "pace": sentiment.pace,
        }
        record = AgentThreadRecord(thread_id=session.thread_id, payload=payload)
        self.agents_service.memory_store.write(record)


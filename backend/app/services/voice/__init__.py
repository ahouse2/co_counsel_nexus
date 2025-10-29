from __future__ import annotations

from functools import lru_cache

from ...config import get_settings
from ..agents import get_agents_service
from .adapters import CoquiSynthesizer, WhisperTranscriber
from .sentiment import SentimentAnalyser
from .service import VoiceService, VoiceServiceError, VoiceSessionOutcome
from .session import VoiceSessionStore


@lru_cache(maxsize=1)
def get_voice_service() -> VoiceService:
    settings = get_settings()
    agents_service = get_agents_service()
    transcriber = WhisperTranscriber(
        settings.voice_whisper_model,
        cache_dir=settings.voice_cache_dir / "whisper",
        compute_type=settings.voice_whisper_compute_type,
        device_preference=settings.voice_device_preference,
        target_sample_rate=16000,
    )
    synthesizer = CoquiSynthesizer(
        settings.voice_tts_model,
        cache_dir=settings.voice_cache_dir / "tts",
        device_preference=settings.voice_device_preference,
        default_sample_rate=settings.voice_sample_rate,
    )
    sentiment = SentimentAnalyser(
        settings.voice_sentiment_model,
        device_preference=settings.voice_device_preference,
    )
    session_store = VoiceSessionStore(settings.voice_sessions_dir)
    return VoiceService(
        settings=settings,
        transcriber=transcriber,
        synthesizer=synthesizer,
        sentiment=sentiment,
        session_store=session_store,
        agents_service=agents_service,
    )


__all__ = [
    "get_voice_service",
    "VoiceService",
    "VoiceServiceError",
    "VoiceSessionOutcome",
]


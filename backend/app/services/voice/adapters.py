from __future__ import annotations

from dataclasses import dataclass
from dataclasses import dataclass
import time
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
import soundfile as sf


@dataclass(slots=True)
class TranscriptionSegment:
    """Discrete transcription segment emitted by Whisper."""

    start: float
    end: float
    text: str
    confidence: float


@dataclass(slots=True)
class TranscriptionResult:
    """Container for Whisper transcription output."""

    text: str
    language: str
    duration: float
    segments: Sequence[TranscriptionSegment]


class WhisperTranscriber:
    """Faster-Whisper adapter with GPU/CPU fallback and cache-aware loading."""

    def __init__(
        self,
        model_id: str,
        *,
        cache_dir: Path,
        compute_type: str,
        device_preference: str,
        target_sample_rate: int,
    ) -> None:
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.compute_type = compute_type
        self.device_preference = device_preference
        self.target_sample_rate = target_sample_rate
        self._model = None
        self._device = None

    def _resolve_device(self) -> str:
        if self._device is not None:
            return self._device
        preference = (self.device_preference or "auto").lower()
        device = "cpu"
        if preference in {"auto", "cuda"}:
            try:
                import torch  # type: ignore

                if torch.cuda.is_available():
                    device = "cuda"
            except Exception:  # pragma: no cover - optional dependency failure
                device = "cpu"
            if preference == "cuda" and device != "cuda":
                raise RuntimeError("CUDA device requested but not available")
        self._device = device
        return device

    @property
    def device(self) -> str:
        return self._resolve_device()

    def _load_model(self):
        if self._model is not None:
            return self._model
        load_started = time.perf_counter()
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "faster-whisper is required for speech transcription. Install backend voice extras."
            ) from exc
        device = self._resolve_device()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = WhisperModel(
            self.model_id,
            device=device,
            compute_type=self.compute_type,
            download_root=str(self.cache_dir),
        )
        load_duration = (time.perf_counter() - load_started) * 1000.0
        try:
            from ..costs import get_cost_tracking_service

            service = get_cost_tracking_service()
            service.record_model_load(
                model_name=self.model_id,
                framework="faster-whisper",
                device=device,
                duration_ms=load_duration,
            )
        except Exception:  # pragma: no cover - optional instrumentation
            pass
        return self._model

    def transcribe(self, audio_bytes: bytes, *, language: str | None = None) -> TranscriptionResult:
        if not audio_bytes:
            raise ValueError("Audio payload is empty")
        audio, sample_rate = self._read_audio(audio_bytes)
        audio = self._resample(audio, sample_rate, self.target_sample_rate)
        model = self._load_model()
        segments_iter, info = model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=True,
        )
        segments: List[TranscriptionSegment] = []
        transcript_parts: List[str] = []
        duration = float(info.duration)
        detected_language = info.language or "en"
        for segment in segments_iter:
            confidence = float(getattr(segment, "avg_logprob", 0.0))
            if hasattr(segment, "compression_ratio") and segment.compression_ratio:
                confidence = max(confidence, float(1.0 - segment.compression_ratio))
            segments.append(
                TranscriptionSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=str(segment.text).strip(),
                    confidence=confidence,
                )
            )
            transcript_parts.append(str(segment.text).strip())
        transcript = " ".join(part for part in transcript_parts if part)
        if not transcript:
            raise RuntimeError("Whisper produced an empty transcription")
        return TranscriptionResult(
            text=transcript,
            language=detected_language,
            duration=duration,
            segments=tuple(segments),
        )

    def _read_audio(self, payload: bytes) -> tuple[np.ndarray, int]:
        buffer = BytesIO(payload)
        data, sample_rate = sf.read(buffer, dtype="float32")
        if data.ndim == 2:
            data = np.mean(data, axis=1)
        return data.astype(np.float32), int(sample_rate)

    def _resample(self, data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return data
        duration = len(data) / float(orig_sr)
        target_length = int(round(duration * target_sr))
        if target_length <= 0:
            raise ValueError("Resampling produced non-positive frame length")
        old_indices = np.linspace(0.0, duration, num=len(data), endpoint=False)
        new_indices = np.linspace(0.0, duration, num=target_length, endpoint=False)
        resampled = np.interp(new_indices, old_indices, data)
        return resampled.astype(np.float32)


class CoquiSynthesizer:
    """Coqui TTS adapter supporting persona-specific speakers and tempo control."""

    def __init__(
        self,
        model_id: str,
        *,
        cache_dir: Path,
        device_preference: str,
        default_sample_rate: int,
    ) -> None:
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.device_preference = device_preference
        self.default_sample_rate = default_sample_rate
        self._tts = None
        self._device = None

    def _resolve_device(self) -> str:
        if self._device is not None:
            return self._device
        preference = (self.device_preference or "auto").lower()
        device = "cpu"
        if preference in {"auto", "cuda"}:
            try:
                import torch  # type: ignore

                if torch.cuda.is_available():
                    device = "cuda"
            except Exception:  # pragma: no cover - defensive
                device = "cpu"
            if preference == "cuda" and device != "cuda":
                raise RuntimeError("CUDA device requested for TTS but not available")
        self._device = device
        return device

    @property
    def device(self) -> str:
        return self._resolve_device()

    def _load_model(self):
        if self._tts is not None:
            return self._tts
        load_started = time.perf_counter()
        try:
            from TTS.api import TTS  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("Coqui TTS is required for voice synthesis") from exc
        device = self._resolve_device()
        kwargs = {
            "model_name": self.model_id,
            "progress_bar": False,
            "gpu": device == "cuda",
        }
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            kwargs["cache_dir"] = str(self.cache_dir)
        self._tts = TTS(**kwargs)
        load_duration = (time.perf_counter() - load_started) * 1000.0
        try:
            from ..costs import get_cost_tracking_service

            service = get_cost_tracking_service()
            service.record_model_load(
                model_name=self.model_id,
                framework="coqui-tts",
                device=device,
                duration_ms=load_duration,
            )
        except Exception:  # pragma: no cover - optional instrumentation
            pass
        return self._tts

    def available_speakers(self) -> Iterable[str]:
        model = self._load_model()
        speakers = getattr(model, "speakers", None)
        if not speakers:
            return ()
        return tuple(str(speaker) for speaker in speakers)

    def synthesize(
        self,
        text: str,
        *,
        speaker_id: str | None,
        speed: float,
        sample_rate: int | None = None,
    ) -> bytes:
        if not text.strip():
            raise ValueError("Cannot synthesise empty text")
        tts = self._load_model()
        desired_sample_rate = sample_rate or getattr(tts, "output_sample_rate", self.default_sample_rate)
        wav: np.ndarray = tts.tts(text=text, speaker=speaker_id, speed=max(0.5, min(speed, 2.0)))  # type: ignore
        wav = wav.astype(np.float32)
        buffer = BytesIO()
        sf.write(buffer, wav, desired_sample_rate, format="WAV")
        return buffer.getvalue()


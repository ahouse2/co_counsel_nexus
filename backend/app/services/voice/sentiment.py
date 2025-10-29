from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class SentimentResult:
    """Sentiment score with recommended playback pace."""

    label: Literal["positive", "negative", "neutral"]
    score: float
    pace: float


class SentimentAnalyser:
    """Transformer-based sentiment analyser with deterministic pacing heuristic."""

    def __init__(self, model_id: str, *, device_preference: str) -> None:
        self.model_id = model_id
        self.device_preference = device_preference
        self._pipeline = None
        self._device = None

    def _resolve_device(self) -> int:
        if self._device is not None:
            return self._device
        preference = (self.device_preference or "auto").lower()
        device = -1
        if preference in {"auto", "cuda"}:
            try:
                import torch  # type: ignore

                if torch.cuda.is_available():
                    device = 0
            except Exception:  # pragma: no cover - optional dependency guard
                device = -1
            if preference == "cuda" and device != 0:
                raise RuntimeError("CUDA requested for sentiment analysis but unavailable")
        self._device = device
        return device

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError("transformers is required for sentiment analysis") from exc
        device = self._resolve_device()
        kwargs = {"model": self.model_id}
        if device >= 0:
            kwargs["device"] = device
        self._pipeline = pipeline("sentiment-analysis", **kwargs)
        return self._pipeline

    def analyse(self, text: str) -> SentimentResult:
        if not text.strip():
            raise ValueError("Sentiment analysis requires non-empty text")
        nlp = self._load_pipeline()
        raw = nlp(text)[0]
        label = str(raw["label"]).lower()
        score = float(raw.get("score", 0.5))
        if "pos" in label:
            sentiment = "positive"
        elif "neg" in label:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        pace = self._pace(sentiment, score)
        return SentimentResult(label=sentiment, score=score, pace=pace)

    def _pace(self, label: str, score: float) -> float:
        clamped = max(0.0, min(score, 1.0))
        if label == "positive":
            return 1.0 + 0.1 * clamped
        if label == "negative":
            return max(0.75, 1.0 - 0.15 * clamped)
        return 1.0


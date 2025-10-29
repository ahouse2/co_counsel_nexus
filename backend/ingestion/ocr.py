"""OCR utilities for the ingestion pipeline."""

from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from PIL import Image
from pypdf import PdfReader

try:  # pragma: no cover - exercised indirectly via OCR tests
    import pytesseract
    from pytesseract import Output, TesseractNotFoundError
except ModuleNotFoundError:  # pragma: no cover - offline fallback
    class _FallbackOutput:
        DICT = "dict"

    class _MissingTesseract(RuntimeError):
        """Raised when OCR functionality is invoked without pytesseract installed."""

    class _FallbackTesseractModule:
        class TesseractError(_MissingTesseract):
            pass

        def image_to_data(self, *args, **kwargs):
            raise _MissingTesseract(
                "pytesseract is required for Tesseract OCR support. Install pytesseract or configure a vision provider."
            )

    pytesseract = _FallbackTesseractModule()
    Output = _FallbackOutput()
    TesseractNotFoundError = _MissingTesseract

from .settings import OcrConfig, OcrProvider


@dataclass
class OcrResult:
    """Structured OCR response used for provenance metadata."""

    text: str
    engine: str
    confidence: Optional[float]
    tokens: List[Dict[str, Any]]


class OcrEngine:
    """Dispatch OCR requests to the configured backend."""

    def __init__(self, config: OcrConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        if config.tessdata_path:
            import os

            os.environ.setdefault("TESSDATA_PREFIX", str(config.tessdata_path))

    def extract_from_pdf(self, path: Path) -> OcrResult:
        reader = PdfReader(str(path))
        fragments: List[str] = []
        tokens: List[Dict[str, Any]] = []
        for page_index, page in enumerate(reader.pages):
            extracted = (page.extract_text() or "").strip()
            if extracted:
                fragments.append(extracted)
                continue
            self.logger.debug("Running OCR on rasterised PDF page", extra={"page": page_index, "path": str(path)})
            page_tokens, page_text = self._extract_images_from_page(page)
            tokens.extend(page_tokens)
            if page_text:
                fragments.append(page_text)
        text = "\n\n".join(fragment for fragment in fragments if fragment)
        confidence = _average_confidence(tokens)
        return OcrResult(text=text, engine=self.config.provider.value, confidence=confidence, tokens=tokens)

    def extract_from_image(self, path: Path) -> OcrResult:
        image_bytes = path.read_bytes()
        return self._process_image_bytes(image_bytes, source=f"file://{path}")

    # Internal helpers -------------------------------------------------

    def _extract_images_from_page(self, page) -> Tuple[List[Dict[str, Any]], str]:
        tokens: List[Dict[str, Any]] = []
        fragments: List[str] = []
        for image_index, image in enumerate(getattr(page, "images", [])):
            try:
                with Image.open(io.BytesIO(image.data)) as img:
                    result = self._image_to_tokens(img)
            except Exception:  # pragma: no cover - defensive guard
                self.logger.exception(
                    "Failed to decode PDF image for OCR",
                    extra={"image_index": image_index},
                )
                continue
            tokens.extend(result.tokens)
            if result.text:
                fragments.append(result.text)
        text = "\n".join(fragments)
        return tokens, text

    def _process_image_bytes(self, image_bytes: bytes, *, source: str) -> OcrResult:
        if self.config.provider is OcrProvider.VISION:
            vision_payload = self._invoke_vision(image_bytes)
            text = vision_payload.get("text", "").strip()
            tokens = vision_payload.get("tokens", [])
            confidence = vision_payload.get("confidence")
            return OcrResult(text=text, engine="vision", confidence=confidence, tokens=tokens)
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                return self._image_to_tokens(image, source=source)
        except (pytesseract.TesseractError, TesseractNotFoundError) as exc:  # pragma: no cover - escalated to fallback
            fallback = self.config.extra.get("vision_fallback") if self.config.extra else None
            if not fallback:
                self.logger.warning(
                    "Tesseract OCR unavailable; continuing without OCR text",
                    extra={"error": str(exc), "provider": "tesseract"},
                )
                return OcrResult(text="", engine="tesseract-unavailable", confidence=None, tokens=[])
            self.logger.warning(
                "Tesseract OCR failed; invoking vision fallback",
                extra={"error": str(exc)},
            )
            payload = self._invoke_vision(image_bytes, override=fallback)
            text = payload.get("text", "").strip()
            tokens = payload.get("tokens", [])
            confidence = payload.get("confidence")
            return OcrResult(text=text, engine="vision", confidence=confidence, tokens=tokens)

    def _image_to_tokens(self, image: Image.Image, source: str | None = None) -> OcrResult:
        languages = self.config.languages or "eng"
        tess_config = "--oem 3 --psm 6"
        data = pytesseract.image_to_data(image, lang=languages, config=tess_config, output_type=Output.DICT)
        tokens: List[Dict[str, Any]] = []
        fragments: List[str] = []
        for idx, text in enumerate(data.get("text", [])):
            if not text:
                continue
            conf = _coerce_confidence(data.get("conf", [None])[idx])
            token_payload = {
                "text": text,
                "confidence": conf,
                "left": data.get("left", [None])[idx],
                "top": data.get("top", [None])[idx],
                "width": data.get("width", [None])[idx],
                "height": data.get("height", [None])[idx],
                "source": source,
            }
            tokens.append(token_payload)
            fragments.append(text)
        text = " ".join(fragments)
        confidence = _average_confidence(tokens)
        return OcrResult(text=text, engine="tesseract", confidence=confidence, tokens=tokens)

    def _invoke_vision(self, image_bytes: bytes, override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        endpoint = (override or {}).get("endpoint") or self.config.vision_endpoint
        model = (override or {}).get("model") or self.config.vision_model
        api_key = (override or {}).get("api_key") or self.config.api_key
        if not endpoint:
            raise RuntimeError("Vision OCR endpoint not configured")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model or "vision-large",
            "image": base64.b64encode(image_bytes).decode("ascii"),
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, headers=headers, content=json.dumps(payload))
            response.raise_for_status()
            return response.json()


def _average_confidence(tokens: Iterable[Dict[str, Any]]) -> Optional[float]:
    confidences: List[float] = []
    for token in tokens:
        conf = token.get("confidence")
        if conf is None:
            continue
        try:
            confidences.append(float(conf))
        except (TypeError, ValueError):
            continue
    if not confidences:
        return None
    return sum(confidences) / len(confidences)


def _coerce_confidence(value: Any) -> Optional[float]:
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return None
    if conf < 0:
        return None
    return conf


__all__ = ["OcrEngine", "OcrResult"]

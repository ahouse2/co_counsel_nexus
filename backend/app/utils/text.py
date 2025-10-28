from __future__ import annotations

import math
import re
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_CAPITALIZED_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]{2,})\b")
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})")
_SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?")


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="ignore")


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    if overlap >= size:
        raise ValueError("Chunk overlap must be smaller than chunk size")

    chunks: List[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start = end - overlap
    return chunks


def hashed_embedding(text: str, dimensions: int = 128) -> List[float]:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    vector = [0.0] * dimensions
    tokens = _WORD_RE.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        vector[bucket] += 1.0
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


def extract_capitalized_entities(text: str) -> List[str]:
    return sorted({match.group(1) for match in _CAPITALIZED_RE.finditer(text)})


def find_dates(text: str) -> List[str]:
    return [match.group(1) for match in _DATE_RE.finditer(text)]


def sliding_window(sequence: Sequence[str], window: int) -> Iterator[Sequence[str]]:
    if window <= 0:
        raise ValueError("window must be positive")
    for idx in range(0, len(sequence), window):
        yield sequence[idx : idx + window]


def sentence_containing(text: str, fragment: str) -> Optional[str]:
    if not fragment:
        return None
    for match in _SENTENCE_RE.finditer(text):
        sentence = match.group(0).strip()
        if fragment in sentence:
            return sentence
    return None


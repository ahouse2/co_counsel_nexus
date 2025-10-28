from __future__ import annotations

from pathlib import Path

import math
import pytest

from backend.app.utils.text import (
    chunk_text,
    extract_capitalized_entities,
    find_dates,
    hashed_embedding,
    read_text,
    sentence_containing,
    sliding_window,
)


def test_chunk_text_validates_inputs() -> None:
    with pytest.raises(ValueError):
        chunk_text("hello", 0, 1)
    with pytest.raises(ValueError):
        chunk_text("hello", 5, 5)


def test_chunk_text_generates_overlapping_windows() -> None:
    chunks = chunk_text("abcdefghij", 4, 1)
    assert chunks == ["abcd", "defg", "ghij"]


def test_hashed_embedding_normalises_and_validates() -> None:
    with pytest.raises(ValueError):
        hashed_embedding("text", 0)
    vector = hashed_embedding("Alpha beta gamma", dimensions=16)
    assert pytest.approx(math.sqrt(sum(x * x for x in vector)), rel=1e-6) == 1.0


def test_read_text_fallback(tmp_path: Path) -> None:
    latin_file = tmp_path / "latin.txt"
    latin_file.write_bytes("olá".encode("latin-1"))
    assert read_text(latin_file) == "olá"


def test_sentence_containing_handles_missing_fragment() -> None:
    text = "Acme acquired Beta. Gamma responded." \
        " Delta filed suit."
    assert sentence_containing(text, "Gamma") == "Gamma responded."
    assert sentence_containing(text, "Zeta") is None
    assert sentence_containing(text, "") is None


def test_sliding_window_yields_chunks() -> None:
    with pytest.raises(ValueError):
        list(sliding_window(["a", "b"], 0))
    windows = list(sliding_window(["a", "b", "c", "d"], 2))
    assert windows == [["a", "b"], ["c", "d"]]


def test_extractors_find_entities_and_dates() -> None:
    text = "Acme Corp met John Doe on 2024-10-01 at Paris."
    entities = extract_capitalized_entities(text)
    assert entities == ["Acme", "Corp", "Doe", "John", "Paris"]
    dates = find_dates(text)
    assert dates == ["2024-10-01"]

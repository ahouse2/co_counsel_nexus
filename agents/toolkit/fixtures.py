from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Sequence


@dataclass(frozen=True)
class FixtureDocument:
    doc_id: str
    title: str
    snippets: Sequence[str]
    source: str

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FixtureDocument":
        return cls(
            doc_id=str(payload["id"]),
            title=str(payload.get("title", "")),
            snippets=list(payload.get("snippets", [])),
            source=str(payload.get("source", "unknown")),
        )


@dataclass
class FixtureCase:
    case_id: str
    question: str
    context: str
    documents: List[FixtureDocument]
    expected: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "FixtureCase":
        case_id = str(payload.get("id") or payload.get("case_id"))
        if not case_id:
            raise ValueError("Fixture case identifier is required")
        documents = [FixtureDocument.from_dict(item) for item in payload.get("documents", [])]
        expected = dict(payload.get("expected", {}))
        metadata = dict(payload.get("metadata", {}))
        return cls(
            case_id=case_id,
            question=str(payload.get("question", "")),
            context=str(payload.get("context", "")),
            documents=documents,
            expected=expected,
            metadata=metadata,
        )

    def expected_strings(self, key: str) -> List[str]:
        value = self.expected.get(key, [])
        return [str(item) for item in value]

    def required_documents(self) -> List[str]:
        return [str(item) for item in self.expected.get("required_documents", [])]


@dataclass
class FixtureSet:
    name: str
    agent_type: str
    version: str
    seed: int
    cases: List[FixtureCase]
    metadata: Dict[str, Any]
    checksum: str
    source_path: Path

    def iter_cases(self, *, shuffle: bool = False) -> Iterator[FixtureCase]:
        if not shuffle:
            yield from self.cases
            return
        rng = random.Random(self.seed)
        indices = list(range(len(self.cases)))
        rng.shuffle(indices)
        for index in indices:
            yield self.cases[index]

    def get(self, case_id: str) -> FixtureCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(f"Fixture case '{case_id}' not found in set '{self.name}'")

    @classmethod
    def load(cls, path: str | Path) -> "FixtureSet":
        fixture_path = Path(path)
        data = json.loads(fixture_path.read_text())
        if not isinstance(data, dict):
            raise ValueError(f"Fixture set at {fixture_path} is not a JSON object")
        raw_cases = data.get("cases") or []
        cases = [FixtureCase.from_dict(entry) for entry in raw_cases]
        case_ids = [case.case_id for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError(f"Fixture set {fixture_path} contains duplicate case identifiers")
        checksum = hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            name=str(data.get("name") or fixture_path.stem),
            agent_type=str(data.get("agent_type", "general")),
            version=str(data.get("version", "1.0.0")),
            seed=int(data.get("seed", 0)),
            cases=cases,
            metadata=dict(data.get("metadata", {})),
            checksum=checksum,
            source_path=fixture_path.resolve(),
        )


__all__ = [
    "FixtureSet",
    "FixtureCase",
    "FixtureDocument",
]

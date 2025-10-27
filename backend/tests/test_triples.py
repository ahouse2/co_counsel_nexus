from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.app.utils.triples import extract_entities, extract_triples, normalise_entity_id


def test_extract_entities_and_ids() -> None:
    text = "Acme Corporation acquired Beta LLC during Contract Alpha."
    entities = extract_entities(text)
    labels = {span.label for span in entities}
    assert "Acme Corporation" in labels
    assert "Beta LLC" in labels
    ids = {normalise_entity_id(span.label) for span in entities}
    assert "entity::acme_corporation" in ids
    assert "entity::beta_llc" in ids


def test_extract_triples_acquired_relation() -> None:
    text = "Acme Corporation acquired Beta LLC on 2024-10-01."
    triples = extract_triples(text)
    assert triples, "Expected triple extraction to yield at least one relation"
    triple = triples[0]
    assert triple.predicate == "ACQUIRED"
    assert triple.subject.label == "Acme Corporation"
    assert triple.obj.label == "Beta LLC"
    assert triple.evidence.startswith("Acme Corporation acquired Beta LLC")

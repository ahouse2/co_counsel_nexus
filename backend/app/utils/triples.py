from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List, Sequence

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_ENTITY_TOKEN_RE = re.compile(r"[A-Za-z][\w&'\-]*")
_ENTITY_STOPWORDS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "An",
    "A",
    "And",
    "Or",
    "But",
    "With",
    "Within",
    "Without",
    "During",
    "After",
    "Before",
    "On",
    "At",
    "In",
    "For",
    "Of",
    "By",
    "To",
}
_ORGANISATION_HINTS = {
    "corp",
    "corporation",
    "company",
    "inc",
    "llc",
    "ltd",
    "group",
    "bank",
    "university",
    "association",
    "ministry",
    "department",
    "committee",
    "council",
    "agency",
    "board",
    "court",
}
_LOCATION_HINTS = {
    "city",
    "county",
    "state",
    "republic",
    "province",
    "village",
    "island",
    "district",
    "kingdom",
}
_EVENT_HINTS = {
    "agreement",
    "settlement",
    "contract",
    "merger",
    "hearing",
    "trial",
    "acquisition",
}
_PERSON_TITLES = {
    "Judge",
    "Justice",
    "Attorney",
    "Dr",
    "Doctor",
    "Mr",
    "Mrs",
    "Ms",
    "Hon",
    "Professor",
}


@dataclass(frozen=True)
class EntitySpan:
    label: str
    start: int
    end: int
    entity_type: str


@dataclass(frozen=True)
class Triple:
    subject: EntitySpan
    predicate: str
    predicate_text: str
    obj: EntitySpan
    evidence: str
    sentence_index: int


def split_sentences(text: str) -> List[str]:
    sentences: List[str] = []
    for chunk in _SENTENCE_SPLIT_RE.split(text.strip()):
        candidate = chunk.strip()
        if candidate:
            sentences.append(candidate)
    return sentences


def extract_entities(text: str) -> List[EntitySpan]:
    sentences = split_sentences(text)
    entities: List[EntitySpan] = []
    for idx, sentence in enumerate(sentences):
        offset = _sentence_offset(text, sentence, idx)
        entities.extend(_extract_entities_from_sentence(sentence, offset))
    return _deduplicate_entities(entities)


def extract_triples(text: str) -> List[Triple]:
    sentences = split_sentences(text)
    triples: List[Triple] = []
    seen = set()
    for index, sentence in enumerate(sentences):
        spans = _extract_entities_from_sentence(sentence, 0)
        if len(spans) < 2:
            continue
        lowered = sentence.lower()
        for pattern, relation in _predicate_patterns():
            for match in pattern.finditer(lowered):
                subject = _closest_preceding(spans, match.start())
                obj = _closest_following(spans, match.end())
                if not subject or not obj:
                    continue
                key = (
                    normalise_entity_label(subject.label),
                    relation,
                    normalise_entity_label(obj.label),
                    match.group(0),
                )
                if key in seen:
                    continue
                seen.add(key)
                triples.append(
                    Triple(
                        subject=EntitySpan(
                            label=subject.label,
                            start=subject.start,
                            end=subject.end,
                            entity_type=subject.entity_type,
                        ),
                        predicate=relation,
                        predicate_text=match.group(0),
                        obj=EntitySpan(
                            label=obj.label,
                            start=obj.start,
                            end=obj.end,
                            entity_type=obj.entity_type,
                        ),
                        evidence=sentence.strip(),
                        sentence_index=index,
                    )
                )
    return triples


def normalise_entity_label(label: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", label.lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = re.sub(r"[^a-z0-9]+", "", label.lower())
    return cleaned or "entity"


def normalise_entity_id(label: str) -> str:
    return f"entity::{normalise_entity_label(label)}"


def infer_entity_type(label: str) -> str:
    tokens = [token.lower() for token in label.split() if token]
    if not tokens:
        return "Entity"
    if tokens[0].rstrip('.') in {title.lower() for title in _PERSON_TITLES}:
        return "Person"
    last = tokens[-1]
    if last in _ORGANISATION_HINTS or any(hint in tokens for hint in _ORGANISATION_HINTS):
        return "Organization"
    if last in _LOCATION_HINTS:
        return "Location"
    if any(hint in tokens for hint in _EVENT_HINTS):
        return "Event"
    return "Entity"


def _predicate_patterns() -> List[tuple[re.Pattern[str], str]]:
    patterns = [
        (r"filed a lawsuit against", "FILED_LAWSUIT_AGAINST"),
        (r"entered into", "ENTERED_INTO"),
        (r"reached a settlement with", "REACHED_SETTLEMENT_WITH"),
        (r"partnered with", "PARTNERED_WITH"),
        (r"merged with", "MERGED_WITH"),
        (r"acquired", "ACQUIRED"),
        (r"sued", "SUED"),
        (r"investigated", "INVESTIGATED"),
        (r"charged", "CHARGED"),
        (r"appointed", "APPOINTED"),
        (r"awarded", "AWARDED"),
    ]
    compiled: List[tuple[re.Pattern[str], str]] = []
    for raw, relation in patterns:
        tokens = raw.split()
        pattern_text = r"\b" + r"\s+".join(re.escape(token) for token in tokens) + r"\b"
        compiled.append((re.compile(pattern_text), relation))
    return compiled


def _extract_entities_from_sentence(sentence: str, offset: int) -> List[EntitySpan]:
    spans: List[EntitySpan] = []
    tokens = list(_ENTITY_TOKEN_RE.finditer(sentence))
    current: List[tuple[int, int, str]] = []
    for match in tokens:
        token = match.group(0)
        if _is_entity_token(token):
            if current and match.start() - current[-1][1] > 1:
                spans.extend(_coalesce_tokens(sentence, current, offset))
                current = []
            current.append((match.start(), match.end(), token))
        else:
            if current:
                spans.extend(_coalesce_tokens(sentence, current, offset))
                current = []
    if current:
        spans.extend(_coalesce_tokens(sentence, current, offset))
    return spans


def _is_entity_token(token: str) -> bool:
    if token in _ENTITY_STOPWORDS:
        return False
    if token.isupper() and len(token) > 1:
        return True
    return token[:1].isupper() and any(ch.islower() for ch in token[1:])


def _coalesce_tokens(
    sentence: str, tokens: Sequence[tuple[int, int, str]], offset: int
) -> Iterable[EntitySpan]:
    label = " ".join(token for _, _, token in tokens)
    label = label.strip()
    if len(label) <= 1:
        return []
    entity_type = infer_entity_type(label)
    start = tokens[0][0] + offset
    end = tokens[-1][1] + offset
    yield EntitySpan(label=label, start=start, end=end, entity_type=entity_type)


def _closest_preceding(spans: Sequence[EntitySpan], position: int) -> EntitySpan | None:
    candidates = [span for span in spans if span.end <= position]
    if not candidates:
        return None
    return max(candidates, key=lambda span: span.end)


def _closest_following(spans: Sequence[EntitySpan], position: int) -> EntitySpan | None:
    candidates = [span for span in spans if span.start >= position]
    if not candidates:
        return None
    return min(candidates, key=lambda span: span.start)


def _deduplicate_entities(entities: Sequence[EntitySpan]) -> List[EntitySpan]:
    result: List[EntitySpan] = []
    seen = set()
    for entity in entities:
        key = normalise_entity_label(entity.label)
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return result


def _sentence_offset(text: str, sentence: str, occurrence: int) -> int:
    start = -1
    search_from = 0
    for _ in range(occurrence + 1):
        start = text.find(sentence, search_from)
        if start == -1:
            break
        search_from = start + len(sentence)
    return max(start, 0)

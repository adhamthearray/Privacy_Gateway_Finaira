"""Deterministic, inference-only span and group proposal.

The official corpus does not provide a NER layer to the detector.  This module
therefore proposes spans from the document text only.  Gold spans are never
read by :func:`mine_spans` or :func:`mine_groups`; the training builder may add
gold spans as supervised positives, and records that fact in its manifest.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass
from typing import Iterable, Sequence


TOKEN_RE = re.compile(r"\w+(?:[-'/]\w+)*|[^\w\s]", re.UNICODE)
SENTENCE_RE = re.compile(r"[^.!?؟؛\n]+(?:[.!?؟؛]+|$)", re.UNICODE)
MONTH_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.I,
)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "we",
    "were", "with", "you", "your", "من", "في", "على", "إلى", "عن", "هذا", "هذه", "و", "أن",
}


@dataclass(frozen=True)
class CandidateSpan:
    span_id: str
    text: str
    start: int
    end: int
    score: float = 0.0

    def as_dict(self) -> dict:
        return {"span_id": self.span_id, "text": self.text, "start": self.start, "end": self.end}


@dataclass(frozen=True)
class CandidateGroup:
    group_id: str
    spans: tuple[CandidateSpan, ...]
    source: str = "document_only"

    def as_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "source": self.source,
            "spans": [s.as_dict() for s in self.spans],
        }


def _tokens(text: str, start: int = 0, end: int | None = None) -> list[tuple[str, int, int]]:
    end = len(text) if end is None else end
    return [(m.group(0), start + m.start(), start + m.end()) for m in TOKEN_RE.finditer(text[start:end])]


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    while end > start and text[end - 1] in ",.;:!?؟؛)]}،":
        end -= 1
    while start < end and text[start] in "([{\"'":
        start += 1
    return start, end


def _span_score(text: str, tokens: Sequence[tuple[str, int, int]]) -> float:
    words = [t for t, _, _ in tokens if re.search(r"\w", t, re.UNICODE)]
    if not words:
        return -100.0
    score = 0.25 * min(len(words), 8)
    if any(ch.isdigit() for ch in text):
        score += 4.0
    if MONTH_RE.search(text):
        score += 3.0
    if any(w[:1].isupper() for w in words if w.isascii()):
        score += 1.5
    if len(words) >= 2:
        score += 0.7
    if all(w.casefold() in STOPWORDS for w in words):
        score -= 5.0
    # Prefer phrases that are not merely one very common word, while leaving
    # Arabic and non-Latin scripts language-neutral.
    if len(words) == 1 and words[0].casefold() in STOPWORDS:
        score -= 4.0
    return score


def mine_spans(text: str, *, max_tokens: int = 8, max_spans: int = 256) -> list[CandidateSpan]:
    """Mine deterministic text-only spans, with no access to annotations.

    Candidate recall is reported separately.  A low proposal recall is a real
    detector limitation and is not hidden by inserting gold spans at inference.
    """
    raw: dict[tuple[int, int], tuple[str, float]] = {}
    for sentence in SENTENCE_RE.finditer(text):
        toks = _tokens(text, sentence.start(), sentence.end())
        for i in range(len(toks)):
            for n in range(1, min(max_tokens, len(toks) - i) + 1):
                chosen = toks[i : i + n]
                start, end = _trim(text, chosen[0][1], chosen[-1][2])
                if start >= end:
                    continue
                value = text[start:end]
                if not re.search(r"\w", value, re.UNICODE):
                    continue
                score = _span_score(value, chosen)
                if score <= -1:
                    continue
                key = (start, end)
                if key not in raw or score > raw[key][1]:
                    raw[key] = (value, score)
    ordered = sorted(raw.items(), key=lambda kv: (-kv[1][1], kv[0][0], kv[0][1]))[:max_spans]
    ordered.sort(key=lambda kv: (kv[0][0], kv[0][1]))
    return [CandidateSpan(f"c{i:04d}", value, start, end, score) for i, ((start, end), (value, score)) in enumerate(ordered)]


def _stable_score(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)


def _non_overlapping(a: CandidateSpan, b: CandidateSpan) -> bool:
    return a.end <= b.start or b.end <= a.start


def mine_groups(spans: Sequence[CandidateSpan], *, max_groups: int = 512, max_group_size: int = 4) -> list[CandidateGroup]:
    """Build bounded group proposals from mined spans only.

    The construction uses local neighbours plus deterministic distance buckets;
    this keeps inference finite while allowing both near and far cues.  The
    resulting proposal recall is an explicit metric in evaluation artifacts.
    """
    spans = sorted(spans, key=lambda s: (s.start, s.end, s.span_id))
    proposals: dict[tuple[str, ...], CandidateGroup] = {}
    for i, base in enumerate(spans):
        later = [s for s in spans[i + 1 :] if _non_overlapping(base, s)]
        if not later:
            continue
        local = later[:10]
        buckets: dict[int, list[CandidateSpan]] = {}
        for s in later:
            distance = max(0, s.start - base.end)
            bucket = 0 if distance < 80 else 1 if distance < 240 else 2 if distance < 700 else 3
            buckets.setdefault(bucket, []).append(s)
        selected = list(local)
        for bucket in sorted(buckets):
            selected.extend(sorted(buckets[bucket], key=lambda s: (_stable_score(base.span_id, s.span_id), s.start))[:4])
        selected = list(dict.fromkeys(selected))
        for size in range(2, max_group_size + 1):
            pool = selected[: (12 if size == 2 else 7 if size == 3 else 6)]
            for combo in itertools.combinations([base, *pool], size):
                combo = tuple(sorted(combo, key=lambda s: (s.start, s.end)))
                if len({s.span_id for s in combo}) != size:
                    continue
                if any(not _non_overlapping(x, y) for x, y in itertools.combinations(combo, 2)):
                    continue
                key = tuple(s.span_id for s in combo)
                proposals.setdefault(key, CandidateGroup(f"g{len(proposals):05d}", combo))
                if len(proposals) >= max_groups:
                    return list(proposals.values())
    return list(proposals.values())


def gold_group_spans(row: dict) -> dict[tuple[tuple[int, int], ...], str]:
    spans = {s["span_id"]: s for s in row["gold"]["spans"]}
    result = {}
    for group in row["gold"]["groups"]:
        key = tuple(sorted((spans[c]["start"], spans[c]["end"]) for c in group["cue_ids"]))
        result[key] = group["attribute"]
    return result


def training_groups(row: dict, *, max_groups: int = 512) -> list[CandidateGroup]:
    """Create train candidates: document proposals plus supervised gold positives."""
    # Keep preprocessing practical on CPU.  The positive gold groups are
    # unioned below, so reducing the mined negative pool cannot remove a
    # supervised positive.
    mined = mine_spans(row["document"], max_spans=min(192, max(64, max_groups // 2)))
    groups = mine_groups(mined, max_groups=max_groups)
    by_key = {tuple(sorted((s.start, s.end) for s in g.spans)): g for g in groups}
    for group in row["gold"]["groups"]:
        span_map = {s["span_id"]: s for s in row["gold"]["spans"]}
        spans = tuple(sorted((CandidateSpan(f"gold_{s}", span_map[s]["text"], span_map[s]["start"], span_map[s]["end"], 0.0) for s in group["cue_ids"]), key=lambda s: (s.start, s.end)))
        key = tuple(sorted((s.start, s.end) for s in spans))
        if key not in by_key:
            by_key[key] = CandidateGroup(f"gold_{group['group_id']}", spans, source="gold_supervised_positive")
    return list(by_key.values())


def oracle_groups(row: dict) -> list[CandidateGroup]:
    """Return gold groups for an explicitly labelled diagnostic upper bound.

    This function must never be used for the primary test run. It separates
    Laya classification quality from proposal recall.
    """
    spans = {s["span_id"]: s for s in row["gold"]["spans"]}
    groups = []
    for group in row["gold"]["groups"]:
        selected = tuple(sorted((CandidateSpan(f"gold_{cue}", spans[cue]["text"], spans[cue]["start"], spans[cue]["end"], 0.0) for cue in group["cue_ids"]), key=lambda s: (s.start, s.end)))
        groups.append(CandidateGroup(f"gold_{group['group_id']}", selected, source="gold_diagnostic_upper_bound"))
    return groups

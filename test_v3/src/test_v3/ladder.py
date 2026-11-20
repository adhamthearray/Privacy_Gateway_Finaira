from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LadderCandidate:
    candidate_id: str
    text: str
    level: int
    permitted: bool = True
    metadata: dict[str, Any] | None = None


def permitted_ladder(entity: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the policy-permitted ordered ladder with normalized positions."""
    candidates = [
        dict(item)
        for item in entity.get("candidates", [])
        if item.get("permitted", True) and not item.get("policy_forbidden", False)
    ]
    candidates.sort(key=lambda item: (int(item.get("level", 0)), str(item.get("candidate_id", ""))))
    if not candidates:
        raise ValueError(f"NO_PERMITTED_CANDIDATES:{entity.get('id')}")
    for index, candidate in enumerate(candidates):
        candidate["normalized_level"] = index
        candidate.setdefault("source_level", candidate.get("level", index))
    return candidates


def normalized_loss(level: int, candidate_count: int) -> float:
    if candidate_count <= 1:
        return 0.0
    return float(level) / float(candidate_count - 1)


def ladder_loss(ladders: Mapping[str, list[dict[str, Any]]], selection: Mapping[str, int]) -> float:
    return sum(
        normalized_loss(max(0, selection[entity_id]), len(candidates))
        for entity_id, candidates in ladders.items()
    )


def initial_selection(ladders: Mapping[str, list[dict[str, Any]]]) -> dict[str, int]:
    # -1 is the detector-only raw observation. It is deliberately absent from
    # every optimizer ladder, so the optimizer can never select the original.
    return {entity_id: -1 for entity_id in ladders}


def candidate_texts(ladders: Mapping[str, list[dict[str, Any]]], selection: Mapping[str, int]) -> dict[str, str]:
    return {
        entity_id: candidates[int(selection[entity_id])]["text"]
        for entity_id, candidates in ladders.items()
    }

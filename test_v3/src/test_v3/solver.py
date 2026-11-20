from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .ladder import ladder_loss, permitted_ladder


@dataclass
class SolveResult:
    status: str
    selection: dict[str, int]
    normalized_loss: float | None
    solver: str
    variables: int
    constraints: int
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _identity_groups(entities: list[Mapping[str, Any]]) -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for entity in entities:
        groups.setdefault(str(entity.get("identity_key") or entity["id"]), []).append(str(entity["id"]))
    return [ids for ids in groups.values() if len(ids) > 1]


def _is_cut(selection: Mapping[str, int], cut: Iterable[tuple[str, int]]) -> bool:
    pairs = list(cut)
    return bool(pairs) and all(selection.get(entity_id) == level for entity_id, level in pairs)


def _best_key(selection: Mapping[str, int], ladders: Mapping[str, list[dict[str, Any]]], tie_break: bool) -> tuple:
    return (
        round(ladder_loss(ladders, selection), 12),
        sum(level > 0 for level in selection.values()) if tie_break else 0,
        tuple((entity_id, selection[entity_id]) for entity_id in sorted(selection)),
    )


def _exhaustive(entities, ladders, min_levels, cuts, tie_break):
    ids = [str(entity["id"]) for entity in entities]
    domains = [range(max(0, min_levels.get(entity_id, 0)), len(ladders[entity_id])) for entity_id in ids]
    best = None
    for values in itertools.product(*domains):
        selection = dict(zip(ids, values))
        if any(_is_cut(selection, cut) for cut in cuts):
            continue
        if any(len({selection[entity_id] for entity_id in group}) > 1 for group in _identity_groups(entities)):
            continue
        key = _best_key(selection, ladders, tie_break)
        if best is None or key < best[0]:
            best = key, selection
    if best is None:
        return SolveResult("INFEASIBLE", {}, None, "exhaustive", sum(map(len, ladders.values())), len(cuts), "NO_FEASIBLE_ASSIGNMENT")
    return SolveResult("FEASIBLE", best[1], ladder_loss(ladders, best[1]), "exhaustive", sum(map(len, ladders.values())), len(cuts), "")


def solve_ladders(case: Mapping[str, Any], *, min_levels: Mapping[str, int] | None = None, cuts: list[list[tuple[str, int]]] | None = None, time_limit_seconds: float = 5.0, tie_break: bool = True) -> SolveResult:
    entities = list(case["entities"])
    ladders = {str(entity["id"]): permitted_ladder(entity) for entity in entities}
    min_levels = {str(key): int(value) for key, value in (min_levels or {}).items()}
    cuts = cuts or []
    # CP-SAT is the production path; exhaustive enumeration is deterministic
    # and keeps local unit tests independent of optional native wheels.
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return _exhaustive(entities, ladders, min_levels, cuts, tie_break)
    model = cp_model.CpModel()
    variables: dict[tuple[str, int], Any] = {}
    scale = 1_000_000
    objective_terms = []
    for entity in entities:
        entity_id = str(entity["id"])
        choices = []
        for level, _candidate in enumerate(ladders[entity_id]):
            var = model.NewBoolVar(f"x_{entity_id}_{level}")
            variables[(entity_id, level)] = var
            choices.append(var)
            objective_terms.append(int(round(level / max(1, len(ladders[entity_id]) - 1) * scale)) * var)
        model.Add(sum(choices) == 1)
        minimum = min_levels.get(entity_id, 0)
        for level in range(minimum):
            model.Add(variables[(entity_id, level)] == 0)
    for group in _identity_groups(entities):
        first = group[0]
        for other in group[1:]:
            if len(ladders[first]) != len(ladders[other]):
                return _exhaustive(entities, ladders, min_levels, cuts, tie_break)
            for level in range(len(ladders[first])):
                model.Add(variables[(first, level)] == variables[(other, level)])
    for cut in cuts:
        terms = [variables[(entity_id, level)] for entity_id, level in cut if (entity_id, level) in variables]
        if terms:
            model.Add(sum(terms) <= len(terms) - 1)
    # Deterministic single-worker search. Secondary tie-breaking is encoded by
    # a tiny deterministic level coefficient after normalized loss.
    if tie_break:
        objective_terms.extend((index + 1) * 1 * variables[(str(entity["id"]), level)] for index, entity in enumerate(entities) for level in range(len(ladders[str(entity["id"])])))
    model.Minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_seconds)
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveResult("INFEASIBLE", {}, None, "cp-sat", sum(map(len, ladders.values())), len(cuts), solver.StatusName(status))
    selection = {}
    for entity in entities:
        entity_id = str(entity["id"])
        selection[entity_id] = next(level for level in range(len(ladders[entity_id])) if solver.Value(variables[(entity_id, level)]))
    return SolveResult("FEASIBLE", selection, ladder_loss(ladders, selection), "cp-sat", sum(map(len, ladders.values())), len(cuts), solver.StatusName(status))

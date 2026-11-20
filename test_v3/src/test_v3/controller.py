from __future__ import annotations

import hashlib
import itertools
import json
import time
from typing import Any, Mapping

from .detector import DetectorResponse
from .ladder import initial_selection, ladder_loss, permitted_ladder
from .rendering import render_document
from .solver import solve_ladders


def _cache_key(case, rendered):
    payload = {"case": case["case_id"], "document": rendered["text"], "policy": case.get("policy", {})}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _terminal_selection(ladders):
    return {entity_id: len(candidates) - 1 for entity_id, candidates in ladders.items()}


def run_case(case: Mapping[str, Any], detector, *, max_iterations=8, max_detector_calls=40, solver_time_limit=5.0) -> dict[str, Any]:
    ladders = {str(entity["id"]): permitted_ladder(entity) for entity in case["entities"]}
    selection = initial_selection(ladders)
    cuts: list[list[tuple[str, int]]] = []
    cache: dict[str, dict[str, Any]] = {}
    iterations = []
    started = time.perf_counter()
    final_status = "UNRESOLVED"
    fallback_applied = False

    def ask(current):
        nonlocal fallback_applied
        rendered = render_document(case, current, ladders)
        request_case = dict(case)
        request_case["_selection"] = current
        key = _cache_key(request_case, rendered)
        if key in cache:
            response = DetectorResponse(**cache[key])
            response.latency_seconds = 0.0
            return rendered, response, True
        if sum(1 for _ in cache) >= max_detector_calls:
            return rendered, DetectorResponse("UNCERTAIN", error="DETECTOR_CALL_LIMIT"), False
        response = detector.predict(request_case, rendered)
        cache[key] = response.as_dict()
        return rendered, response, False

    for iteration in range(max_iterations):
        rendered, response, cached = ask(selection)
        item = {"iteration": iteration, "selection": dict(selection), "rendered_document": rendered["text"], "response": response.as_dict(), "cached": cached, "cuts_before": [list(map(list, cut)) for cut in cuts]}
        iterations.append(item)
        if response.decision == "NO_RISK":
            final_status = "NO_RISK_DETECTED" if iteration == 0 else "NO_RISK_AFTER_REPAIR"
            break
        if response.decision == "UNCERTAIN":
            if not fallback_applied:
                selection = _terminal_selection(ladders)
                fallback_applied = True
                continue
            final_status = "UNRESOLVED_UNCERTAIN"
            break
        group_ids = [span.get("entity_id") for span in response.evidence_spans if span.get("entity_id") in selection]
        group_ids = list(dict.fromkeys(group_ids))
        if not group_ids:
            # Evidence spans may be missing or may not map cleanly after a
            # replacement. Probe bounded subsets before applying fallback.
            probe_records = []
            entity_ids = list(selection)
            found_group = None
            for size in range(1, min(3, len(entity_ids)) + 1):
                for combo in itertools.combinations(entity_ids, size):
                    probe_selection = _terminal_selection(ladders)
                    for entity_id in combo:
                        probe_selection[entity_id] = selection[entity_id]
                    probe_rendered, probe_response, probe_cached = ask(probe_selection)
                    probe_records.append({"entity_ids": list(combo), "selection": probe_selection, "rendered_document": probe_rendered["text"], "response": probe_response.as_dict(), "cached": probe_cached})
                    if probe_response.decision == "RISK":
                        found_group = list(combo)
                        break
                if found_group:
                    break
            item["subset_probes"] = probe_records
            if found_group:
                group_ids = found_group
            elif not fallback_applied:
                selection = _terminal_selection(ladders)
                fallback_applied = True
                continue
            else:
                final_status = "UNRESOLVED_NO_EDITABLE_EVIDENCE"
                break
        # A risk detected on the raw observation (-1) forces at least the
        # first permitted generalization level; raw text is never a solver
        # choice.
        cut = [(entity_id, max(0, selection[entity_id])) for entity_id in group_ids]
        if cut not in cuts:
            cuts.append(cut)
        solved = solve_ladders(case, min_levels=selection, cuts=cuts, time_limit_seconds=solver_time_limit)
        item["solver"] = solved.as_dict()
        if solved.status != "FEASIBLE" or solved.selection == selection:
            selection = _terminal_selection(ladders)
            fallback_applied = True
            final_status = "UNRESOLVED_SOLVER_INFEASIBLE" if solved.status != "FEASIBLE" else "UNRESOLVED_NO_BROADER_PLAN"
            break
        selection = solved.selection
    else:
        final_status = "UNRESOLVED_MAX_ITERATIONS"

    final_rendered = render_document(case, selection, ladders)
    final_response = iterations[-1]["response"] if iterations else {}
    return {
        "case_id": case["case_id"],
        "language": case["language"],
        "initial_selection": initial_selection(ladders),
        "final_selection": selection,
        "initial_document": render_document(case, initial_selection(ladders), ladders)["text"],
        "final_document": final_rendered["text"],
        "normalized_loss": ladder_loss(ladders, selection),
        "status": final_status,
        "privacy_claim": "NO_GUARANTEE_FROM_NO_DETECTION",
        "fallback_applied": fallback_applied,
        "iterations": iterations,
        "cuts": [list(map(list, cut)) for cut in cuts],
        "detector_calls": len(cache),
        "detector_latency_seconds": sum(item["response"].get("latency_seconds", 0.0) for item in iterations),
        "solver_seconds": time.perf_counter() - started,
        "entities": case["entities"],
        "policy": case.get("policy", {}),
        "gold": case.get("gold", {}),
        "limitations": case.get("limitations", [])
    }

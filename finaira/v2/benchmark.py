"""Reproducible V2 benchmark and small-case exhaustive checks."""

from __future__ import annotations

import random
import time
from typing import Any

from .core import V2Optimizer, exhaustive_optimum


def synthetic_benchmark_request(entity_count: int, candidate_count: int = 5, seed: int = 20261118) -> dict[str, Any]:
    rng = random.Random(seed + entity_count + candidate_count)
    values = [f"age-{index}" for index in range(entity_count)]
    document = " ".join(values)
    entities = []
    cursor = 0
    for index, value in enumerate(values):
        start = document.find(value, cursor)
        cursor = start + len(value)
        candidates = []
        for candidate_index in range(candidate_count - 1):
            candidates.append({
                "candidate_id": f"b{index}-{candidate_index}",
                "text": f"band-{index}-{candidate_index}",
                "level_code": f"BAND_{candidate_index}",
                "utility_loss": round(candidate_index * 0.5 + rng.random() * 0.01, 6),
                "specificity": round(max(0.05, 0.9 - candidate_index * 0.15), 6),
            })
        candidates.append({
            "candidate_id": f"pseudo-{index}",
            "text": f"__FN_AGE_{index + 1:04d}__",
            "level_code": "TYPED_PSEUDONYM",
            "utility_loss": 2.0,
            "specificity": 0.0,
            "terminal_pseudonym": True,
        })
        entities.append({"id": f"e{index:04d}", "type": "AGE", "original": value, "start": start, "end": start + len(value), "metadata": {"synthetic_candidates": candidates}})
    return {"case_id": f"benchmark-{entity_count}", "task": "customer_demographic_summary", "document": document, "entities": entities, "synthetic_fixture": True}


def run_benchmarks(*, sizes: tuple[int, ...] = (5, 10, 20, 50, 100), candidate_count: int = 5, seed: int = 20261118) -> list[dict[str, Any]]:
    optimizer = V2Optimizer()
    rows = []
    for size in sizes:
        request = synthetic_benchmark_request(size, candidate_count, seed)
        started = time.perf_counter()
        baseline = optimizer.independent_baseline(request, max_utility_loss=float(size * 2))
        greedy = optimizer.greedy_baseline(request, max_utility_loss=float(size * 2))
        v2 = optimizer.v2_milp(request, max_utility_loss=float(size * 2))
        rows.append({
            "entities": size,
            "candidates_per_entity": candidate_count,
            "baseline_runtime_ms": baseline["metrics"]["runtime_ms"],
            "greedy_runtime_ms": greedy["metrics"]["runtime_ms"],
            "v2_runtime_ms": v2["metrics"]["runtime_ms"],
            "total_runtime_ms": round((time.perf_counter() - started) * 1000, 3),
            "variables": (v2.get("optimization") or {}).get("variables"),
            "constraints": (v2.get("optimization") or {}).get("constraints"),
            "solver_status": v2["metrics"].get("solver_status"),
            "specificity": v2["metrics"].get("total_specificity"),
            "utility_loss": v2["metrics"].get("total_utility_loss"),
            "pseudonym_count": v2["metrics"].get("pseudonymized_entity_count"),
            "feasible": v2["status"] == "FEASIBLE",
        })
    return rows


__all__ = ["synthetic_benchmark_request", "run_benchmarks", "exhaustive_optimum"]

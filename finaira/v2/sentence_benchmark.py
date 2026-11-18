"""Large deterministic sentence benchmark using verified repository values.

Templates are synthetic, but entity values are harvested from repository
sources and admitted only after exact/direct GeneralizationDB verification.
The benchmark never promotes a substring match into a benchmark entity.
"""

from __future__ import annotations

import csv
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .core import PRODUCTION_STATUSES, V2Optimizer
from finaira_generalization import GeneralizationDB


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "processed" / "finaira_generalization.db"


def _rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _admit(db: GeneralizationDB, entity_type: str, value: str, language: str, source: str) -> dict[str, Any] | None:
    value = str(value or "").strip()
    if not value:
        return None
    result = db.get_candidates(entity_type, value, output_language=language, include_review_candidates=False, input_language=language)
    exact = [candidate for candidate in result.get("candidates", []) if candidate.get("is_exact") and not candidate.get("is_suppression")]
    if result.get("resolution_status") not in PRODUCTION_STATUSES or len(exact) != 1:
        return None
    return {"value": value, "language": language, "entity_type": entity_type, "canonical_id": result.get("canonical_id"), "source": source, "resolution_status": result.get("resolution_status"), "exact_candidate_id": exact[0].get("candidate_id")}


def verified_value_pools(db_path: str | Path = DB_PATH, *, max_values_per_type: int = 20, seed: int = 20261118) -> dict[str, list[dict[str, Any]]]:
    """Harvest and validate large exact/direct pools from local source files."""
    db = GeneralizationDB(db_path)
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()

    def add(entity_type: str, value: str, language: str, source: str):
        key = (entity_type, value, language)
        if key in seen or len(pools[entity_type]) >= max_values_per_type * 2:
            return
        admitted = _admit(db, entity_type, value, language, source)
        if admitted:
            pools[entity_type].append(admitted); seen.add(key)

    for row in _rows(ROOT / "reports" / "bank_official_names_en_ar.csv"):
        add("BANK", row.get("official_name_en"), "en", "bank_official_names_en_ar.csv")
        add("BANK", row.get("official_name_ar"), "ar", "bank_official_names_en_ar.csv")
    for row in _rows(ROOT / "data" / "sources" / "natural_earth" / "ne_10m_admin_0_countries_v5.1.1.csv"):
        add("COUNTRY", row.get("name_en"), "en", "Natural Earth Admin 0")
        add("COUNTRY", row.get("name_ar"), "ar", "Natural Earth Admin 0")
    for row in _rows(ROOT / "data" / "sources" / "wikidata" / "wikidata_nationality_aliases_ar_en_v2.csv"):
        add("NATIONALITY", row.get("nationality"), row.get("language") or "en", "Wikidata P1549 nationality aliases")
    for row in _rows(ROOT / "reports" / "job_title_database" / "job_title_aliases.csv"):
        if str(row.get("enabled_for_lookup", "")).lower() not in {"1", "true", "yes"}:
            continue
        add("JOB_TITLE", row.get("alias_text"), row.get("language") or "en", "ESCO/ISCO job title aliases")
    for row in _rows(ROOT / "data" / "sources" / "government" / "government_alias_user_approvals.csv"):
        if str(row.get("approval_status", "")).upper() == "APPROVED_BY_USER":
            add("GOVERNMENT_ENTITY", row.get("alias"), row.get("language") or "en", "approved government aliases")
    for row in _rows(ROOT / "reports" / "ner_v1_generalization" / "corporation_unique_values.csv"):
        add("CORPORATION", row.get("value"), "ar" if any("\u0600" <= char <= "\u06ff" for char in row.get("value", "")) else "en", "NER corporation values validated against DB")

    # AGE and DATE are configured deterministic policy domains rather than
    # alias tables. They are admitted from the existing parser/configuration.
    for age in (18, 21, 28, 34, 45, 65, 75):
        pools["AGE"].append({"value": str(age), "language": "en", "entity_type": "AGE", "canonical_id": None, "source": "Finaira age-band configuration", "resolution_status": "VERIFIED", "exact_candidate_id": "EXACT"})
    for iso in ("2020-01-15", "2021-04-30", "2022-07-01", "2023-10-31", "2024-12-15", "2025-03-20"):
        pools["DATE"].append({"value": iso, "language": "en", "entity_type": "DATE", "canonical_id": None, "source": "Finaira deterministic date configuration", "resolution_status": "VERIFIED", "exact_candidate_id": "EXACT"})

    rng = random.Random(seed)
    for entity_type in list(pools):
        rng.shuffle(pools[entity_type])
        pools[entity_type] = pools[entity_type][:max_values_per_type]
    return dict(pools)


def _compose(language: str, values: dict[str, dict[str, Any]], index: int, task: str) -> dict[str, Any]:
    utility_profiles = {
        "professional_summary": {
            "JOB_TITLE": {"ISCO_UNIT": 0, "ISCO_MINOR": 1, "ISCO_SUB_MAJOR": 2, "ISCO_MAJOR": 3},
            "AGE": {}, "BANK": {}, "NATIONALITY": {}, "COUNTRY": {},
        },
        "customer_demographic_summary": {
            "AGE": {"NARROW_BAND": 0, "WIDE_BAND": 0.5, "BROAD_CATEGORY": 1},
            "NATIONALITY": {"SUBREGION": 0, "CONTINENT": 1},
            "COUNTRY": {"SUBREGION": 0, "REGION_UN": 0.5, "CONTINENT": 1},
            "JOB_TITLE": {}, "BANK": {},
        },
    }
    if language == "ar":
        fragments = [
            ("text", "أفاد العميل __FN_PERSON_0001__ أن عمره "), ("AGE", values["AGE"]["value"]),
            ("text", " سنة ويعمل كـ "), ("JOB_TITLE", values["JOB_TITLE"]["value"]),
            ("text", " في "), ("BANK", values["BANK"]["value"]),
            ("text", ". العميل "), ("NATIONALITY", values["NATIONALITY"]["value"]),
            ("text", " والحساب مرتبط بـ "), ("COUNTRY", values["COUNTRY"]["value"]), ("text", "."),
        ]
    else:
        fragments = [
            ("text", "Customer __FN_PERSON_0001__ is "), ("NATIONALITY", values["NATIONALITY"]["value"]),
            ("text", ", aged "), ("AGE", values["AGE"]["value"]),
            ("text", ", works as "), ("JOB_TITLE", values["JOB_TITLE"]["value"]),
            ("text", " at "), ("BANK", values["BANK"]["value"]),
            ("text", " and the account is associated with "), ("COUNTRY", values["COUNTRY"]["value"]), ("text", "."),
        ]
    parts = []
    entities = []
    cursor = 0
    for kind, value in fragments:
        parts.append(value)
        if kind != "text":
            entities.append({"id": f"s{index:04d}-{kind.lower()}", "type": kind, "original": value, "start": cursor, "end": cursor + len(value), "language": language, "identity_key": values[kind].get("canonical_id"), "metadata": {"utility_by_level": utility_profiles[task].get(kind, {})}})
        cursor += len(value)
    document = "".join(parts)
    return {"case_id": f"sentence-benchmark-{index:04d}", "task": task, "document": document, "entities": entities, "metadata": {"language": language, "source_records": {key: value.get("source") for key, value in values.items()}, "lookup_records": values}}


def generate_sentence_requests(*, count: int = 100, db_path: str | Path = DB_PATH, seed: int = 20261118) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pools = verified_value_pools(db_path, seed=seed)
    required = ("AGE", "JOB_TITLE", "BANK", "NATIONALITY", "COUNTRY")
    missing = {entity_type: len(pools.get(entity_type, [])) for entity_type in required if not pools.get(entity_type)}
    if missing:
        raise RuntimeError(f"INSUFFICIENT_VERIFIED_EXACT_POOLS:{missing}")
    rng = random.Random(seed)
    requests = []
    for index in range(count):
        language = "ar" if index % 2 else "en"
        task = "customer_demographic_summary" if language == "ar" else "professional_summary"
        values = {entity_type: rng.choice(pools[entity_type]) for entity_type in required}
        requests.append(_compose(language, values, index, task))
    manifest = {"count_requested": count, "seed": seed, "required_entity_types": list(required), "pool_counts": {key: len(value) for key, value in sorted(pools.items())}, "languages": {"en": (count + 1) // 2, "ar": count // 2}, "database_rule": "Every database-backed value was admitted only after MATCHED/VERIFIED exact/direct lookup; no substring-only values."}
    return requests, manifest


def run_sentence_benchmark(*, count: int = 100, max_utility_loss: float = 1.0, db_path: str | Path = DB_PATH, seed: int = 20261118) -> dict[str, Any]:
    requests, manifest = generate_sentence_requests(count=count, db_path=db_path, seed=seed)
    optimizer = V2Optimizer(db_path)
    started = time.perf_counter()
    rows = []
    method_counts = Counter()
    entity_counts = Counter()
    for request in requests:
        for entity in request["entities"]:
            entity_counts[entity["type"]] += 1
        comparison = optimizer.compare(request, max_utility_loss=max_utility_loss)
        for method in ("baseline", "greedy", "v2"):
            method_counts[(method, comparison[method]["status"])] += 1
        rows.append({"case_id": request["case_id"], "language": request["metadata"]["language"], "task": request["task"], "status_v1": comparison["baseline"]["status"], "status_greedy": comparison["greedy"]["status"], "status_v2": comparison["v2"]["status"], "v2_reason": comparison["v2"].get("reason"), "v1_specificity": comparison["baseline"]["metrics"].get("total_specificity"), "v2_specificity": comparison["v2"]["metrics"].get("total_specificity"), "v1_utility": comparison["baseline"]["metrics"].get("total_utility_loss"), "v2_utility": comparison["v2"]["metrics"].get("total_utility_loss"), "v2_runtime_ms": comparison["v2"]["metrics"].get("runtime_ms"), "reduction_pct": comparison["evaluation"].get("structural_disclosure_reduction_pct"), "v2_pseudonyms": comparison["v2"]["metrics"].get("pseudonymized_entity_count")})
    feasible = [row for row in rows if row["status_v2"] == "FEASIBLE"]
    reductions = [row["reduction_pct"] for row in feasible if row["reduction_pct"] is not None]
    database_entities = sum(1 for request in requests for entity in request["entities"] if entity["type"] in {"JOB_TITLE", "BANK", "NATIONALITY", "COUNTRY"})
    configured_entities = sum(1 for request in requests for entity in request["entities"] if entity["type"] in {"AGE", "DATE"})
    summary = {
        "sentences": len(rows), "entities": sum(entity_counts.values()), "entity_counts": dict(entity_counts),
        "database_backed_entities_exact_direct_validated": database_entities, "configured_entities": configured_entities,
        "v1_feasible": sum(row["status_v1"] == "FEASIBLE" for row in rows), "greedy_feasible": sum(row["status_greedy"] == "FEASIBLE" for row in rows), "v2_feasible": len(feasible),
        "average_v1_specificity": round(sum(row["v1_specificity"] or 0 for row in rows) / len(rows), 6) if rows else None,
        "average_v2_specificity": round(sum(row["v2_specificity"] or 0 for row in rows) / len(rows), 6) if rows else None,
        "average_v1_utility": round(sum(row["v1_utility"] or 0 for row in rows) / len(rows), 6) if rows else None,
        "average_v2_utility": round(sum(row["v2_utility"] or 0 for row in rows) / len(rows), 6) if rows else None,
        "total_v2_pseudonymized_entities": sum(row["v2_pseudonyms"] or 0 for row in rows),
        "average_v2_runtime_ms": round(sum(row["v2_runtime_ms"] or 0 for row in rows) / len(rows), 3) if rows else None,
        "average_structural_reduction_pct": round(sum(reductions) / len(reductions), 4) if reductions else None,
        "structural_reduction_unavailable_count": sum(row["reduction_pct"] is None for row in rows),
        "status_counts": {f"{method}:{status}": count for (method, status), count in sorted(method_counts.items())},
        "v2_failure_reasons": dict(Counter(row["v2_reason"] for row in rows if row["status_v2"] != "FEASIBLE")),
        "task_performance": "NOT_VALIDATED_NO_GROUND_TRUTH_EVALUATOR",
    }
    return {"manifest": manifest, "summary": summary, "rows": rows, "requests": requests, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}


__all__ = ["verified_value_pools", "generate_sentence_requests", "run_sentence_benchmark"]

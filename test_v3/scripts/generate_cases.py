from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO))

from finaira.v2.sentence_benchmark import verified_value_pools
from finaira_generalization import GeneralizationDB

DB_PATH = REPO / "data" / "processed" / "finaira_generalization.db"


def a(codepoints: str) -> str:
    """Build Arabic fixture text without depending on console encoding."""
    return "".join(chr(int(item, 16)) for item in codepoints.split())


AR = {
    "customer": a("0627 0644 0639 0645 064a 0644"),
    "age": a("0639 0645 0631 0647"),
    "year": a("0633 0646 0629"),
    "works": a("0648 064a 0639 0645 0644 0020 0643 0640"),
    "in": a("0641 064a"),
    "again": a("0645 0631 0629 0020 0623 062e 0631 0649"),
    "nationality": a("062c 0646 0633 064a 062a 0647"),
    "country": a("0648 0627 0644 062f 0648 0644 0629 0020 0627 0644 0645 0631 062a 0628 0637 0629 0020 0628 0627 0644 062d 0633 0627 0628"),
    "date": a("062a 0627 0631 064a 062e 0020 0627 0644 0637 0644 0628"),
    "nationality_label": a("0627 0644 062c 0646 0633 064a 0629"),
    "amount": a("0665 066c 0660 0660 0660 0020 062f 0648 0644 0627 0631"),
    "comma": a("060c"),
}
AR_AGES = [a("0662 0668"), a("0663 0665"), a("0664 0664"), a("0666 0665")]
EN_AGES = ["28", "35", "44", "65"]
DATES = ["2026-01-14", "2026-03-22", "2026-07-09", "2026-10-31"]


def _db_ladder(db: GeneralizationDB, entity_type: str, value: str, language: str, pseudo: str) -> tuple[list[dict], dict]:
    result = db.get_candidates(entity_type, value, output_language=language, input_language=language, include_review_candidates=False)
    if result.get("resolution_status") not in {"MATCHED", "VERIFIED"}:
        raise RuntimeError(f"V3_VALUE_NOT_EXACT_DIRECT:{entity_type}:{value}:{language}:{result.get('resolution_status')}")
    exact = [candidate for candidate in result.get("candidates", []) if candidate.get("is_exact") and not candidate.get("is_suppression")]
    if len(exact) != 1:
        raise RuntimeError(f"V3_VALUE_EXACT_CARDINALITY:{entity_type}:{value}:{len(exact)}")
    ladder = []
    for candidate in result.get("candidates", []):
        if candidate.get("is_exact") or candidate.get("is_suppression") or not candidate.get("representation"):
            continue
        ladder.append({
            "candidate_id": candidate["candidate_id"], "text": candidate["representation"], "level": len(ladder), "permitted": True,
            "source": candidate.get("source"), "verification_status": candidate.get("verification_status"),
            "metadata": {"level_code": candidate.get("level_code"), "taxonomy": candidate.get("taxonomy"), "taxonomy_code": candidate.get("taxonomy_code"), "canonical_id": result.get("canonical_id"), "source_entity_type": result.get("source_entity_type") or entity_type, "lookup_resolution_status": result.get("resolution_status"), "database_candidate_id": candidate.get("candidate_id")},
        })
    ladder.append({"candidate_id": f"{entity_type.lower()}-typed-pseudonym", "text": pseudo, "level": len(ladder), "permitted": True, "source": "Finaira case-scoped pseudonym fallback", "verification_status": "CONFIGURED", "terminal_pseudonym": True, "metadata": {"level_code": "TYPED_PSEUDONYM", "canonical_id": result.get("canonical_id")}})
    lookup = {"resolution_status": result.get("resolution_status"), "canonical_id": result.get("canonical_id"), "source_entity_type": result.get("source_entity_type"), "exact_candidate_id": exact[0].get("candidate_id"), "exact_verification_status": exact[0].get("verification_status"), "exact_source": exact[0].get("source"), "candidate_count_from_database": len(result.get("candidates", [])), "usable_generalization_count": len(ladder) - 1}
    return ladder, lookup


def _entry(pools: dict[str, list[dict]], entity_type: str, language: str, rng: random.Random, fallback: list[str] | None = None) -> tuple[str, str, str]:
    entries = [item for item in pools.get(entity_type, []) if item.get("language") == language and item.get("canonical_id")]
    if entries:
        item = rng.choice(entries)
        return str(item["value"]), language, str(item.get("source") or "verified Finaira source")
    if fallback:
        return rng.choice(fallback), language, "verified Finaira direct-value fallback"
    raise RuntimeError(f"NO_VERIFIED_VALUE_POOL:{entity_type}:{language}")


def make_case(index: int, language: str, risky: bool, rng: random.Random, db: GeneralizationDB, pools: dict[str, list[dict]]) -> dict:
    value_language = "ar" if language == "ar" else "en"
    age = rng.choice(AR_AGES if value_language == "ar" else EN_AGES)
    age_lang = value_language
    if value_language == "ar":
        job, job_lang, job_source = _entry(pools, "JOB_TITLE", "ar", rng)
    else:
        job, job_lang, job_source = "Software Engineer", "en", "verified Finaira direct-value fallback"
    nationality, nationality_lang, nationality_source = _entry(pools, "NATIONALITY", value_language, rng)
    country, country_lang, country_source = _entry(pools, "COUNTRY", value_language, rng)
    date = rng.choice(DATES)
    date_lang, date_source = "en", "Finaira deterministic date configuration"

    bank = bank_lang = bank_source = None
    bank_ladder = None
    bank_lookup = None
    for _ in range(30):
        candidate_bank, candidate_lang, candidate_source = _entry(pools, "BANK", value_language, rng)
        candidate_ladder, candidate_lookup = _db_ladder(db, "BANK", candidate_bank, candidate_lang, "__FN_BANK_0001__")
        if not risky or len(candidate_ladder) >= 2:
            bank, bank_lang, bank_source = candidate_bank, candidate_lang, candidate_source
            bank_ladder, bank_lookup = candidate_ladder, candidate_lookup
            break
    if bank is None:
        raise RuntimeError(f"NO_BANK_WITH_USABLE_GENERALIZATION:{language}")

    values = {
        "age": (age, age_lang, "Finaira age-band configuration", "AGE"),
        "job": (job, job_lang, job_source, "JOB_TITLE"),
        "nationality": (nationality, nationality_lang, nationality_source, "NATIONALITY"),
        "country": (country, country_lang, country_source, "COUNTRY"),
        "bank": (bank, bank_lang, bank_source, "BANK"),
        "date": (date, date_lang, date_source, "DATE"),
    }
    ladders, lookups = {}, {}
    for key, (value, lang, _source, entity_type) in values.items():
        ladders[key], lookups[key] = (bank_ladder, bank_lookup) if key == "bank" else _db_ladder(db, entity_type, value, lang, f"__FN_{entity_type}_0001__")

    chunks: list[str] = []
    entities: list[dict] = []

    def literal(text: str):
        chunks.append(text)

    def entity(key: str, entity_id: str | None = None):
        value, lang, source, entity_type = values[key]
        start = sum(len(item) for item in chunks)
        chunks.append(value)
        entities.append({"id": entity_id or f"{key}-1", "entity_type": entity_type, "original": value, "start": start, "end": start + len(value), "identity_key": f"{entity_type}:{lookups[key].get('canonical_id') or key}", "language": lang, "candidates": ladders[key], "lookup": lookups[key], "source_provenance": source})

    if language == "ar":
        literal(AR["customer"] + " __FN_PERSON_0001__" + AR["comma"] + " " + AR["age"] + " "); entity("age"); literal(" " + AR["year"] + " " + AR["works"] + " "); entity("job"); literal(" " + AR["in"] + " "); entity("bank")
        if index % 5 == 0: literal(" " + AR["again"] + AR["comma"] + " "); entity("bank", "bank-1-mention")
        literal(". " + AR["nationality"] + " "); entity("nationality"); literal(AR["comma"] + " " + AR["country"] + " "); entity("country"); literal(". " + AR["date"] + " "); entity("date"); literal(". " + AR["amount"] + ".")
    elif language == "mixed":
        literal("Customer __FN_PERSON_0001__ is "); entity("job"); literal(" at "); entity("bank")
        if index % 5 == 0: literal(" again "); entity("bank", "bank-1-mention")
        literal("; " + AR["nationality_label"] + ": "); entity("nationality"); literal("; country: "); entity("country"); literal("; application date: "); entity("date"); literal(". Monthly amount: $5,000.")
    else:
        literal("Customer __FN_PERSON_0001__ is "); entity("nationality"); literal(", aged "); entity("age"); literal(", works as a "); entity("job"); literal(" at "); entity("bank")
        if index % 5 == 0: literal(" again "); entity("bank", "bank-1-mention")
        literal("; country: "); entity("country"); literal("; application date: "); entity("date"); literal(". Monthly amount: $5,000.")

    hidden_attribute = rng.choice(["age", "occupation", "nationality", "income"]) if risky else "health"
    protected = ["age", "gender", "nationality", "education", "occupation", "income", "relationship", "health"]
    policy = {"hide": [hidden_attribute], "keep": [], "neutral": [item for item in protected if item != hidden_attribute]}
    if risky:
        groups = [["age-1", "date-1"], ["bank-1", "date-1"], ["age-1", "bank-1"]]
        attributes = ["age", "occupation", "nationality"]
        group, attribute = groups[index % 3], attributes[index % 3]
        gold = {"verified_groups": [{"entity_ids": group, "attribute": attribute, "break_level": 1, "rule_id": f"synthetic_rule_{index % 3 + 1}", "rationale": "Verified synthetic finite-rule case; this is not a claim about real-world identifiability."}], "status": "verified_synthetic_rule"}
    else:
        gold = {"verified_groups": [], "status": "verified_control"}
    return {"sample_id": f"test-v3-{index:03d}", "case_id": f"test-v3-{index:03d}", "language": language, "document": "".join(chunks), "profile": {"age": age, "gender": "female" if index % 2 else "male", "nationality": nationality, "education": "higher education", "occupation": job, "income": "middle", "relationship": "single", "health": "unknown"}, "policy": policy, "entities": entities, "gold": gold, "limitations": ["Gold groups are controlled synthetic finite rules; they are not claims about real-world identifiability.", "Every annotated value was admitted by a single MATCHED/VERIFIED exact/direct lookup against the local Finaira database; exact/raw values are observation-only and excluded from optimizer ladders."]}


def main():
    seed = 42
    rng = random.Random(seed)
    db = GeneralizationDB(DB_PATH)
    pools = verified_value_pools(DB_PATH, max_values_per_type=20, seed=seed)
    counts = [("ar", 36), ("mixed", 9), ("en", 5)]
    cases = []
    for language, count in counts:
        for _ in range(count):
            index = len(cases) + 1
            cases.append(make_case(index, language, index <= 30, rng, db, pools))
    output = ROOT / "cases" / "synthetic_cases.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    manifest = {"seed": seed, "cases": len(cases), "language_counts": {language: count for language, count in counts}, "risky_cases": 30, "control_cases": 20, "database_backed_entity_types": ["AGE", "JOB_TITLE", "BANK", "NATIONALITY", "COUNTRY", "DATE"], "database_lookup_rule": "Each annotated source value requires a single MATCHED/VERIFIED exact/direct lookup; exact/raw candidates are observation-only and excluded from optimizer ladders.", "repeated_identity_cases": sum(any(entity["id"] == "bank-1-mention" for entity in case["entities"]) for case in cases), "output": "cases/synthetic_cases.jsonl"}
    (ROOT / "cases" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

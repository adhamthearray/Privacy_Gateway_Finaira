"""Build a review-only queue for Arabic nationality variants.

This script never writes production nationality aliases. It only proposes a
candidate QID when a deterministic Arabic surface-form reduction reaches one
unique, already source-verified Wikidata P1549 alias.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira_generalization.db import NationalityAliasV2, make_engine
from finaira_generalization.normalization import normalize


def language_for(value: str) -> str:
    return "ar" if re.search(r"[\u0600-\u06ff]", value) else "en"


def surface_forms(value: str, language: str) -> list[tuple[str, str]]:
    """Return conservative review suggestions, not production mappings."""
    normalized = normalize(value, language)
    if language != "ar":
        return [(normalized, "exact-normalized-source-alias")]

    forms: list[tuple[str, str]] = [(normalized, "exact-normalized-source-alias")]
    stems = [(normalized, "")]
    if normalized.startswith("ال") and len(normalized) > 2:
        stems.append((normalized[2:], "remove-arabic-definite-article"))

    expanded = list(stems)
    for stem, rule in stems:
        if stem.endswith(("ين", "ون")) and len(stem) > 4:
            expanded.append((stem[:-2], (rule + "+" if rule else "") + "remove-masculine-plural-suffix"))
        if stem.endswith("ة") and len(stem) > 3:
            expanded.append((stem[:-1], (rule + "+" if rule else "") + "remove-feminine-ending"))

    for form, rule in expanded:
        if form and (form, rule) not in forms:
            forms.append((form, rule))
    return forms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, default=Path("reports/ner_v1_generalization/coverage_nationality.csv"))
    parser.add_argument("--db", type=Path, default=Path("data/processed/finaira_generalization.db"))
    parser.add_argument("--output", type=Path, default=Path("reports/nationality_improvement/nationality_variant_review_queue.csv"))
    args = parser.parse_args()

    with args.coverage.open(encoding="utf-8", newline="") as handle:
        missing = [row for row in csv.DictReader(handle) if row["coverage_category"] != "MATCHED_OR_VERIFIED"]

    prior_reviews = {}
    if args.output.exists():
        with args.output.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("corpus_value", ""), row.get("candidate_qid", ""), row.get("derivation_rule", ""))
                prior_reviews[key] = (row.get("review_decision", "PENDING"), row.get("evidence_reference", ""))

    aliases: dict[tuple[str, str], list[NationalityAliasV2]] = defaultdict(list)
    with Session(make_engine(args.db)) as session:
        for row in session.scalars(select(NationalityAliasV2)).all():
            if row.verification_status == "SOURCE_VERIFIED":
                aliases[(row.language, row.normalized_alias)].append(row)

    fields = [
        "corpus_value",
        "span_count",
        "language",
        "base_alias",
        "candidate_qid",
        "candidate_iso2",
        "source_property",
        "derivation_rule",
        "suggestion_status",
        "review_decision",
        "evidence_reference",
    ]
    output_rows = []
    for row in missing:
        value = row["value"]
        language = language_for(value)
        suggestions = []
        for form, rule in surface_forms(value, language):
            candidates = aliases.get((language, form), [])
            qids = {candidate.country_qid for candidate in candidates}
            if len(qids) == 1:
                candidate = next(candidate for candidate in candidates if candidate.country_qid in qids)
                suggestions.append((candidate, form, rule or "exact-normalized-source-alias"))

        if not suggestions:
            decision, evidence = prior_reviews.get((value, "", "NO_UNIQUE_SOURCE_BACKED_BASE_ALIAS"), ("PENDING", ""))
            output_rows.append({
                "corpus_value": value,
                "span_count": row["span_count"],
                "language": language,
                "base_alias": "",
                "candidate_qid": "",
                "candidate_iso2": "",
                "source_property": "",
                "derivation_rule": "NO_UNIQUE_SOURCE_BACKED_BASE_ALIAS",
                "suggestion_status": "NO_SUGGESTION",
                "review_decision": decision,
                "evidence_reference": evidence,
            })
            continue

        seen = set()
        for candidate, base_alias, rule in suggestions:
            key = (candidate.country_qid, rule)
            if key in seen:
                continue
            seen.add(key)
            review_key = (value, candidate.country_qid, rule)
            decision, evidence = prior_reviews.get(review_key, ("PENDING", ""))
            output_rows.append({
                "corpus_value": value,
                "span_count": row["span_count"],
                "language": language,
                "base_alias": candidate.alias_text,
                "candidate_qid": candidate.country_qid,
                "candidate_iso2": candidate.iso2,
                "source_property": "Wikidata P1549; source alias row",
                "derivation_rule": rule,
                "suggestion_status": "REVIEW_ONLY",
                "review_decision": decision,
                "evidence_reference": evidence,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(output_rows, key=lambda row: (-int(row["span_count"]), row["corpus_value"], row["derivation_rule"])))
    print({
        "output": str(args.output),
        "missing_values": len(missing),
        "review_rows": len(output_rows),
        "suggested_values": len({row["corpus_value"] for row in output_rows if row["suggestion_status"] == "REVIEW_ONLY"}),
        "suggested_spans": sum(int(row["span_count"]) for row in output_rows if row["suggestion_status"] == "REVIEW_ONLY"),
    })


if __name__ == "__main__":
    main()

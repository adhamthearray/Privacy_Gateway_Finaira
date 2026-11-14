"""Audit distinct finaira_ner_v1 values against the local generalization DB."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira_generalization.age_date import parse_age, parse_date
from finaira_generalization.db import (
    Bank,
    BankAlias,
    GovernmentAlias,
    NaturalEarthCountry,
    NaturalEarthCountryAlias,
    NationalityAliasV2,
    NationalityGeoJoin,
    OccupationAlias,
    Organization,
    OrganizationAlias,
    OrganizationExclusion,
    make_engine,
)
from finaira_generalization.normalization import normalize
from sqlalchemy import select
from sqlalchemy.orm import Session


ENTITY_TYPES = (
    "BANK",
    "COUNTRY",
    "NATIONALITY",
    "CORPORATION",
    "ORGANIZATION",
    "UNIVERSITY",
    "GOVERNMENT_ENTITY",
    "JOB_TITLE",
    "AGE",
    "DATE",
)
INPUT_ENTITY_TYPES = set(ENTITY_TYPES) | {"OCCUPATION"}
SUPPORTED = set(ENTITY_TYPES)
STATUS_RANK = {
    "MATCHED": 6,
    "VERIFIED": 6,
    "REVIEW_ONLY": 5,
    "AMBIGUOUS": 4,
    "EXCLUDED": 3,
    "NOT_FOUND": 2,
    "INVALID_INPUT": 1,
    "AMBIGUOUS_DATE": 1,
    "UNSUPPORTED_ENTITY_TYPE": 0,
}


def _ids(index: dict[tuple[str, str], set[str]], language: str, value: str) -> set[str]:
    return index.get((language, normalize(value, language)), set())


def _occupation_phrase_key(value: str, language: str) -> str:
    normalized = normalize(value, language)
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _occupation_alias_variants(alias_text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*/\s*", alias_text) if part.strip()]


def _result(status: str, reason: str | None, language: str, canonical_id=None, levels=(), exact=False, non_suppression=False, verification=()):
    return {
        "resolution_status": status,
        "reason_code": reason or "",
        "lookup_language": language,
        "canonical_id": canonical_id or "",
        "candidate_levels": "|".join(levels),
        "has_exact_candidate": bool(exact),
        "has_non_suppression_candidate": bool(non_suppression),
        "verification_statuses": "|".join(sorted(set(verification))),
    }


class CoverageIndex:
    def __init__(self, db_path: Path):
        self.session = Session(make_engine(db_path))
        self.ne = self.session.scalars(select(NaturalEarthCountry)).all()
        self.ne_by_name: dict[tuple[str, str], list[NaturalEarthCountry]] = defaultdict(list)
        self.country_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.ne:
            if row.name_ar:
                self.ne_by_name[("ar", normalize(row.name_ar, "ar"))].append(row)
            if row.name_en:
                self.ne_by_name[("en", normalize(row.name_en, "en"))].append(row)
            if row.iso_a2 and row.iso_a2 != "-99":
                self.ne_by_name[("ar", row.iso_a2.casefold())].append(row)
                self.ne_by_name[("en", row.iso_a2.casefold())].append(row)
        for alias in self.session.scalars(select(NaturalEarthCountryAlias)).all():
            if alias.enabled_for_lookup:
                self.country_alias[(alias.language, alias.normalized_alias)].add(alias.natural_earth_id)

        self.bank_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.bank_canonical: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.session.scalars(select(BankAlias)).all():
            if row.enabled_for_lookup:
                self.bank_alias[(row.language, row.normalized_alias)].add(row.bank_id)
        for row in self.session.scalars(select(Bank)).all():
            if row.name_en:
                self.bank_canonical[("en", normalize(row.name_en, "en"))].add(row.bank_id)
            if row.name_ar:
                self.bank_canonical[("ar", normalize(row.name_ar, "ar"))].add(row.bank_id)

        self.nat_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.session.scalars(select(NationalityAliasV2)).all():
            self.nat_alias[(row.language, row.normalized_alias)].add(row.country_qid)
        self.nat_join = {row.country_qid: row for row in self.session.scalars(select(NationalityGeoJoin)).all()}

        self.org_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.session.scalars(select(OrganizationAlias)).all():
            if row.enabled_for_lookup:
                self.org_alias[(row.language, row.normalized_alias)].add(row.organization_qid)
        self.orgs = {row.organization_qid: row for row in self.session.scalars(select(Organization)).all()}
        self.org_exclusions = {row.organization_qid for row in self.session.scalars(select(OrganizationExclusion)).all()}

        self.gov_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.session.scalars(select(GovernmentAlias)).all():
            if row.enabled_for_lookup:
                self.gov_alias[(row.language, row.normalized_alias)].add(row.entity_id)

        self.occupation_alias: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.occupation_alias_variant: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.occupation_phrase: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in self.session.scalars(select(OccupationAlias)).all():
            if row.review_status in {"OFFICIAL", "REVIEWED"}:
                self.occupation_alias[(row.language, row.normalized_alias)].add(row.occupation_id)
                for variant in _occupation_alias_variants(row.alias_text):
                    variant_key = normalize(variant, row.language)
                    self.occupation_alias_variant[(row.language, variant_key)].add(row.occupation_id)
                    phrase = _occupation_phrase_key(variant, row.language)
                    if phrase:
                        self.occupation_phrase[(row.language, phrase)].add(row.occupation_id)

    def close(self):
        self.session.close()

    def lookup(self, entity_type: str, value: str) -> dict:
        if entity_type == "COUNTRY":
            attempts = []
            for language in ("ar", "en"):
                alias_ids = self.country_alias.get((language, normalize(value, language)), set())
                if alias_ids:
                    rows = [self.session.get(NaturalEarthCountry, natural_earth_id) for natural_earth_id in sorted(alias_ids)]
                else:
                    rows = []
                    seen = set()
                    for row in self.ne_by_name.get((language, normalize(value, language)), []):
                        if row.natural_earth_id not in seen:
                            rows.append(row)
                            seen.add(row.natural_earth_id)
                if len(rows) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("SUPPRESSED",)))
                elif len(rows) == 1:
                    attempts.append(_result("MATCHED", None, language, rows[0].iso_a2 or rows[0].natural_earth_id, levels=("EXACT", "SUBREGION", "REGION_UN", "CONTINENT", "SUPPRESSED"), exact=True, non_suppression=True, verification=("SOURCE_VERIFIED",)))
                else:
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_COUNTRY", language, levels=("SUPPRESSED",)))
            return self._choose(attempts)
        if entity_type == "NATIONALITY":
            attempts = []
            for language in ("ar", "en"):
                qids = _ids(self.nat_alias, language, value)
                if len(qids) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("SUPPRESSED",)))
                elif not qids:
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_NATIONALITY", language, levels=("SUPPRESSED",)))
                else:
                    qid = next(iter(qids))
                    join = self.nat_join.get(qid)
                    if join and join.join_status in {"MATCHED_QID", "MATCHED_ISO"}:
                        attempts.append(_result("MATCHED", None, language, qid, levels=("EXACT", "SUBREGION", "CONTINENT", "SUPPRESSED"), exact=True, non_suppression=True, verification=("SOURCE_VERIFIED",)))
                    else:
                        attempts.append(_result("REVIEW_ONLY", "NATURAL_EARTH_JOIN_UNRESOLVED", language, qid, levels=("SUPPRESSED",)))
            return self._choose(attempts)
        if entity_type == "BANK":
            attempts = []
            for language in ("ar", "en"):
                ids = _ids(self.bank_alias, language, value) or _ids(self.bank_canonical, language, value)
                if len(ids) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("BANKING_INSTITUTION", "FINANCIAL_INSTITUTION", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                elif len(ids) == 1:
                    attempts.append(_result("MATCHED", None, language, next(iter(ids)), levels=("EXACT", "FINANCE_MODEL", "BANKING_INSTITUTION", "FINANCIAL_INSTITUTION", "SUPPRESSED"), exact=True, non_suppression=True, verification=("SOURCE_VERIFIED", "CONFIGURED")))
                else:
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_BANK", language, levels=("BANKING_INSTITUTION", "FINANCIAL_INSTITUTION", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
            return self._choose(attempts)
        if entity_type == "GOVERNMENT_ENTITY":
            attempts = []
            for language in ("ar", "en"):
                ids = _ids(self.gov_alias, language, value)
                if len(ids) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("GOVERNMENT_ENTITY_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                elif len(ids) == 1:
                    attempts.append(_result("REVIEW_ONLY", None, language, next(iter(ids)), levels=("EXACT", "GOVERNMENT_ENTITY_GENERIC", "SUPPRESSED"), exact=True, non_suppression=True, verification=("REVIEW_REQUIRED", "CONFIGURED")))
                else:
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_GOVERNMENT_ENTITY", language, levels=("GOVERNMENT_ENTITY_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
            return self._choose(attempts)
        if entity_type in {"CORPORATION", "ORGANIZATION", "UNIVERSITY"}:
            attempts = []
            for language in ("ar", "en"):
                ids = _ids(self.org_alias, language, value)
                if len(ids) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("ORGANIZATION_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                elif not ids:
                    fallback = "University" if entity_type == "UNIVERSITY" else "Company" if entity_type == "CORPORATION" else "Organization"
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_ORGANIZATION", language, levels=("ORGANIZATION_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                else:
                    oid = next(iter(ids))
                    org = self.orgs[oid]
                    if oid in self.org_exclusions:
                        attempts.append(_result("EXCLUDED", "EXCLUDED_ORGANIZATION", language, levels=("ORGANIZATION_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                    elif entity_type in {"CORPORATION", "UNIVERSITY"} and org.semantic_kind != entity_type:
                        attempts.append(_result("NOT_FOUND", "ENTITY_KIND_MISMATCH", language, levels=("ORGANIZATION_GENERIC", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
                    else:
                        verified = org.identity_verification_status in {"VERIFIED", "APPROVED", "OFFICIAL"} and org.import_decision in {"VERIFIED", "APPROVED"}
                        attempts.append(_result("MATCHED" if verified else "REVIEW_ONLY", None, language, oid, levels=("EXACT", "ORGANIZATION_GENERIC", "SUPPRESSED"), exact=True, non_suppression=True, verification=(org.identity_verification_status,)))
            return self._choose(attempts)
        if entity_type == "OCCUPATION":
            entity_type = "JOB_TITLE"
        if entity_type == "JOB_TITLE":
            attempts = []
            for language in ("ar", "en"):
                ids, method, matched_phrase = self._occupation_lookup(value, language)
                if len(ids) > 1:
                    attempts.append(_result("AMBIGUOUS", "ALIAS_COLLISION", language, levels=("SUPPRESSED",)))
                elif len(ids) == 1:
                    shortened = method == "LONGEST_PHRASE_MATCH"
                    attempts.append(_result("VERIFIED", "LONGEST_PHRASE_MATCH" if shortened else None, language, next(iter(ids)), levels=("EXACT", "ISCO_UNIT", "ISCO_MINOR", "ISCO_SUB_MAJOR", "ISCO_MAJOR", "SUPPRESSED"), exact=not shortened, non_suppression=True, verification=("OFFICIAL",)))
                else:
                    attempts.append(_result("NOT_FOUND", "UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK", language, levels=("JOB_TITLE_1", "JOB_TITLE_2", "SUPPRESSED"), non_suppression=True, verification=("CONFIGURED",)))
            return self._choose(attempts)
        if entity_type == "AGE":
            try:
                parse_age(value)
                return _result("VERIFIED", None, "ar", levels=("EXACT", "NARROW_BAND", "WIDE_BAND", "BROAD_CATEGORY", "SUPPRESSED"), exact=True, non_suppression=True, verification=("CONFIGURED",))
            except ValueError:
                return _result("INVALID_INPUT", "INVALID_INPUT", "ar")
        if entity_type == "DATE":
            try:
                parse_date(value)
                return _result("VERIFIED", None, "ar", levels=("EXACT", "MONTH", "QUARTER", "YEAR", "SUPPRESSED"), exact=True, non_suppression=True, verification=("CONFIGURED",))
            except ValueError as exc:
                return _result(str(exc), str(exc), "ar")
        return _result("UNSUPPORTED_ENTITY_TYPE", "UNSUPPORTED_ENTITY_TYPE", "ar")

    def _occupation_lookup(self, value: str, language: str) -> tuple[set[str], str, str]:
        ids = _ids(self.occupation_alias, language, value)
        phrase = _occupation_phrase_key(value, language)
        if ids:
            return ids, "EXACT_ALIAS", value
        ids = _ids(self.occupation_alias_variant, language, value)
        if ids:
            return ids, "ALIAS_VARIANT", value
        if phrase:
            ids = self.occupation_phrase.get((language, phrase), set())
            if ids:
                return ids, "NORMALIZED_FULL_PHRASE", phrase
        tokens = phrase.split()
        for size in range(len(tokens) - 1, 0, -1):
            found: list[tuple[str, set[str]]] = []
            for start in range(0, len(tokens) - size + 1):
                candidate = " ".join(tokens[start:start + size])
                candidate_ids = self.occupation_phrase.get((language, candidate), set())
                if candidate_ids:
                    found.append((candidate, candidate_ids))
            if found:
                return set().union(*(candidate_ids for _, candidate_ids in found)), "LONGEST_PHRASE_MATCH", " | ".join(candidate for candidate, _ in found)
        return set(), "NO_MATCH", ""

    @staticmethod
    def _choose(attempts: list[dict]) -> dict:
        return max(attempts, key=lambda row: (STATUS_RANK.get(row["resolution_status"], -1), int(row["has_exact_candidate"]), int(row["has_non_suppression_candidate"]), row["lookup_language"]))


def category(row: dict) -> str:
    status = row["resolution_status"]
    if status in {"MATCHED", "VERIFIED"}:
        return "MATCHED_OR_VERIFIED"
    if status == "REVIEW_ONLY":
        return "REVIEW_ONLY"
    if status == "AMBIGUOUS":
        return "AMBIGUOUS"
    if status == "UNSUPPORTED_ENTITY_TYPE":
        return "OUT_OF_SCOPE"
    if status == "NOT_FOUND" and row["has_non_suppression_candidate"]:
        return "GENERIC_FALLBACK_ONLY"
    if status == "NOT_FOUND" and row["candidate_levels"] == "SUPPRESSED":
        return "SUPPRESSION_ONLY"
    return "INVALID_OR_UNRESOLVED"


def next_action(entity_type: str, result_category: str) -> str:
    if result_category == "MATCHED_OR_VERIFIED":
        return "none"
    if result_category == "GENERIC_FALLBACK_ONLY":
        return {"BANK": "verify and add bank alias", "CORPORATION": "review organization identity and alias", "GOVERNMENT_ENTITY": "review government identity and alias"}.get(entity_type, "add verified alias")
    if result_category == "SUPPRESSION_ONLY":
        return {"COUNTRY": "verify Natural Earth/Wikidata country alias or ISO mapping", "NATIONALITY": "add verified Wikidata P1549 demonym if available", "JOB_TITLE": "add verified ESCO/ISCO alias", "OCCUPATION": "add verified ESCO/ISCO alias", "DATE": "supply or define a deterministic date format"}.get(entity_type, "add verified alias")
    if result_category == "REVIEW_ONLY":
        return "complete source review; do not auto-promote"
    if result_category == "AMBIGUOUS":
        return "resolve alias collision with context or explicit review"
    if result_category == "OUT_OF_SCOPE":
        return "not in current generalization API"
    return "validate input format or source evidence"


def review_source(entity_type: str) -> str:
    return {
        "BANK": "handoff/input/bank/banks_FINAL_evidence.csv plus regulator evidence",
        "COUNTRY": "Natural Earth Admin-0 + Wikidata label/alias/QID evidence",
        "NATIONALITY": "Wikidata P1549 Arabic/English demonym evidence",
        "CORPORATION": "handoff/input/organization Wikidata directory + approval evidence",
        "ORGANIZATION": "handoff/input/organization Wikidata directory + approval evidence",
        "UNIVERSITY": "handoff/input/organization Wikidata directory + approval evidence",
        "GOVERNMENT_ENTITY": "handoff/input/government seed + official identity evidence",
        "JOB_TITLE": "existing ESCO/ISCO source files and alias provenance",
        "OCCUPATION": "existing ESCO/ISCO source files and alias provenance",
        "AGE": "config age bands and deterministic parser policy",
        "DATE": "date format context or explicit caller policy",
    }[entity_type]


def read_dataset(dataset: Path) -> dict[str, Counter[str]]:
    values: dict[str, Counter[str]] = defaultdict(Counter)
    details: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: {"files": set(), "splits": set(), "origins": set()})
    for path in sorted(dataset.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                for span in row.get("spans", []):
                    raw_entity_type = span["label"]
                    if raw_entity_type not in INPUT_ENTITY_TYPES:
                        continue
                    entity_type = "JOB_TITLE" if raw_entity_type == "OCCUPATION" else raw_entity_type
                    value = span["text"]
                    values[entity_type][value] += 1
                    details[(entity_type, value)]["files"].add(path.name)
                    details[(entity_type, value)]["splits"].add(row.get("split", ""))
                    details[(entity_type, value)]["origins"].add(row.get("origin", ""))
    return values, details


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=Path("data/processed/finaira_generalization.db"))
    parser.add_argument("--output", type=Path, default=Path("reports/ner_v1_generalization"))
    args = parser.parse_args()
    values, details = read_dataset(args.dataset)
    index = CoverageIndex(args.db)
    rows = []
    for entity_type in ENTITY_TYPES:
        for value, span_count in values[entity_type].items():
            result = index.lookup(entity_type, value)
            result_category = category(result)
            context = details[(entity_type, value)]
            rows.append({
                "entity_type": entity_type,
                "value": value,
                "span_count": span_count,
                "source_files": ";".join(sorted(context["files"])),
                "splits": ";".join(sorted(context["splits"])),
                "origins": ";".join(sorted(context["origins"])),
                **result,
                "coverage_category": result_category,
                "next_action": next_action(entity_type, result_category),
            })
    index.close()
    args.output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (args.output / "coverage_values.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["entity_type"], -row["span_count"], row["value"])))

    summary = []
    for entity_type in ENTITY_TYPES:
        entity_rows = [row for row in rows if row["entity_type"] == entity_type]
        spans = sum(row["span_count"] for row in entity_rows)
        counts = Counter(row["coverage_category"] for row in entity_rows)
        span_counts = Counter()
        for row in entity_rows:
            span_counts[row["coverage_category"]] += row["span_count"]
        item = {
            "entity_type": entity_type,
            "unique_values": len(entity_rows),
            "spans": spans,
        }
        for key in ("MATCHED_OR_VERIFIED", "REVIEW_ONLY", "AMBIGUOUS", "GENERIC_FALLBACK_ONLY", "SUPPRESSION_ONLY", "INVALID_OR_UNRESOLVED", "OUT_OF_SCOPE"):
            item[f"{key.lower()}_unique"] = counts[key]
            item[f"{key.lower()}_spans"] = span_counts[key]
            item[f"{key.lower()}_unique_pct"] = round(100 * counts[key] / len(entity_rows), 2) if entity_rows else 0
            item[f"{key.lower()}_span_pct"] = round(100 * span_counts[key] / spans, 2) if spans else 0
        summary.append(item)
        with (args.output / f"coverage_{entity_type.lower()}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(sorted(entity_rows, key=lambda row: (-row["span_count"], row["coverage_category"], row["value"])))
        missing = [row for row in entity_rows if row["coverage_category"] != "MATCHED_OR_VERIFIED"]
        with (args.output / f"missing_{entity_type.lower()}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(sorted(missing, key=lambda row: (-row["span_count"], row["coverage_category"], row["value"])))

    summary_fields = list(summary[0])
    with (args.output / "coverage_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary)

    # This is an evidence-preserving work queue, not an automatic alias importer.
    # Keep every unresolved value and its frequency visible so a later reviewer can
    # attach a source-backed alias without promoting corpus text by itself.
    review_fields = [
        "entity_type",
        "value",
        "span_count",
        "source_files",
        "splits",
        "origins",
        "coverage_category",
        "resolution_status",
        "reason_code",
        "canonical_id",
        "lookup_language",
        "next_action",
        "reviewer_guidance",
        "candidate_source",
        "review_decision",
        "evidence_reference",
    ]
    review_rows = []
    for row in rows:
        if row["coverage_category"] == "MATCHED_OR_VERIFIED":
            continue
        review_rows.append({
            key: row.get(key, "") for key in review_fields[:-4]
        } | {
            "reviewer_guidance": "Do not promote until the candidate identity and source evidence are verified.",
            "candidate_source": review_source(row["entity_type"]),
            "review_decision": "PENDING",
            "evidence_reference": "",
        })
    with (args.output / "alias_review_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(sorted(review_rows, key=lambda row: (row["entity_type"], -int(row["span_count"]), row["value"])))

    lines = [
        "# finaira_ner_v1 generalization coverage audit",
        "",
        "This report compares every distinct value in the supported generalization labels against the local SQLite database. Percentages are reported by unique value and by annotated span frequency.",
        "",
        "Categories: `MATCHED_OR_VERIFIED` is production source/configuration coverage; `REVIEW_ONLY` is present but gated; `AMBIGUOUS` has a collision; `GENERIC_FALLBACK_ONLY` has a safe generic candidate but no exact identity; `SUPPRESSION_ONLY` has no usable non-suppression candidate; `OUT_OF_SCOPE` is not a current database entity type.",
        "",
        "| Entity | Unique | Spans | Matched/verified | Review | Ambiguous | Generic fallback | Suppression/invalid | Out of scope |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(f"| {item['entity_type']} | {item['unique_values']:,} | {item['spans']:,} | {item['matched_or_verified_unique']:,} ({item['matched_or_verified_unique_pct']:.2f}%) | {item['review_only_unique']:,} ({item['review_only_unique_pct']:.2f}%) | {item['ambiguous_unique']:,} ({item['ambiguous_unique_pct']:.2f}%) | {item['generic_fallback_only_unique']:,} ({item['generic_fallback_only_unique_pct']:.2f}%) | {item['suppression_only_unique'] + item['invalid_or_unresolved_unique']:,} ({item['suppression_only_unique_pct'] + item['invalid_or_unresolved_unique_pct']:.2f}%) | {item['out_of_scope_unique']:,} |")
    lines += ["", "## Highest-frequency gaps", ""]
    for entity_type in ENTITY_TYPES:
        gaps = sorted([row for row in rows if row["entity_type"] == entity_type and row["coverage_category"] != "MATCHED_OR_VERIFIED"], key=lambda row: -row["span_count"])[:15]
        if not gaps:
            continue
        lines.append(f"### {entity_type}")
        lines.append("")
        lines.append("| Value | Spans | Category | Reason | Next action |")
        lines.append("|---|---:|---|---|---|")
        for row in gaps:
            safe_value = row["value"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {safe_value} | {row['span_count']:,} | {row['coverage_category']} | {row['reason_code'] or '-'} | {row['next_action']} |")
        lines.append("")
    (args.output / "coverage_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "entities": {item["entity_type"]: item["unique_values"] for item in summary}, "coverage_values": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

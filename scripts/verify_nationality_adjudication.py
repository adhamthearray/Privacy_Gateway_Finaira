"""Verify the supplied nationality adjudication plan against repository sources.

The verifier is deliberately conservative. It approves only source-backed
P1549 bases with a reproducible, narrow Arabic derivation, a unique QID, a
valid Natural Earth join, collision-free normalization, and valid NATIONALITY
span offsets. The plan's non-routine groups remain pending.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from finaira_generalization.db import (  # noqa: E402
    NaturalEarthCountry,
    NationalityAliasV2,
    NationalityCountry,
    NationalityGeoJoin,
    make_engine,
)
from finaira_generalization.normalization import normalize  # noqa: E402


SOURCE_CSV = ROOT / "data/sources/wikidata/wikidata_nationality_aliases_ar_en_v2.csv"
QUEUE_CSV = ROOT / "reports/nationality_improvement/nationality_variant_review_queue.csv"
PLAN_CSV = ROOT / "Finaira_Nationality_Codex_Handoff/nationality_adjudication_plan.csv"
DATASET = Path(r"C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1")
POLICY_ID = "AR-NATIONALITY-INFLECTION-V1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def qid(value: str) -> str:
    match = re.search(r"\bQ\d+\b", value or "")
    return match.group(0) if match else ""


def derivation_check(corpus_value: str, base_alias: str, rule: str) -> tuple[bool, str]:
    value = normalize(corpus_value, "ar")
    base = normalize(base_alias, "ar")
    stem = value
    applied = []
    if "remove-arabic-definite-article" in rule:
        if not stem.startswith("ال"):
            return False, "missing-definite-article"
        stem = stem[2:]
        applied.append("DEFINITE_ARTICLE")
    if "remove-masculine-plural-suffix" in rule:
        if not stem.endswith(("ين", "ون")):
            return False, "missing-masculine-plural-suffix"
        stem = stem[:-2]
        applied.append("MASCULINE_PLURAL")
    if "remove-feminine-ending" in rule:
        if not stem.endswith(("ة", "ه")):
            return False, "missing-feminine-ending"
        stem = stem[:-1]
        applied.append("FEMININE_ENDING")
    # Spelling-group candidates use only the existing conservative normalizer
    # for hamza/alef, final ya/aleph-maqsura, and ta marbuta/ha equivalence.
    if stem != base:
        return False, f"reduced={stem};base={base}"
    return True, "+".join(applied) or "NORMALIZED_IDENTITY"


def candidate_base_forms(value: str) -> list[tuple[str, str]]:
    normalized = normalize(value, "ar")
    forms = [(normalized, "exact-normalized-source-alias")]
    if normalized.startswith("ال"):
        stripped = normalized[2:]
        forms.append((stripped, "remove-arabic-definite-article"))
        if stripped.endswith(("ين", "ون")):
            forms.append((stripped[:-2], "remove-arabic-definite-article+remove-masculine-plural-suffix"))
        if stripped.endswith(("ة", "ه")):
            forms.append((stripped[:-1], "remove-arabic-definite-article+remove-feminine-ending"))
    elif normalized.endswith(("ين", "ون")):
        forms.append((normalized[:-2], "remove-masculine-plural-suffix"))
    return forms


def load_contexts(dataset: Path, values: set[str]) -> dict[str, list[dict[str, str]]]:
    contexts: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in sorted(dataset.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                text = row.get("text", "")
                for span in row.get("spans", []):
                    if span.get("label") != "NATIONALITY" or span.get("text") not in values:
                        continue
                    value = span["text"]
                    start, end = int(span["start"]), int(span["end"])
                    contexts[value].append({
                        "id": str(row.get("id", "")),
                        "split": str(row.get("split", "")),
                        "origin": str(row.get("origin", "")),
                        "offsets_valid": str(text[start:end] == value),
                        "context": text[max(0, start - 70):min(len(text), end + 70)],
                    })
    return contexts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN_CSV)
    parser.add_argument("--queue", type=Path, default=QUEUE_CSV)
    parser.add_argument("--source", type=Path, default=SOURCE_CSV)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/nationality_improvement/adjudication_results.csv")
    parser.add_argument("--contexts-output", type=Path, default=ROOT / "reports/nationality_improvement/adjudication_contexts.csv")
    parser.add_argument("--apply", action="store_true", help="write APPROVED decisions back to the authoritative queue")
    args = parser.parse_args()

    plan = list(csv.DictReader(args.plan.open(encoding="utf-8-sig", newline="")))
    queue = list(csv.DictReader(args.queue.open(encoding="utf-8-sig", newline="")))
    source_rows = []
    with args.source.open(encoding="utf-8-sig", newline="") as handle:
        for line_no, row in enumerate(csv.DictReader(handle), start=2):
            row["source_line"] = str(line_no)
            source_rows.append(row)

    source_index: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        source_index[(qid(row.get("country", "")), row.get("language", "").lower(), normalize(row.get("nationality", ""), row.get("language", "")))].append(row)
    queue_by_value: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in queue:
        queue_by_value[row["corpus_value"]].append(row)
    contexts = load_contexts(args.dataset, {row["corpus_value"] for row in plan})
    source_checksum = sha256(args.source)

    with Session(make_engine(args.db)) as session:
        ne_by_qid = {row.wikidata_qid: row for row in session.scalars(select(NaturalEarthCountry)).all() if row.wikidata_qid}
        ne_by_iso = defaultdict(list)
        for row in ne_by_qid.values():
            if row.iso_a2 and row.iso_a2 != "-99":
                ne_by_iso[row.iso_a2.upper()].append(row)
        country_by_qid = {row.country_qid: row for row in session.scalars(select(NationalityCountry)).all()}
        join_by_qid = {row.country_qid: row for row in session.scalars(select(NationalityGeoJoin)).all()}
        existing_alias_qids: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in session.scalars(select(NationalityAliasV2)).all():
            existing_alias_qids[(row.language, row.normalized_alias)].add(row.country_qid)

    results = []
    for plan_row in plan:
        value = plan_row["corpus_value"]
        action = plan_row["recommended_action"]
        qid_expected = qid(plan_row.get("proposed_qid", ""))
        candidates = [row for row in queue_by_value[value] if qid(row.get("candidate_qid", "")) == qid_expected] if qid_expected else queue_by_value[value]
        qid_corrected = False
        # The supplied Palestine proposal uses Q219060, which is not the
        # Natural Earth country QID. If the current P1549 snapshot contains a
        # uniquely supported alternative country QID for the same base alias,
        # verify that alternative explicitly instead of accepting the plan QID.
        if qid_expected and qid_expected not in ne_by_qid:
            alternatives = []
            for candidate in candidates:
                base = candidate.get("base_alias", "")
                source_qids = {
                    qid(source_row.get("country", ""))
                    for source_row in source_rows
                    if source_row.get("language", "").lower() == "ar"
                    and normalize(source_row.get("nationality", ""), "ar") == normalize(base, "ar")
                    and qid(source_row.get("country", "")) in ne_by_qid
                }
                for source_qid in sorted(source_qids):
                    alternatives.append((source_qid, candidate))
            alternative_qids = {source_qid for source_qid, _candidate in alternatives}
            if len(alternative_qids) == 1:
                qid_for_result = next(iter(alternative_qids))
                candidates = [candidate for source_qid, candidate in alternatives if source_qid == qid_for_result]
                qid_corrected = True
            else:
                # A stale plan row may point to a non-country QID while its
                # literal corpus form has an exact current P1549 form under
                # one Natural Earth country QID. Accept only one unique such
                # (QID, base, derivation) result.
                source_alternatives = []
                for base_form, rule in candidate_base_forms(value):
                    for source_row in source_rows:
                        source_qid = qid(source_row.get("country", ""))
                        if source_row.get("language", "").lower() == "ar" and source_qid in ne_by_qid and normalize(source_row.get("nationality", ""), "ar") == base_form:
                            source_alternatives.append((source_qid, source_row.get("nationality", ""), rule))
                distinct_alternatives = {(source_qid, base, rule) for source_qid, base, rule in source_alternatives}
                if len(distinct_alternatives) == 1:
                    qid_for_result, base, rule = next(iter(distinct_alternatives))
                    candidates = [{"base_alias": base, "derivation_rule": rule, "candidate_qid": qid_for_result}]
                    qid_corrected = True
                else:
                    qid_for_result = qid_expected
        else:
            qid_for_result = qid_expected
        contexts_for_value = contexts.get(value, [])
        offsets_valid = bool(contexts_for_value) and all(row["offsets_valid"] == "True" for row in contexts_for_value)
        approved = action in {"VERIFY_RULE_THEN_APPROVE", "CHECK_SPELLING_EQUIVALENCE", "CHECK_CORPUS_CONTEXT"}
        reasons = []
        evidence_rows = []
        approved_iso = plan_row.get("proposed_iso2", "").upper()
        if not candidates or not qid_for_result:
            approved = False
            reasons.append("NO_QUEUE_QID")
        for candidate in candidates:
            base = candidate.get("base_alias", "")
            source_matches = source_index.get((qid_for_result, "ar", normalize(base, "ar")), [])
            if not source_matches:
                approved = False
                reasons.append("BASE_NOT_IN_P1549_SOURCE")
                continue
            if not all(row.get("source_property", "").startswith("wdt:P1549") for row in source_matches):
                approved = False
                reasons.append("BASE_SOURCE_NOT_P1549")
            derived_ok, derivation = derivation_check(value, base, candidate.get("derivation_rule", ""))
            if not derived_ok:
                approved = False
                reasons.append("DERIVATION_FAILED:" + derivation)
            evidence_rows.extend((base, row["source_line"], row.get("source_property", ""), derivation) for row in source_matches)
        with Session(make_engine(args.db)) as session:
            country = session.get(NationalityCountry, qid_for_result) if qid_for_result else None
            join = session.get(NationalityGeoJoin, qid_for_result) if qid_for_result else None
            natural = ne_by_qid.get(qid_for_result)
        if not country or not join:
            approved = False
            reasons.append("MISSING_QID_COUNTRY_OR_NATURAL_EARTH_JOIN")
        else:
            if natural is not None:
                natural_iso = (natural.iso_a2 or "").upper()
                if natural_iso and natural_iso != "-99":
                    if approved_iso and approved_iso != natural_iso:
                        approved = False
                        reasons.append("ISO_MISMATCH")
                    approved_iso = natural_iso
            elif approved_iso and country.iso2 and approved_iso != country.iso2.upper():
                approved = False
                reasons.append("ISO_MISMATCH_WITH_NATIONALITY_COUNTRY")
            if natural is None and country.iso2 and ne_by_iso.get(country.iso2.upper()):
                approved = False
                reasons.append("QID_NOT_NATURAL_EARTH_COUNTRY")
            # An unresolved Natural Earth join blocks geographic hierarchy,
            # not the exact nationality alias itself. Preserve that limitation
            # in the review result instead of inventing a region.
            if join.join_status not in {"MATCHED_QID", "MATCHED_ISO"}:
                reasons.append("NATURAL_EARTH_JOIN_UNRESOLVED_EXACT_ONLY")
        normalized_value = normalize(value, "ar")
        collision_qids = set(existing_alias_qids.get(("ar", normalized_value), set()))
        if qid_for_result:
            collision_qids.add(qid_for_result)
        if len(collision_qids) > 1:
            approved = False
            reasons.append("NORMALIZED_ALIAS_COLLISION")
        if not offsets_valid:
            approved = False
            reasons.append("NER_CONTEXT_OR_OFFSETS_INVALID")
        if action == "CHECK_CORPUS_CONTEXT":
            # The supplied السورية rows are approved only because every
            # sampled context contains the explicit nationality cue الجنسية.
            context_cue_verified = bool(contexts_for_value) and all("الجنسية" in row["context"] for row in contexts_for_value)
            if not context_cue_verified:
                approved = False
                reasons.append("CONTEXT_REVIEW_REQUIRED")
            else:
                reasons.append("CONTEXT_CONFIRMED_NATIONALITY_CUE")
        if action in {"HOLD_FIND_INDEPENDENT_SOURCE", "HOLD_MALFORMED_SPAN"}:
            approved = False
            reasons.append(action)
        if qid_corrected:
            reasons.append(f"QID_CORRECTED_FROM_PLAN:{qid_expected}")
        if approved:
            reason = "PASS:" + ",".join(sorted(set(reasons))) if reasons else "PASS"
        else:
            reason = ";".join(sorted(set(reasons))) or "REVIEW_REQUIRED"
        evidence_reference = ""
        if approved and evidence_rows:
            refs = [f"{args.source.relative_to(ROOT)}#line={line};qid={qid_for_result};base={base};property={prop}" for base, line, prop, _ in evidence_rows]
            evidence_reference = f"source_sha256={source_checksum};policy={POLICY_ID};" + "|".join(refs)
        results.append({
            "corpus_value": value,
            "span_count": plan_row["span_count"],
            "language": plan_row["language"],
            "recommended_action": action,
            "candidate_qid": qid_for_result,
            "plan_qid": qid_expected,
            "candidate_iso2": approved_iso,
            "candidate_base_alias": candidates[0].get("base_alias", "") if candidates else "",
            "candidate_derivation_rule": candidates[0].get("derivation_rule", "") if candidates else "",
            "approval_status": "APPROVED" if approved else "PENDING",
            "verification_reason": reason,
            "base_source_rows": "|".join(f"{base}@line{line}" for base, line, _prop, _derivation in evidence_rows),
            "natural_earth_join_status": join.join_status if join else "",
            "natural_earth_id": join.natural_earth_id if join else "",
            "normalized_collision_qids": "|".join(sorted(collision_qids)),
            "context_count": str(len(contexts_for_value)),
            "context_offsets_valid": str(offsets_valid),
            "evidence_reference": evidence_reference,
            "review_notes": reason,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result_fields = list(results[0])
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_fields)
        writer.writeheader()
        writer.writerows(results)
    context_fields = ["corpus_value", "id", "split", "origin", "offsets_valid", "context"]
    with args.contexts_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=context_fields)
        writer.writeheader()
        for value in sorted(contexts):
            for context in contexts[value]:
                writer.writerow({"corpus_value": value, **context})

    if args.apply:
        queue_fields = list(queue[0])
        for field in ("review_notes",):
            if field not in queue_fields:
                queue_fields.append(field)
        additions = []
        for row in queue:
            result = next((candidate for candidate in results if candidate["corpus_value"] == row["corpus_value"]), None)
            row_qid = qid(row.get("candidate_qid", ""))
            if result is not None and row_qid == result["candidate_qid"]:
                row["candidate_iso2"] = result["candidate_iso2"]
                row["review_decision"] = result["approval_status"]
                row["evidence_reference"] = result["evidence_reference"]
                row["review_notes"] = result["review_notes"]
            elif result is not None and result["plan_qid"] and row_qid == result["plan_qid"] and result["plan_qid"] != result["candidate_qid"]:
                row["review_decision"] = "REJECTED"
                row["review_notes"] = f"REJECTED_PLAN_QID:{result['plan_qid']};USE_CORRECTED_QID:{result['candidate_qid']}"
                corrected = dict(row)
                corrected["candidate_qid"] = result["candidate_qid"]
                corrected["candidate_iso2"] = result["candidate_iso2"]
                corrected["base_alias"] = result["candidate_base_alias"]
                corrected["derivation_rule"] = result["candidate_derivation_rule"]
                corrected["review_decision"] = result["approval_status"]
                corrected["evidence_reference"] = result["evidence_reference"]
                corrected["review_notes"] = result["review_notes"]
                additions.append(corrected)
            elif result is not None and not result["candidate_qid"] and not row_qid:
                row["review_decision"] = result["approval_status"]
                row["evidence_reference"] = result["evidence_reference"]
                row["review_notes"] = result["review_notes"]
        queue.extend(additions)
        deduplicated_queue = []
        seen_queue_keys = set()
        for row in queue:
            queue_key = (row.get("corpus_value", ""), qid(row.get("candidate_qid", "")), row.get("candidate_iso2", "").upper(), row.get("derivation_rule", ""))
            if queue_key in seen_queue_keys:
                continue
            seen_queue_keys.add(queue_key)
            deduplicated_queue.append(row)
        queue = deduplicated_queue
        with args.queue.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=queue_fields)
            writer.writeheader()
            writer.writerows(queue)

    counts = {status: sum(row["approval_status"] == status for row in results) for status in ("APPROVED", "PENDING")}
    print(json.dumps({"results": str(args.output), "contexts": str(args.contexts_output), "counts": counts, "approved_spans": sum(int(row["span_count"]) for row in results if row["approval_status"] == "APPROVED"), "applied": args.apply}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

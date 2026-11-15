"""Import the researched cross-country, model-aware bank identity package.

The importer is additive and idempotent. Existing ``banks``, ``bank_aliases``
and GCC audit rows are preserved. The seven supplied CSVs are stored in
source-preserving tables so country operations, historical names, evidence,
relationship decisions, exclusions, and proposed cohorts remain auditable.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from finaira_generalization.db import (
    Bank,
    BankAuditClassification,
    BankDoNotMerge,
    BankGeneralizationCohort,
    BankGeneralizationForm,
    BankIdentityModel,
    BankModelAlias,
    BankModelEvidenceNote,
    BankModelRelationshipEvidence,
    BankResearchCorrection,
    DataSource,
    init_db,
    make_engine,
)
from finaira_generalization.handoff import _put, _sha256, _source, _stable, _text
from finaira_generalization.normalization import normalize


DEFAULT_SOURCE_DIR = ROOT / "data/sources/bank/model_safe_2026"
DEFAULT_DB = ROOT / "data/processed/finaira_generalization.db"
DEFAULT_REPORT_DIR = ROOT / "reports/bank_identity_model"

IDENTITY_FIELDS = (
    "country_code", "source_name_en", "source_name_ar", "family_id",
    "family_display_name", "generalization_key", "bank_identity_id",
    "is_same_legal_bank_as_parent", "relationship_to_family",
    "banking_model_from_audit", "source_entity_kind",
    "source_license_confirmation", "group_relation_status",
    "family_evidence_basis", "verified_family_source_urls", "import_action",
    "historical_successor_record_id", "transition_effective_date", "review_note",
    "country_license_review_needed", "original_category", "canonical_name_2026",
    "former_legal_name", "banking_model_effective",
    "historical_operating_model_pre_transition", "banking_service_profile",
    "model_evidence_tier", "banking_model_verified_source",
    "status_asof_2026_11_15", "record_class", "source_original_generalization_key",
    "proposed_model_aware_key", "safe_generalization_key", "identity_resolution_confidence",
    "review_reason", "successor_model_aware_key_if_post_transition",
    "non_merge_reason", "source_bank_register_url", "banking_business_scope",
    "original_model_confidence", "aliases_en", "aliases_ar", "former_names",
    "arabic_name_confidence",
)

MODEL_ALIASES = {
    "CONVENTIONAL", "ISLAMIC", "MIXED", "ISLAMIC_WINDOW", "SPECIALIZED"
}

# These are the shared, human-facing bank generalization forms.  They are
# deliberately keyed by the authoritative banking model rather than by a
# bank family, so different banks can converge on the same safe form.
BANK_MODEL_FORMS = {
    "CONVENTIONAL": ("Conventional bank", "بنك تقليدي"),
    "MIXED": ("Bank offering conventional and Islamic banking services", "بنك يقدم خدمات مصرفية تقليدية وإسلامية"),
    "ISLAMIC": ("Islamic bank", "بنك إسلامي"),
    "ISLAMIC_WINDOW": ("Bank with an Islamic window", "بنك ذو نافذة إسلامية"),
    "SPECIALIZED": ("Specialized or development bank", "بنك متخصص أو تنموي"),
    "UNKNOWN": ("Unknown banking model", "نموذج مصرفي غير معروف"),
    "HISTORICAL_UNDETERMINED": ("Historical or undetermined banking model", "نموذج مصرفي تاريخي أو غير محدد"),
    "NOT_A_BANK": ("Not a bank", "ليس بنكًا"),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "y"}


def _required_paths(source_dir: Path) -> dict[str, Path]:
    names = {
        "identity": "finaira_bank_identity_model_safe_2026.csv",
        "aliases": "finaira_bank_aliases_model_safe_2026.csv",
        "cohorts": "finaira_bank_safe_generalization_cohorts_2026.csv",
        "relationships": "finaira_bank_relationships_2026.csv",
        "exclusions": "finaira_bank_do_not_merge_2026.csv",
        "corrections": "finaira_bank_research_corrections_2026.csv",
        "evidence": "finaira_bank_model_evidence_notes_2026.csv",
    }
    paths = {key: source_dir / name for key, name in names.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing bank model source files: " + ", ".join(missing))
    return paths


def _existing_bank_map(db_path: Path, record_ids: set[str]) -> tuple[dict[str, str], int]:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    with sqlite3.connect(db_path) as connection:
        existing = {row[0] for row in connection.execute("select bank_id from banks")}
        audit_map = {
            row[0]: row[1]
            for row in connection.execute(
                "select source_record_id, bank_id from bank_audit_classifications"
            )
        }
    mapping = {}
    unresolved = []
    for record_id in record_ids:
        if record_id in existing:
            mapping[record_id] = record_id
        elif record_id in audit_map:
            # The legacy GCC importer intentionally maps BH-241 to BH-197.
            mapping[record_id] = audit_map[record_id]
        else:
            unresolved.append(record_id)
    if unresolved:
        raise ValueError("BANK_RECORD_NOT_PRESENT_IN_EXISTING_DATABASE:" + ",".join(sorted(unresolved)))
    return mapping, len(existing)


def _eligibility(row: dict[str, str]) -> tuple[bool, str]:
    reasons = []
    if not _bool(row.get("automatic_grouping")):
        reasons.append("AUTOMATIC_GROUPING_NO")
    if _bool(row.get("review_required")):
        reasons.append("REVIEW_REQUIRED")
    if row.get("record_class") != "BANK":
        reasons.append("NON_ACTIVE_BANK_RECORD")
    if row.get("group_relation_status") != "SOURCE_VERIFIED_RELATIONSHIP":
        reasons.append("RELATIONSHIP_NOT_SOURCE_VERIFIED")
    if row.get("banking_model_effective") not in MODEL_ALIASES:
        reasons.append("MODEL_NOT_SUFFICIENTLY_VERIFIED")
    if not _text(row.get("safe_generalization_key")):
        reasons.append("SAFE_KEY_MISSING")
    return not reasons, ";".join(reasons) if reasons else "ELIGIBLE_SOURCE_VERIFIED_MODEL_GROUP"


def _alias_enabled(row: dict[str, str], identity: dict[str, str], eligible: bool) -> bool:
    alias_type = (row.get("alias_type") or "").casefold()
    if not eligible or _bool(row.get("review_required")):
        return False
    if identity.get("record_class") != "BANK":
        return False
    if alias_type in {"historic_predecessor_or_previous_name", "historical"}:
        return False
    return True


def _write_report(report_dir: Path, report: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "migration_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    lines = ["# Bank identity/model-safe migration report", "", f"Generated: {report['generated_at']}", ""]
    for key, value in report.items():
        if key != "generated_at":
            lines.append(f"- **{key}**: {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
    (report_dir / "migration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def import_bank_identity_model(
    db_path: str | Path = DEFAULT_DB,
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> dict:
    db_path = Path(db_path)
    source_dir = Path(source_dir)
    report_dir = Path(report_dir)
    paths = _required_paths(source_dir)
    identity_rows = _read_csv(paths["identity"])
    alias_rows = _read_csv(paths["aliases"])
    cohort_rows = _read_csv(paths["cohorts"])
    relationship_rows = _read_csv(paths["relationships"])
    exclusion_rows = _read_csv(paths["exclusions"])
    correction_rows = _read_csv(paths["corrections"])
    evidence_rows = _read_csv(paths["evidence"])

    identity_by_id = {row["record_id"]: row for row in identity_rows}
    if len(identity_by_id) != len(identity_rows):
        raise ValueError("DUPLICATE_BANK_IDENTITY_RECORD_ID")
    bank_map, existing_bank_count = _existing_bank_map(db_path, set(identity_by_id))
    eligible_by_record = {record_id: _eligibility(row)[0] for record_id, row in identity_by_id.items()}

    cohort_ids = set()
    cohort_validation = []
    for row in cohort_rows:
        key = _text(row.get("safe_generalization_key"))
        if not key or key in cohort_ids:
            raise ValueError("DUPLICATE_OR_EMPTY_SAFE_GENERALIZATION_KEY")
        cohort_ids.add(key)
        members = [part.strip() for part in (row.get("bank_record_ids") or "").split("|") if part.strip()]
        if not members or any(member not in identity_by_id for member in members):
            raise ValueError(f"COHORT_MEMBER_NOT_FOUND:{key}")
        member_reasons = [_eligibility(identity_by_id[member])[1] for member in members]
        # ``automatic_grouping`` controls whether multiple operations may
        # share this key. A single verified operation may still use its own
        # safe model-aware key when automatic grouping is deliberately NO.
        source_eligible = all(eligible_by_record[member] for member in members)
        if source_eligible:
            reason = "ELIGIBLE_SOURCE_VERIFIED_MODEL_GROUP" if _bool(row.get("automatic_grouping")) else "ELIGIBLE_UNIQUE_MODEL_SAFE_KEY"
        else:
            reason = ";".join(sorted(set(member_reasons)))
        cohort_validation.append((row, source_eligible, reason))

    source_cohort_keys = {row["safe_generalization_key"] for row, _, _ in cohort_validation}
    derived_review_cohorts = []
    for record_id, identity in identity_by_id.items():
        safe_key = _text(identity.get("safe_generalization_key"))
        if safe_key and safe_key not in source_cohort_keys:
            derived_review_cohorts.append(({
                "safe_generalization_key": safe_key,
                "model": _text(identity.get("banking_model_effective")) or "UNKNOWN",
                "records": "1",
                "countries": _text(identity.get("country_code")),
                "names": _text(identity.get("canonical_name_2026")) or _text(identity.get("source_name_en")),
                "bank_record_ids": record_id,
                "automatic_grouping": "NO",
                "family_id": _text(identity.get("family_id")),
            }, False, "IDENTITY_SAFE_KEY_WITHOUT_APPROVED_COHORT"))

    for row in alias_rows:
        if row.get("record_id") not in identity_by_id:
            raise ValueError(f"ALIAS_RECORD_NOT_FOUND:{row.get('record_id')}")
    for row in relationship_rows:
        if row.get("from_record_id") not in identity_by_id or row.get("to_record_id") not in identity_by_id:
            raise ValueError(f"RELATIONSHIP_RECORD_NOT_FOUND:{row}")
    for row in exclusion_rows:
        if row.get("record_a") not in identity_by_id or row.get("record_b") not in identity_by_id:
            raise ValueError(f"EXCLUSION_RECORD_NOT_FOUND:{row}")
    for row in correction_rows + evidence_rows:
        if row.get("record_id") not in identity_by_id:
            raise ValueError(f"EVIDENCE_RECORD_NOT_FOUND:{row}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": str(db_path),
        "source_dir": str(source_dir),
        "dry_run": dry_run,
        "input_records": len(identity_rows),
        "existing_bank_records_before": existing_bank_count,
        "canonical_bank_records_reused": len(set(bank_map.values())),
        "duplicate_source_records_mapped": sum(record_id != bank_id for record_id, bank_id in bank_map.items()),
        "aliases_processed": len(alias_rows),
        "aliases_enabled_for_lookup": sum(_alias_enabled(row, identity_by_id[row["record_id"]], eligible_by_record[row["record_id"]]) for row in alias_rows),
        "aliases_review_or_historical": sum(not _alias_enabled(row, identity_by_id[row["record_id"]], eligible_by_record[row["record_id"]]) for row in alias_rows),
        "cohorts_imported": len(cohort_rows),
        "derived_review_cohorts": len(derived_review_cohorts),
        "cohorts_materialized": len(cohort_rows) + len(derived_review_cohorts),
        "cohorts_enabled_for_lookup": sum(enabled for _, enabled, _ in cohort_validation),
        "cohorts_review_or_separate": sum(not enabled for _, enabled, _ in cohort_validation),
        "generalization_forms_imported": len(identity_rows) * 2,
        "shared_finance_model_forms": len(identity_rows),
        "approved_shared_cohort_keys": sum(enabled and _bool(row.get("automatic_grouping")) and int(row.get("records") or 0) > 1 for row, enabled, _ in cohort_validation),
        "identities_in_approved_shared_cohorts": sum(int(row.get("records") or 0) for row, enabled, _ in cohort_validation if enabled and _bool(row.get("automatic_grouping")) and int(row.get("records") or 0) > 1),
        "review_required_identity_records": sum(_bool(row.get("review_required")) for row in identity_rows),
        "relationships_imported": len(relationship_rows),
        "do_not_merge_imported": len(exclusion_rows),
        "research_corrections_imported": len(correction_rows),
        "model_evidence_notes_imported": len(evidence_rows),
        "model_counts": dict(Counter(row.get("banking_model_effective") for row in identity_rows)),
        "record_class_counts": dict(Counter(row.get("record_class") for row in identity_rows)),
        "unresolved_records": [],
        "backup_path": None,
    }

    if dry_run:
        _write_report(report_dir, report)
        return report

    if backup and db_path.exists():
        backup_path = db_path.with_name(
            f"{db_path.stem}_backup_bank_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_path.suffix}"
        )
        copy2(db_path, backup_path)
        report["backup_path"] = str(backup_path)

    engine = init_db(db_path)
    with Session(engine) as session:
        source_identity = _source(session, "finaira_bank_identity_model_safe_2026", paths["identity"], version="bank-model-safe-2026", license_text="Supplied researched bank identity/model package")
        source_alias = _source(session, "finaira_bank_aliases_model_safe_2026", paths["aliases"], version="bank-model-safe-2026", license_text="Supplied researched bank alias package")
        source_cohort = _source(session, "finaira_bank_safe_generalization_cohorts_2026", paths["cohorts"], version="bank-model-safe-2026", license_text="Supplied proposed model-safe cohorts")
        source_relationship = _source(session, "finaira_bank_relationships_2026", paths["relationships"], version="bank-model-safe-2026", license_text="Supplied researched relationship evidence")
        source_exclusion = _source(session, "finaira_bank_do_not_merge_2026", paths["exclusions"], version="bank-model-safe-2026", license_text="Supplied explicit bank merge exclusions")
        source_correction = _source(session, "finaira_bank_research_corrections_2026", paths["corrections"], version="bank-model-safe-2026", license_text="Supplied research corrections")
        source_evidence = _source(session, "finaira_bank_model_evidence_notes_2026", paths["evidence"], version="bank-model-safe-2026", license_text="Supplied model evidence notes")

        for row in identity_rows:
            values = {field: _text(row.get(field)) for field in IDENTITY_FIELDS}
            values.update({
                "canonical_bank_id": bank_map[row["record_id"]],
                "automatic_grouping": _bool(row.get("automatic_grouping")),
                "review_required": _bool(row.get("review_required")),
                "source_id": source_identity.source_id,
            })
            _put(session, BankIdentityModel, row["record_id"], values)

        for index, row in enumerate(alias_rows):
            identity = identity_by_id[row["record_id"]]
            alias = _text(row.get("alias"))
            language = "ar" if any("\u0600" <= char <= "\u06ff" for char in alias) else "en"
            alias_id = _stable("bank-model-alias-2026", index, row["record_id"], alias, row.get("alias_type"))
            _put(session, BankModelAlias, alias_id, {
                "record_id": row["record_id"],
                "canonical_bank_id": bank_map[row["record_id"]],
                "country_code": _text(row.get("country_code")),
                "bank_name_en": _text(row.get("bank_name_en")),
                "alias_text": alias,
                "normalized_alias": normalize(alias, language),
                "language": language,
                "alias_type": _text(row.get("alias_type")),
                "category": _text(row.get("category")),
                "status": _text(row.get("status")),
                "review_required": _bool(row.get("review_required")),
                "safe_generalization_key": _text(row.get("safe_generalization_key")),
                "proposed_model_aware_key": _text(row.get("proposed_model_aware_key")),
                "family_id": _text(row.get("family_id")),
                "bank_identity_id": _text(row.get("bank_identity_id")),
                "banking_model_effective": _text(row.get("banking_model_effective")),
                "automatic_grouping": _bool(row.get("automatic_grouping")),
                "enabled_for_lookup": _alias_enabled(row, identity, eligible_by_record[row["record_id"]]),
                "source_id": source_alias.source_id,
            })

        for row, enabled, reason in cohort_validation:
            _put(session, BankGeneralizationCohort, row["safe_generalization_key"], {
                "model": _text(row.get("model")),
                "record_count": int(row.get("records") or 0),
                "countries": _text(row.get("countries")),
                "names": _text(row.get("names")),
                "bank_record_ids": _text(row.get("bank_record_ids")),
                "automatic_grouping": _bool(row.get("automatic_grouping")),
                "family_id": _text(row.get("family_id")),
                "eligible_for_lookup": enabled,
                "eligibility_reason": reason,
                "source_id": source_cohort.source_id,
            })

        for row, enabled, reason in derived_review_cohorts:
            _put(session, BankGeneralizationCohort, row["safe_generalization_key"], {
                "model": row["model"],
                "record_count": 1,
                "countries": row["countries"],
                "names": row["names"],
                "bank_record_ids": row["bank_record_ids"],
                "automatic_grouping": False,
                "family_id": row["family_id"],
                "eligible_for_lookup": False,
                "eligibility_reason": reason,
                "source_id": source_cohort.source_id,
            })

        cohort_by_key = {row["safe_generalization_key"]: (row, enabled) for row, enabled, _ in cohort_validation + derived_review_cohorts}
        for record_id, identity in identity_by_id.items():
            safe_key = _text(identity.get("safe_generalization_key"))
            if not safe_key or safe_key not in cohort_by_key:
                continue
            cohort_row, enabled = cohort_by_key[safe_key]
            bank = session.get(Bank, bank_map[record_id])
            model = _text(bank.finance_model if bank else None) or _text(identity.get("banking_model_effective")) or "UNKNOWN"
            model_label_en, model_label_ar = BANK_MODEL_FORMS.get(model, BANK_MODEL_FORMS["UNKNOWN"])
            # The shared model form is enabled only for an active, source-
            # verified bank operation.  Family-level cohort approval is not
            # required for this broader form; it is exactly what lets
            # different banks with the same verified banking model converge.
            model_enabled = (
                bool(bank)
                and identity.get("record_class") == "BANK"
                and not _bool(identity.get("review_required"))
                and model in MODEL_ALIASES
            )
            model_form_id = _stable("bank-generalization-form-model-2026", record_id, model)
            _put(session, BankGeneralizationForm, model_form_id, {
                "source_record_id": record_id,
                "canonical_bank_id": bank_map[record_id],
                "safe_generalization_key": safe_key,
                "level_code": "FINANCE_MODEL",
                "specificity_rank": 2,
                "label_en": model_label_en,
                "label_ar": model_label_ar,
                "banking_model": model,
                "verification_status": "SOURCE_VERIFIED" if model_enabled else "REVIEW_ONLY",
                "enabled_for_lookup": model_enabled,
                "disclosure_approved": model_enabled,
                "is_exact": False,
                "is_local_only": False,
                "is_suppression": False,
                "source_id": source_cohort.source_id,
            })
            form_id = _stable("bank-generalization-form-2026", record_id, safe_key)
            _put(session, BankGeneralizationForm, form_id, {
                "source_record_id": record_id,
                "canonical_bank_id": bank_map[record_id],
                "safe_generalization_key": safe_key,
                "level_code": "MODEL_SAFE_GROUP",
                "specificity_rank": 1,
                "label_en": safe_key,
                "label_ar": safe_key,
                "banking_model": _text(identity.get("banking_model_effective")),
                "verification_status": "SOURCE_VERIFIED" if enabled else "REVIEW_ONLY",
                "enabled_for_lookup": enabled,
                "disclosure_approved": enabled,
                "is_exact": False,
                "is_local_only": False,
                "is_suppression": False,
                "source_id": source_cohort.source_id,
            })

        for index, row in enumerate(relationship_rows):
            _put(session, BankModelRelationshipEvidence, _stable("bank-model-relationship-2026", index, row.get("from_record_id"), row.get("to_record_id"), row.get("relationship_type")), {
                "from_record_id": row["from_record_id"], "to_record_id": row["to_record_id"],
                "relationship_type": _text(row.get("relationship_type")),
                "impact_on_generalization": _text(row.get("impact_on_generalization")),
                "explanation": _text(row.get("explanation")), "source_url": _text(row.get("source_url")),
                "source_id": source_relationship.source_id,
            })

        for index, row in enumerate(exclusion_rows):
            _put(session, BankDoNotMerge, _stable("bank-model-exclusion-2026", index, row.get("record_a"), row.get("record_b")), {
                "record_a": row["record_a"], "record_b": row["record_b"],
                "why": _text(row.get("why")), "collision_type": _text(row.get("collision_type")),
                "source_id": source_exclusion.source_id,
            })

        for index, row in enumerate(correction_rows):
            _put(session, BankResearchCorrection, _stable("bank-model-correction-2026", index, row.get("record_id")), {
                "record_id": row["record_id"], "description": _text(row.get("description")),
                "old_values": _text(row.get("old_values")), "new_values": _text(row.get("new_values")),
                "source_url": _text(row.get("source_url")), "evidence_tier": _text(row.get("evidence_tier")),
                "source_id": source_correction.source_id,
            })

        for index, row in enumerate(evidence_rows):
            _put(session, BankModelEvidenceNote, _stable("bank-model-evidence-2026", index, row.get("record_id")), {
                "record_id": row["record_id"], "risk": _text(row.get("risk")),
                "detail": _text(row.get("detail")), "source_url": _text(row.get("source_url")),
                "source_id": source_evidence.source_id,
            })
        session.commit()

    _write_report(report_dir, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()
    report = import_bank_identity_model(
        args.db, args.source_dir, args.report_dir,
        dry_run=args.dry_run, backup=not args.no_backup,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

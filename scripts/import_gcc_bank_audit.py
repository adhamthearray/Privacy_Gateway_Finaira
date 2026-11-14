"""Idempotently integrate the supplied 2026 GCC bank audit.

The audited CSV is the classification authority. The original flat alias CSV
is the alias authority. This importer never deletes existing bank rows or
aliases, keeps historical/unverified records visible as non-confirmed, and
materializes only explicitly supported parent/window relationships.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from finaira_generalization.db import (
    Bank,
    BankAlias,
    BankAuditClassification,
    BankCandidate,
    BankRelationship,
    DataSource,
    init_db,
)
from finaira_generalization.handoff import _put, _sha256, _stable, _text, _source
from finaira_generalization.normalization import normalize


DEFAULT_SOURCE_DIR = ROOT / "data/sources/bank/gcc_2026"
DEFAULT_DB = ROOT / "data/processed/finaira_generalization.db"
DEFAULT_REPORT_DIR = ROOT / "reports/gcc_bank_audit"

KNOWN_ACTIONS = {
    "IMPORT_WITH_LICENSE_CLASS",
    "IMPORT_WITH_MODEL_SOURCE",
    "IMPORT_WITH_2026_RECHECK",
    "CHECK_CBB_ENTITY_LICENSE",
    "LINK_TO_PARENT_BANK",
    "ALIAS_ONLY_HISTORICAL",
    "DO_NOT_IMPORT_AS_LICENSED",
    "DO_NOT_TREAT_AS_OPERATING",
    "DUPLICATE_RECONCILIATION",
    "EXCLUDE_FROM_LICENSED_BANK_COUNT",
    "IMPORT_MODEL_WITH_CAUTION",
    "SEPARATE_FROM_COMMERCIAL_BANKS",
    "IMPORT_WITH_ENTITY_NOTE",
    "VERIFY_BANK_MODEL",
    "REVERIFY_CURRENT_2026",
}

MODEL_MAP = {
    "conventional": ("CONVENTIONAL", "Conventional", "تقليدي"),
    "islamic": ("ISLAMIC", "Islamic", "إسلامي"),
    "islamic window": ("ISLAMIC_WINDOW", "Islamic window", "نافذة إسلامية"),
    "specialized / development": ("SPECIALIZED", "Specialized / development", "متخصص / تنموي"),
    "unspecified specialized": ("SPECIALIZED", "Specialized / development", "متخصص / تنموي"),
    "unknown": ("UNKNOWN", "Unknown", "غير معروف"),
    "not applicable": ("NOT_APPLICABLE", "Not applicable", "لا ينطبق"),
    "historical / not currently classified": ("HISTORICAL", "Historical / not currently classified", "تاريخي / غير مصنف حاليًا"),
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _is_arabic(value: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" for char in value)


def _bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def _model(raw: str) -> tuple[str, str, str]:
    return MODEL_MAP.get(str(raw or "").strip().casefold(), ("UNKNOWN", "Unknown", "غير معروف"))


def _operational_status(row: dict[str, str], license_status: str) -> str:
    raw = (row.get("status") or "").strip().casefold()
    if raw == "historical":
        return "HISTORICAL"
    if raw == "licensed_not_operational":
        return "LICENSED_NOT_OPERATIONAL"
    if raw == "candidate_verify_license":
        return "LICENSE_UNVERIFIED"
    if raw == "2024_register_check_current":
        return "REQUIRES_2026_RECHECK"
    if license_status == "CONFIRMED":
        return "ACTIVE_LISTED"
    return "ACTIVE_REQUIRES_REVIEW"


def _license_status(row: dict[str, str], model_code: str) -> tuple[str, bool]:
    action = (row.get("review_action") or "").strip()
    status = (row.get("status") or "").strip().casefold()
    kind = (row.get("entity_kind") or "").strip().casefold()
    confidence = (row.get("confidence") or "").strip().casefold()
    if model_code == "NOT_APPLICABLE" or "regulator" in kind:
        return "NOT_APPLICABLE", False
    if model_code == "HISTORICAL" or status == "historical" or action == "ALIAS_ONLY_HISTORICAL":
        return "HISTORICAL", False
    if action == "LINK_TO_PARENT_BANK" or model_code == "ISLAMIC_WINDOW":
        return "LINKED_WINDOW", False
    if action in {"DO_NOT_IMPORT_AS_LICENSED", "CHECK_CBB_ENTITY_LICENSE", "VERIFY_BANK_MODEL", "REVERIFY_CURRENT_2026", "DUPLICATE_RECONCILIATION"}:
        return "UNVERIFIED", False
    if action in {"IMPORT_WITH_2026_RECHECK", "DO_NOT_TREAT_AS_OPERATING", "IMPORT_MODEL_WITH_CAUTION"}:
        return "RECHECK_REQUIRED", False
    if "high" in confidence and action in {"IMPORT_WITH_LICENSE_CLASS", "IMPORT_WITH_MODEL_SOURCE", "IMPORT_WITH_ENTITY_NOTE"}:
        return "CONFIRMED", status == "listed"
    return "PROVISIONAL", False


def _alias_status(row: dict[str, str], audit: dict[str, str]) -> tuple[str, bool]:
    alias_type = row.get("alias_type") or "curated_alias"
    review_required = _bool(row.get("review_required"))
    historical = alias_type == "historic_predecessor_or_previous_name" or audit.get("review_action") == "ALIAS_ONLY_HISTORICAL"
    if historical:
        return "HISTORICAL_SOURCE", True
    if review_required:
        return "REVIEW_REQUIRED", False
    return "SOURCE_IMPORTED", True


def _parent_name(note: str | None) -> str | None:
    match = re.search(r"(?i)parent\s*:\s*([^;,.]+)", str(note or ""))
    return match.group(1).strip() if match else None


def _write_report(report_dir: Path, report: dict, audit_rows: list[dict[str, str]]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "migration_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    with (report_dir / "audit_results.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = list(audit_rows[0]) if audit_rows else []
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audit_rows)
    lines = ["# GCC bank audit migration report", "", f"Generated: {report['generated_at']}", ""]
    for key, value in report.items():
        if key in {"generated_at", "audit_rows"}:
            continue
        lines.append(f"- **{key}**: {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
    (report_dir / "migration_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def import_gcc_audit(
    db_path: str | Path = DEFAULT_DB,
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    *,
    dry_run: bool = False,
    backup: bool = False,
) -> dict:
    db_path = Path(db_path)
    source_dir = Path(source_dir)
    report_dir = Path(report_dir)
    master_path = source_dir / "gcc_banks_master_2026.csv"
    alias_path = source_dir / "gcc_banks_aliases_flat_2026.csv"
    audit_path = source_dir / "gcc_banks_audited_classifications_2026.csv"
    for path in (master_path, alias_path, audit_path):
        if not path.exists():
            raise FileNotFoundError(path)

    master_rows = _read_csv(master_path)
    alias_rows = _read_csv(alias_path)
    audit_rows = _read_csv(audit_path)
    audit_by_id = {row["id"]: row for row in audit_rows}
    master_by_id = {row["id"]: row for row in master_rows}
    if set(audit_by_id) != set(master_by_id):
        raise ValueError("Master and audited CSV IDs do not match")

    duplicate_map = {"BH-241": "BH-197"}
    target_by_source = {source_id: duplicate_map.get(source_id, source_id) for source_id in audit_by_id}
    model_counts = Counter(_model(row.get("banking_model"))[0] for row in audit_rows)
    action_counts = Counter(row.get("review_action") or "" for row in audit_rows)
    unknown_actions = sorted(set(action_counts) - KNOWN_ACTIONS)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "database": str(db_path),
        "source_dir": str(source_dir),
        "audit_rows": len(audit_rows),
        "master_rows": len(master_rows),
        "alias_rows": len(alias_rows),
        "model_counts": dict(model_counts),
        "review_action_counts": dict(action_counts),
        "unrecognized_review_actions": unknown_actions,
        "duplicate_candidates": [{"source_record_id": key, "canonical_record_id": value} for key, value in duplicate_map.items()],
        "existing_bank_records_before": 0,
        "new_records_created": 0,
        "records_matched_existing": 0,
        "aliases_preserved_before": 0,
        "new_aliases_imported": 0,
        "alias_rows_skipped": 0,
        "alias_duplicates_collapsed": 0,
        "parent_relationships_created": 0,
        "unresolved_parent_relationships": [],
        "license_status_counts": {},
        "operational_status_counts": {},
        "licensed_count_eligible": 0,
        "manual_review_records": 0,
    }
    result_rows: list[dict[str, str]] = []

    if dry_run:
        import sqlite3
        if db_path.exists():
            connection = sqlite3.connect(db_path)
            report["existing_bank_records_before"] = connection.execute("select count(*) from banks").fetchone()[0]
            report["aliases_preserved_before"] = connection.execute("select count(*) from bank_aliases").fetchone()[0]
            connection.close()
        for row in audit_rows:
            code, _, _ = _model(row.get("banking_model"))
            license_status, eligible = _license_status(row, code)
            result_rows.append({"source_record_id": row["id"], "canonical_bank_id": target_by_source[row["id"]], "banking_model": code, "license_status": license_status, "licensed_count_eligible": str(eligible), "review_action": row.get("review_action", ""), "review_note": row.get("review_note", "")})
            report["license_status_counts"][license_status] = report["license_status_counts"].get(license_status, 0) + 1
            report["operational_status_counts"][_operational_status(row, license_status)] = report["operational_status_counts"].get(_operational_status(row, license_status), 0) + 1
            report["licensed_count_eligible"] += int(eligible)
            report["manual_review_records"] += int(license_status not in {"CONFIRMED", "NOT_APPLICABLE", "HISTORICAL"})
        report["audit_rows"] = result_rows
        _write_report(report_dir, report, result_rows)
        return report

    if backup and db_path.exists():
        backup_path = db_path.with_name(f"{db_path.stem}_backup_gcc_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_path.suffix}")
        copy2(db_path, backup_path)
        report["backup_path"] = str(backup_path)

    engine = init_db(db_path)
    with Session(engine) as session:
        report["existing_bank_records_before"] = session.execute(select(Bank)).scalars().all().__len__()
        report["aliases_preserved_before"] = session.execute(select(BankAlias)).scalars().all().__len__()
        sources = {
            "master": _source(session, "gcc_banks_master_2026", master_path, version="gcc-master-2026", license_text="Supplied GCC bank identity dataset"),
            "aliases": _source(session, "gcc_banks_aliases_flat_2026", alias_path, version="gcc-aliases-2026", license_text="Supplied GCC alias dataset"),
            "audit": _source(session, "gcc_banks_audited_classifications_2026", audit_path, version="gcc-audit-2026", license_text="Supplied audit; source URLs retained per row"),
        }
        for optional in ("gcc_banks_master_2026.json", "gcc_banks_audited_classifications_2026.json", "gcc_banks_verified_models_2026.xlsx", "GCC_Bank_Model_Classification_Audit_2026.pdf"):
            path = source_dir / optional
            if path.exists():
                _source(session, f"gcc_{path.stem}", path, version="gcc-audit-2026", license_text="Supplied supporting audit artifact")

        for row in audit_rows:
            source_id = row["id"]
            bank_id = target_by_source[source_id]
            model_code, model_label_en, model_label_ar = _model(row.get("banking_model"))
            license_status, eligible = _license_status(row, model_code)
            existing = session.get(Bank, bank_id)
            if existing is None:
                _put(session, Bank, bank_id, {
                    "cbe_list_number": None,
                    "name_en": row["bank_name_en"],
                    "name_ar": _text(row.get("bank_name_ar")),
                    "finance_model": model_code,
                    "finance_model_label_en": model_label_en,
                    "finance_model_label_ar": model_label_ar,
                    "classification_rule": "GCC_AUDIT_2026",
                    "evidence_status": license_status,
                    "evidence_confidence": _text(row.get("confidence")),
                    "as_of_date": "2026",
                    "evidence_review_status": _text(row.get("review_action")),
                    "source_id": sources["master"].source_id,
                })
                report["new_records_created"] += 1
            else:
                report["records_matched_existing"] += 1
            _put(session, BankAuditClassification, f"GCC_AUDIT_{source_id}", {
                "source_record_id": source_id,
                "bank_id": bank_id,
                "country_code": row["country_code"],
                "country": row["country"],
                "raw_category": _text(row.get("category")),
                "raw_status": _text(row.get("status")),
                "banking_model": model_code,
                "banking_model_source": _text(row.get("banking_model")) or "Unknown",
                "business_scope": _text(row.get("business_scope")),
                "entity_kind": _text(row.get("entity_kind")),
                "operational_status": _operational_status(row, license_status),
                "license_confirmation": _text(row.get("license_confirmation")),
                "classification_evidence": _text(row.get("classification_evidence")),
                "source_url": _text(row.get("source_url")),
                "evidence_url": _text(row.get("evidence_url")),
                "confidence": _text(row.get("confidence")),
                "review_action": _text(row.get("review_action")),
                "review_note": _text(row.get("review_note")),
                "license_status": license_status,
                "licensed_count_eligible": eligible,
                "source_id": sources["audit"].source_id,
            })
            report["license_status_counts"][license_status] = report["license_status_counts"].get(license_status, 0) + 1
            operational = _operational_status(row, license_status)
            report["operational_status_counts"][operational] = report["operational_status_counts"].get(operational, 0) + 1
            report["licensed_count_eligible"] += int(eligible)
            report["manual_review_records"] += int(license_status not in {"CONFIRMED", "NOT_APPLICABLE", "HISTORICAL"})
            result_rows.append({"source_record_id": source_id, "canonical_bank_id": bank_id, "banking_model": model_code, "license_status": license_status, "licensed_count_eligible": str(eligible), "review_action": row.get("review_action", ""), "review_note": row.get("review_note", "")})

        parent_lookup = {}
        for row in audit_rows:
            parent_lookup[(row["country_code"], normalize(row["bank_name_en"], "en"))] = target_by_source[row["id"]]
        for row in audit_rows:
            if row.get("review_action") != "LINK_TO_PARENT_BANK":
                continue
            parent = _parent_name(row.get("review_note"))
            parent_id = parent_lookup.get((row["country_code"], normalize(parent or "", "en")))
            if not parent_id:
                report["unresolved_parent_relationships"].append({"source_record_id": row["id"], "parent_name": parent})
                continue
            relationship_id = _stable("gcc-bank-relationship", row["id"], "ISLAMIC_WINDOW_OF")
            _put(session, BankRelationship, relationship_id, {
                "child_bank_id": target_by_source[row["id"]],
                "parent_bank_id": parent_id,
                "relationship_type": "ISLAMIC_WINDOW_OF",
                "source_record_id": row["id"],
                "verification_status": "SOURCE_VERIFIED",
                "evidence_note": row.get("review_note"),
                "source_id": sources["audit"].source_id,
            })
            report["parent_relationships_created"] += 1

        new_bank_ids = {target_by_source[row["id"]] for row in audit_rows if row["id"] not in duplicate_map}
        for bank_id in new_bank_ids:
            session.execute(delete(BankCandidate).where(BankCandidate.bank_id == bank_id))
        target_rows = {row["id"]: row for row in audit_rows}
        target_audit = {}
        for row in audit_rows:
            target_audit.setdefault(target_by_source[row["id"]], row)
        for bank_id, row in target_audit.items():
            bank = session.get(Bank, bank_id)
            code, label_en, label_ar = _model(row.get("banking_model"))
            license_status, _ = _license_status(row, code)
            verification = "SOURCE_VERIFIED" if license_status == "CONFIRMED" else "HISTORICAL" if license_status == "HISTORICAL" else "REVIEW_ONLY" if license_status in {"UNVERIFIED", "LINKED_WINDOW"} else "PROVISIONAL"
            levels = [
                ("EXACT", 0, bank.name_en, bank.name_ar, None, True, True, False, None),
                ("FINANCE_MODEL", 1, label_en, label_ar, model_counts[code], False, False, False, code),
                ("BANKING_INSTITUTION", 2, "Banking institution", "مؤسسة مصرفية", len(target_audit), False, False, False, None),
                ("FINANCIAL_INSTITUTION", 3, "Financial institution", "مؤسسة مالية", len(target_audit), False, False, False, None),
                ("SUPPRESSED", 4, None, None, None, False, False, True, None),
            ]
            for level, rank, en, ar, population, exact, local, suppression, model in levels:
                _put(session, BankCandidate, f"{bank_id}__{level}", {
                    "bank_id": bank_id,
                    "level_code": level,
                    "specificity_rank": rank,
                    "label_en": en,
                    "label_ar": ar,
                    "finance_model": model,
                    "category_population_count": population,
                    "is_exact": exact,
                    "is_local_only": local,
                    "is_suppression": suppression,
                    "disclosure_approved": False,
                    "evidence_status": license_status,
                    "verification_status": verification,
                    "source_id": sources["audit"].source_id,
                    "derivation_method": "derived:gcc-audit-2026",
                })

        for row in alias_rows:
            alias = _text(row.get("alias"))
            if not alias or row.get("record_id") not in target_by_source:
                report["alias_rows_skipped"] += 1
                continue
            language = "ar" if _is_arabic(alias) else "en"
            audit = audit_by_id[row["record_id"]]
            status, enabled = _alias_status(row, audit)
            normalized_alias = normalize(alias, language)
            existing_alias = session.scalar(select(BankAlias).where(
                BankAlias.bank_id == target_by_source[row["record_id"]],
                BankAlias.language == language,
                BankAlias.normalized_alias == normalized_alias,
            ))
            alias_id = _stable("gcc-bank-alias-2026", target_by_source[row["record_id"]], language, alias, row.get("alias_type"))
            if existing_alias is not None and existing_alias.alias_id != alias_id:
                # The existing schema intentionally has one normalized alias
                # per bank/language. Keep the first stable spelling and record
                # the duplicate rather than violating the constraint.
                report["alias_duplicates_collapsed"] += 1
                if (row.get("alias_type") or "").startswith("canonical") and not (existing_alias.alias_kind or "").startswith("canonical"):
                    existing_alias.alias_text = alias
                    existing_alias.alias_kind = row.get("alias_type")
                    existing_alias.review_status = status
                    existing_alias.enabled_for_lookup = enabled
                continue
            alias_exists = session.get(BankAlias, alias_id) is not None
            _put(session, BankAlias, alias_id, {
                "bank_id": target_by_source[row["record_id"]],
                "alias_text": alias,
                "normalized_alias": normalized_alias,
                "language": language,
                "alias_kind": row.get("alias_type"),
                "review_status": status,
                "enabled_for_lookup": enabled,
                "source_id": sources["aliases"].source_id,
            })
            if not alias_exists:
                report["new_aliases_imported"] += 1

        session.commit()
    with Session(engine) as session:
        report["aliases_preserved_after"] = session.execute(select(BankAlias)).scalars().all().__len__()
    _write_report(report_dir, report, result_rows)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", action="store_true")
    args = parser.parse_args()
    report = import_gcc_audit(args.db, args.source_dir, args.report_dir, dry_run=args.dry_run, backup=args.backup)
    print(json.dumps({key: value for key, value in report.items() if key != "audit_rows"}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

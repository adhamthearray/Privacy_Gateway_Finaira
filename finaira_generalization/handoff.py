"""Idempotent import of the Finaira generalization handoff sources.

The importer is deliberately source-shaped: source rows retain their review
state, derived candidates are regenerated from authoritative rows, and no
source-backed record is promoted merely because it was present in a candidate
export.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import (
    Bank, Base,
    BankAlias,
    BankCandidate,
    BankEvidence,
    DataSource,
    GovernmentAlias,
    GovernmentCandidateReview,
    GovernmentCategory,
    GovernmentEntity,
    GovernmentEntityCategory,
    GovernmentReviewQueue,
    ImportBatch,
    IndustryCategory,
    IndustryQIDMapping,
    NaturalEarthCountryAlias,
    NaturalEarthCountry,
    NationalityAliasV2,
    NationalityAliasReviewProvenance,
    NationalityCountry,
    NationalityDeduplication,
    NationalityGeoJoin,
    Organization,
    OrganizationAlias,
    OrganizationExclusion,
    OrganizationIndustry,
    OrganizationReviewQueue,
    init_db,
)
from .natural_earth import extract_natural_earth_csv
from .normalization import normalize

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = Path(
    r"C:\Users\domma\Downloads\Finaira_Generalization_DB_Codex_Handoff_2026-11-12_ext"
)
NATURAL_EARTH_ZIP = ROOT / "data/sources/natural_earth/ne_10m_admin_0_countries_v5.1.1.zip"
NATURAL_EARTH_CSV = ROOT / "data/sources/natural_earth/ne_10m_admin_0_countries_v5.1.1.csv"
NATURAL_EARTH_URL = "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/"
NATIONALITY_VARIANT_REVIEW_CSV = ROOT / "reports/nationality_improvement/nationality_variant_review_queue.csv"
COUNTRY_REVIEWED_ALIAS_CSV = ROOT / "data/sources/wikidata/wikidata_country_reviewed_aliases_ar_en_v1.csv"
BANK_ALIAS_APPROVAL_CSV = ROOT / "data/sources/bank/bank_alias_user_approvals.csv"
GOVERNMENT_ALIAS_APPROVAL_CSV = ROOT / "data/sources/government/government_alias_user_approvals.csv"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(value) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value and value.lower() != "nan" else None


def _bool(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _tokens(value) -> list[str]:
    return [x.strip() for x in re.split(r"[;,|]", str(value or "")) if x.strip()]


def _qid(value) -> str | None:
    match = re.search(r"\bQ\d+\b", str(value or ""))
    return match.group(0) if match else None


def _stable(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode("utf-8")).hexdigest()[:64]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _source(
    session: Session,
    name: str,
    path: Path,
    *,
    version: str = "handoff-2026-11-12",
    url: str | None = None,
    license_text: str | None = None,
) -> DataSource:
    checksum = _sha256(path)
    source = session.scalar(select(DataSource).where(DataSource.name == name))
    if source is None:
        source = DataSource(name=name)
        session.add(source)
    source.version = version
    source.source_url = url or str(path)
    source.license = license_text
    source.checksum = checksum
    source.retrieved_at = datetime.now(timezone.utc).isoformat()
    session.flush()
    return source


def _put(session: Session, model, key: str, values: dict):
    item = session.get(model, key)
    if item is None:
        primary_key = next(iter(model.__table__.primary_key.columns.keys()))
        item = model(**{primary_key: key})
        session.add(item)
    for field, value in values.items():
        setattr(item, field, value)
    return item


def _natural_earth(handoff_root: Path) -> Path:
    if not NATURAL_EARTH_CSV.exists():
        if not NATURAL_EARTH_ZIP.exists():
            raise FileNotFoundError(f"Missing Natural Earth artifact: {NATURAL_EARTH_ZIP}")
        extract_natural_earth_csv(NATURAL_EARTH_ZIP, NATURAL_EARTH_CSV)
    return NATURAL_EARTH_CSV


def _import_nationality(session: Session, handoff_root: Path, metrics: dict, report_dir: Path):
    expanded_source_path = ROOT / "data/sources/wikidata/wikidata_nationality_aliases_ar_en_v2.csv"
    source_path = expanded_source_path if expanded_source_path.exists() else handoff_root / "inputs/nationality/wikidata_nationality_aliases.csv"
    qid_index_path = handoff_root / "inputs/nationality/wikidata_country_qid_index_DERIVED.csv"
    country_alias_path = ROOT / "data/sources/wikidata/wikidata_country_aliases_ar_en_v1.csv"
    ne_csv = _natural_earth(handoff_root)
    alias_source_name = "wikidata_nationality_aliases_ar_en_v2" if expanded_source_path.exists() else "handoff_nationality_aliases"
    alias_source = _source(session, alias_source_name, source_path, version="wikidata-p1549-ar-en" if expanded_source_path.exists() else "handoff-2026-11-12", license_text="Wikidata structured data CC0")
    variant_source = _source(session, "nationality_variant_review_queue", NATIONALITY_VARIANT_REVIEW_CSV, version="review-queue-v1", license_text="Human-reviewed derivative of Wikidata CC0 aliases") if NATIONALITY_VARIANT_REVIEW_CSV.exists() else None
    country_alias_source = _source(session, "wikidata_country_aliases_ar_en_v1", country_alias_path, version="wikidata-labels-aliases-ar-en" , license_text="Wikidata structured data CC0") if country_alias_path.exists() else None
    country_reviewed_source = _source(session, "wikidata_country_reviewed_aliases_ar_en_v1", COUNTRY_REVIEWED_ALIAS_CSV, version="ner-country-review-v1", license_text="Human-reviewed derivative of Wikidata CC0 country identity evidence") if COUNTRY_REVIEWED_ALIAS_CSV.exists() else None
    _source(session, "handoff_nationality_qid_index_derived", qid_index_path, license_text="Derived audit; source rows remain Wikidata CC0")
    ne_source = _source(
        session,
        "natural_earth_admin0_10m_v5.1.1_csv",
        ne_csv,
        version="5.1.1",
        url=NATURAL_EARTH_URL,
        license_text="Natural Earth public-domain terms",
    )
    rows = _read_csv(source_path)
    ne_rows = _read_csv(ne_csv)
    ne_by_qid = {row.get("wikidata_qid"): row for row in ne_rows if _text(row.get("wikidata_qid"))}
    # The expanded Wikidata source is a complete deterministic snapshot of
    # the supplied aliases plus the refreshed P1549 response. Rebuild only
    # these source-shaped rows so repeated refreshes cannot retain aliases
    # that disappeared from the snapshot or accumulate duplicates.
    session.execute(delete(NationalityAliasReviewProvenance))
    session.execute(delete(NationalityAliasV2))
    session.execute(delete(NationalityDeduplication))
    session.execute(delete(NationalityGeoJoin))
    session.execute(delete(NationalityCountry))
    session.execute(delete(NaturalEarthCountryAlias))
    if NATURAL_EARTH_ZIP.exists():
        _source(
            session,
            "natural_earth_admin0_10m_v5.1.1_zip",
            NATURAL_EARTH_ZIP,
            version="5.1.1",
            url=NATURAL_EARTH_URL,
            license_text="Natural Earth public-domain terms",
        )
    for row in ne_rows:
        _put(session, NaturalEarthCountry, row["natural_earth_id"], {"wikidata_qid": _text(row.get("wikidata_qid")), "iso_a2": _text(row.get("iso_a2")), "name_en": _text(row.get("name_en")), "name_ar": _text(row.get("name_ar")), "subregion": _text(row.get("subregion")), "region_un": _text(row.get("region_un")), "continent": _text(row.get("continent")), "source_id": ne_source.source_id, "source_version": "5.1.1"})
    country_alias_count = 0
    country_reviewed_alias_count = 0
    if country_alias_source is not None:
        for row in _read_csv(country_alias_path):
            qid = _qid(row.get("wikidata_qid") or row.get("country"))
            natural = ne_by_qid.get(qid)
            alias = _text(row.get("alias_text"))
            language = (_text(row.get("language")) or "").lower()
            if natural is None or not alias or language not in {"ar", "en"}:
                continue
            normalized = normalize(alias, language)
            # The table intentionally has one lookup row per normalized alias
            # and language for a Natural Earth country. Raw source spellings
            # remain preserved in the checked-in source CSV; runtime lookup
            # must not create duplicate normalized rows.
            alias_id = _stable("natural-earth-country-alias", natural["natural_earth_id"], language, normalized)
            _put(session, NaturalEarthCountryAlias, alias_id, {"natural_earth_id": natural["natural_earth_id"], "alias_text": alias, "normalized_alias": normalized, "language": language, "alias_kind": _text(row.get("alias_kind")) or "wikidata_alias", "source_property": _text(row.get("source_property")) or "wikidata", "source_id": country_alias_source.source_id, "verification_status": "SOURCE_VERIFIED", "enabled_for_lookup": True})
            country_alias_count += 1
    if country_reviewed_source is not None:
        for row in _read_csv(COUNTRY_REVIEWED_ALIAS_CSV):
            if _text(row.get("review_decision")) != "APPROVED" or _text(row.get("verification_status")) != "REVIEWED":
                continue
            qid = _qid(row.get("country_qid") or row.get("wikidata_qid"))
            natural = ne_by_qid.get(qid) if qid else None
            alias = _text(row.get("candidate_value") or row.get("alias_text"))
            language = (_text(row.get("language")) or "").lower()
            if natural is None or not alias or language not in {"ar", "en"} or not _text(row.get("evidence_reference")):
                continue
            iso = (_text(row.get("iso2")) or "").upper()
            if iso and iso != (_text(natural.get("iso_a2")) or "").upper():
                raise ValueError(f"COUNTRY_REVIEW_ISO_MISMATCH:{alias}:{qid}:{iso}")
            normalized = normalize(alias, language)
            existing = session.scalars(select(NaturalEarthCountryAlias).where(NaturalEarthCountryAlias.language == language, NaturalEarthCountryAlias.normalized_alias == normalized)).all()
            conflicting = {item.natural_earth_id for item in existing if item.natural_earth_id != natural["natural_earth_id"]}
            if conflicting:
                raise ValueError(f"COUNTRY_REVIEW_ALIAS_COLLISION:{alias}:{sorted(conflicting)}")
            alias_id = _stable("natural-earth-country-reviewed-alias", natural["natural_earth_id"], language, normalized)
            _put(session, NaturalEarthCountryAlias, alias_id, {"natural_earth_id": natural["natural_earth_id"], "alias_text": alias, "normalized_alias": normalized, "language": language, "alias_kind": "reviewed_variant", "source_property": "NER_REVIEW", "source_id": country_reviewed_source.source_id, "verification_status": "REVIEWED", "enabled_for_lookup": True})
            country_reviewed_alias_count += 1
    by_qid = {r["wikidata_qid"]: r for r in ne_rows if _text(r.get("wikidata_qid"))}
    by_iso: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ne_rows:
        if _text(row.get("iso_a2")):
            by_iso[row["iso_a2"].upper()].append(row)

    # A source snapshot can contain more than one Wikidata identity for the
    # same current ISO country.  Natural Earth is the authority for choosing
    # the runtime identity; other QIDs are retained only in the audit log.
    raw_iso_by_qid: dict[str, str] = {}
    raw_rows_by_qid: dict[str, list[dict[str, str]]] = defaultdict(list)
    qids_by_iso: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        qid = _qid(row.get("country"))
        if not qid:
            continue
        iso = (_text(row.get("iso2")) or "").upper()
        raw_iso_by_qid.setdefault(qid, iso)
        raw_rows_by_qid[qid].append(row)
        if iso:
            qids_by_iso[iso].add(qid)

    qid_canonical_map = {qid: qid for qid in raw_iso_by_qid}
    for iso, qids in qids_by_iso.items():
        if len(qids) <= 1:
            continue
        natural_qids = qids.intersection(ne_by_qid)
        if len(natural_qids) != 1:
            # Never guess where Natural Earth cannot select one identity.
            continue
        canonical_qid = next(iter(natural_qids))
        for qid in qids:
            qid_canonical_map[qid] = canonical_qid

    canonical_iso_by_qid: dict[str, str] = {}
    canonical_rows_by_qid: dict[str, list[dict[str, str]]] = defaultdict(list)
    for raw_qid, canonical_qid in qid_canonical_map.items():
        canonical_rows_by_qid[canonical_qid].extend(raw_rows_by_qid[raw_qid])
        canonical_iso_by_qid.setdefault(canonical_qid, raw_iso_by_qid[raw_qid])
    for canonical_qid in canonical_rows_by_qid:
        natural_iso = _text(ne_by_qid.get(canonical_qid, {}).get("iso_a2"))
        if natural_iso:
            canonical_iso_by_qid[canonical_qid] = natural_iso.upper()

    deduplication_rows: list[dict[str, str]] = []
    for raw_qid, canonical_qid in sorted(qid_canonical_map.items()):
        if raw_qid == canonical_qid:
            continue
        iso = canonical_iso_by_qid.get(canonical_qid) or raw_iso_by_qid.get(raw_qid) or ""
        deduplication_rows.append({
            "deduplication_type": "COUNTRY_QID",
            "removed_key": raw_qid,
            "kept_key": canonical_qid,
            "removed_country_qid": raw_qid,
            "kept_country_qid": canonical_qid,
            "iso2": iso,
            "alias_text": "",
            "normalized_alias": "",
            "language": "",
            "reason": "SAME_ISO_NATURAL_EARTH_CANONICAL_QID",
        })

    by_qid_input: dict[str, tuple[str, str]] = {}
    for raw_qid, raw_rows in raw_rows_by_qid.items():
        qid = qid_canonical_map[raw_qid]
        iso = canonical_iso_by_qid.get(qid, raw_iso_by_qid.get(raw_qid, ""))
        label = ""
        for row in sorted(raw_rows, key=lambda item: _qid(item.get("country")) != qid):
            label = _text(row.get("countryLabel")) or ""
            if label:
                break
        by_qid_input.setdefault(qid, (iso, label))
    for qid, (iso, label) in sorted(by_qid_input.items()):
        _put(
            session,
            NationalityCountry,
            qid,
            {"iso2": iso, "country_label": label, "source_id": alias_source.source_id, "verification_status": "SOURCE_VERIFIED"},
        )
    for item in deduplication_rows:
        _put(
            session,
            NationalityDeduplication,
            _stable("nationality-deduplication", item["deduplication_type"], item["removed_key"], item["kept_key"], item["iso2"]),
            {**item, "source_id": alias_source.source_id},
        )

    audit_rows = []
    status_counts = Counter()
    for qid, (iso, _label) in sorted(by_qid_input.items()):
        qid_row = by_qid.get(qid)
        iso_rows = by_iso.get(iso, []) if iso else []
        natural = None
        status = "UNMATCHED"
        method = None
        note = None
        if qid_row is not None:
            if iso and qid_row.get("iso_a2") and qid_row["iso_a2"].upper() != iso:
                status = "MISMATCH"
                note = f"QID matched Natural Earth but ISO_A2 differs: {iso} != {qid_row.get('iso_a2')}"
            else:
                status = "MATCHED_QID"
                method = "QID"
                natural = qid_row
        elif len(iso_rows) == 1:
            status = "MATCHED_ISO"
            method = "ISO_A2"
            natural = iso_rows[0]
        elif len(iso_rows) > 1:
            status = "AMBIGUOUS"
            note = f"ISO_A2 has {len(iso_rows)} Natural Earth rows"
        else:
            note = "No Natural Earth WIKIDATAID or unambiguous ISO_A2 match"
        _put(
            session,
            NationalityGeoJoin,
            qid,
            {
                "iso2": iso,
                "natural_earth_id": natural.get("natural_earth_id") if natural else None,
                "join_status": status,
                "match_method": method,
                "audit_note": note,
                "source_id": ne_source.source_id,
            },
        )
        status_counts[status] += 1
        audit_rows.append({"country_qid": qid, "iso2": iso, "natural_earth_id": natural.get("natural_earth_id") if natural else "", "join_status": status, "match_method": method or "", "audit_note": note or ""})

    # Collapse source spellings by canonical country, language, and normalized
    # alias.  Keep one deterministic display spelling while recording every
    # discarded source row in the audit table.
    source_aliases: dict[tuple[str, str, str, str], list[tuple[str, str, str]]] = defaultdict(list)
    for row in rows:
        raw_qid = _qid(row.get("country"))
        if not raw_qid:
            continue
        qid = qid_canonical_map[raw_qid]
        lang = (_text(row.get("language")) or "").lower()
        alias = _text(row.get("nationality"))
        if not alias or lang not in {"ar", "en"}:
            continue
        iso = canonical_iso_by_qid.get(qid, (_text(row.get("iso2")) or "").upper())
        normalized = normalize(alias, lang)
        source_aliases[(qid, iso, lang, normalized)].append((alias, raw_qid, (_text(row.get("iso2")) or "").upper()))

    def _preferred_alias(items: list[tuple[str, str, str]], language: str) -> tuple[str, str, str]:
        if language == "en":
            return max(items, key=lambda item: (item[0][:1].isupper(), len(item[0]), item[0]))
        return max(items, key=lambda item: (len(item[0]), item[0]))

    alias_count = 0
    source_alias_keys: dict[tuple[str, str, str, str], str] = {}
    for (qid, iso, lang, normalized), items in sorted(source_aliases.items()):
        preferred, preferred_raw_qid, _preferred_raw_iso = _preferred_alias(items, lang)
        preferred_item = (preferred, preferred_raw_qid, _preferred_raw_iso)
        kept_preferred = False
        key = _stable("nationality-alias-canonical", qid, iso, lang, normalized)
        source_alias_keys[(qid, iso, lang, normalized)] = key
        _put(
            session,
            NationalityAliasV2,
            key,
            {"country_qid": qid, "iso2": iso, "alias_text": preferred, "normalized_alias": normalized, "language": lang, "source_id": alias_source.source_id, "verification_status": "SOURCE_VERIFIED"},
        )
        alias_count += 1
        for alias, raw_qid, raw_iso in items:
            if not kept_preferred and (alias, raw_qid, raw_iso) == preferred_item:
                kept_preferred = True
                continue
            reason = "DUPLICATE_COUNTRY_QID_SAME_ISO" if raw_qid != qid else "DUPLICATE_NORMALIZED_ALIAS_SAME_COUNTRY"
            deduplication_rows.append({
                "deduplication_type": "ALIAS",
                "removed_key": _stable(raw_qid, raw_iso, lang, normalized, alias),
                "kept_key": key,
                "removed_country_qid": raw_qid,
                "kept_country_qid": qid,
                "iso2": iso,
                "alias_text": alias,
                "normalized_alias": normalized,
                "language": lang,
                "reason": reason,
            })
            _put(
                session,
                NationalityDeduplication,
                _stable("nationality-deduplication", "ALIAS", raw_qid, key, lang, normalized, alias),
                {**deduplication_rows[-1], "source_id": alias_source.source_id},
            )
    reviewed_variant_keys = set()
    reviewed_provenance_keys = set()
    reviewed_alias_first: dict[str, tuple[str, str, str, str, str]] = {}
    if variant_source is not None:
        for variant in _read_csv(NATIONALITY_VARIANT_REVIEW_CSV):
            if (_text(variant.get("review_decision")) or "").upper() != "APPROVED":
                continue
            if not _text(variant.get("evidence_reference")):
                continue
            raw_qid = _qid(variant.get("candidate_qid"))
            lang = (_text(variant.get("language")) or "").lower()
            alias = _text(variant.get("corpus_value"))
            iso = (_text(variant.get("candidate_iso2")) or "").upper()
            if not raw_qid or raw_qid not in qid_canonical_map or lang not in {"ar", "en"} or not alias:
                continue
            qid = qid_canonical_map[raw_qid]
            natural_iso = (_text(by_qid.get(qid, {}).get("iso_a2")) or "").upper() if by_qid.get(qid) else ""
            if not iso or iso == "-99":
                iso = natural_iso or canonical_iso_by_qid[qid]
            iso = iso or canonical_iso_by_qid[qid]
            normalized = normalize(alias, lang)
            alias_key_tuple = (qid, iso, lang, normalized)
            key = source_alias_keys.get(alias_key_tuple)
            if key is None:
                key = _stable("nationality-alias-canonical", qid, iso, lang, normalized)
                source_alias_keys[alias_key_tuple] = key
                _put(
                    session,
                    NationalityAliasV2,
                    key,
                    {"country_qid": qid, "iso2": iso, "alias_text": alias, "normalized_alias": normalized, "language": lang, "source_id": variant_source.source_id, "verification_status": "REVIEWED"},
                )
            elif not session.get(NationalityAliasV2, key):
                _put(
                    session,
                    NationalityAliasV2,
                    key,
                    {"country_qid": qid, "iso2": iso, "alias_text": alias, "normalized_alias": normalized, "language": lang, "source_id": variant_source.source_id, "verification_status": "REVIEWED"},
                )
            reviewed_variant_keys.add(key)
            base_alias = _text(variant.get("base_alias")) or alias
            derivation_rule = _text(variant.get("derivation_rule")) or "reviewed"
            if key in reviewed_alias_first:
                deduplication_rows.append({
                    "deduplication_type": "ALIAS",
                    "removed_key": _stable("reviewed-nationality-alias", raw_qid, iso, lang, normalized, alias, base_alias, derivation_rule, _text(variant.get("evidence_reference")) or ""),
                    "kept_key": key,
                    "removed_country_qid": raw_qid,
                    "kept_country_qid": qid,
                    "iso2": iso,
                    "alias_text": alias,
                    "normalized_alias": normalized,
                    "language": lang,
                    "reason": "DUPLICATE_REVIEWED_ALIAS_SAME_COUNTRY",
                })
                _put(
                    session,
                    NationalityDeduplication,
                    _stable("nationality-deduplication", "REVIEWED_ALIAS", deduplication_rows[-1]["removed_key"], key),
                    {**deduplication_rows[-1], "source_id": variant_source.source_id},
                )
            else:
                reviewed_alias_first[key] = (raw_qid, iso, lang, normalized, alias)
            provenance_key = _stable("nationality-review-provenance", key, base_alias, derivation_rule)
            _put(
                session,
                NationalityAliasReviewProvenance,
                provenance_key,
                {"alias_key": key, "corpus_value": alias, "base_alias": base_alias, "derivation_rule": derivation_rule, "evidence_reference": _text(variant.get("evidence_reference")) or "", "review_status": "REVIEWED", "source_id": variant_source.source_id},
            )
            reviewed_provenance_keys.add(provenance_key)
    report_dir.mkdir(parents=True, exist_ok=True)
    with (report_dir / "nationality_natural_earth_join_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)
    dedup_fields = ["deduplication_type", "removed_key", "kept_key", "removed_country_qid", "kept_country_qid", "iso2", "alias_text", "normalized_alias", "language", "reason"]
    with (report_dir / "nationality_deduplication_report.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=dedup_fields)
        writer.writeheader()
        writer.writerows(deduplication_rows)
    metrics.update({
        "nationality_aliases_v2": alias_count + len(reviewed_variant_keys - set(source_alias_keys.values())),
        "nationality_reviewed_variants": len(reviewed_variant_keys),
        "nationality_review_provenance": len(reviewed_provenance_keys),
        "nationality_deduplications": len(deduplication_rows),
        "nationality_country_qid_merges": sum(item["deduplication_type"] == "COUNTRY_QID" for item in deduplication_rows),
        "nationality_alias_merges": sum(item["deduplication_type"] == "ALIAS" for item in deduplication_rows),
        "natural_earth_country_aliases": country_alias_count,
        "natural_earth_reviewed_country_aliases": country_reviewed_alias_count,
        "nationality_distinct_qids": len(by_qid_input),
        "natural_earth_rows": len(ne_rows),
        "natural_earth_join_status": dict(status_counts),
    })


def _import_banks(session: Session, root: Path, metrics: dict, report_dir: Path):
    bank_dir = root / "inputs/bank"
    master_path = bank_dir / "banks_FINAL_evidence.csv"
    evidence_path = bank_dir / "bank_islamic_mixed_source_evidence.csv"
    alias_path = bank_dir / "bank_aliases_REVIEW.csv"
    master_source = _source(session, "banks_FINAL_evidence", master_path, license_text="Supplied CBE roster and research evidence; row-level URLs remain evidence only")
    evidence_source = _source(session, "bank_islamic_mixed_source_evidence", evidence_path, license_text="Supplied evidence index")
    alias_source = _source(session, "bank_aliases_REVIEW", alias_path, license_text="Supplied review-only aliases")
    approval_source = _source(session, "bank_alias_user_approvals", BANK_ALIAS_APPROVAL_CSV, license_text="Explicit user approval decisions; not external evidence") if BANK_ALIAS_APPROVAL_CSV.exists() else None
    approval_rows = _read_csv(BANK_ALIAS_APPROVAL_CSV) if BANK_ALIAS_APPROVAL_CSV.exists() else []
    approvals = {(r["bank_id"], r["language"], r["alias"], r["alias_kind"]): r for r in approval_rows}
    rows = _read_csv(master_path)
    model_counts = Counter(r["finance_model"] for r in rows)
    for row in rows:
        _put(session, Bank, row["bank_id"], {"cbe_list_number": _text(row.get("cbe_list_number")), "name_en": row["bank_name_en"], "name_ar": _text(row.get("bank_name_ar")), "finance_model": row["finance_model"], "finance_model_label_en": row["finance_model_label_en"], "finance_model_label_ar": row["finance_model_label_ar"], "classification_rule": row["classification_rule"], "evidence_status": row["evidence_status"], "evidence_confidence": _text(row.get("evidence_confidence")), "as_of_date": _text(row.get("as_of_date")), "evidence_review_status": _text(row.get("evidence_review_status")), "source_id": master_source.source_id})
    evidence_rows = _read_csv(evidence_path)
    for row in evidence_rows:
        _put(session, BankEvidence, row["evidence_id"], {"bank_id": row["bank_id"], "finance_model": row["finance_model"], "source_type": row["source_type"], "source_url": _text(row.get("source_url")), "evidence_summary_en": _text(row.get("evidence_summary_en")), "source_publication_or_update": _text(row.get("source_publication_or_update")), "checked_on": _text(row.get("checked_on")), "source_strength": _text(row.get("source_strength")), "notes": _text(row.get("notes")), "source_id": evidence_source.source_id})
    for row in _read_csv(alias_path):
        alias = _text(row.get("alias"))
        if not alias:
            continue
        status = row["review_status"]
        approval = approvals.get((row["bank_id"], row["language"], alias, row.get("alias_kind")))
        if approval:
            status = approval.get("approval_status") or "APPROVED_BY_USER"
        enabled = status in {"source_supported", "APPROVED_BY_USER"}
        key = _stable(row["bank_id"], row.get("language"), alias, row.get("alias_kind"))
        _put(session, BankAlias, key, {"bank_id": row["bank_id"], "alias_text": alias, "normalized_alias": normalize(alias, row.get("language")), "language": row["language"], "alias_kind": row.get("alias_kind"), "review_status": status, "enabled_for_lookup": enabled, "source_id": approval_source.source_id if approval and approval_source else alias_source.source_id})
    # Regenerate only the handoff-owned Egyptian bank candidates.  GCC audit
    # candidates are maintained by scripts/import_gcc_bank_audit.py and must
    # survive a later full handoff refresh.
    legacy_bank_ids = [row["bank_id"] for row in rows]
    session.execute(delete(BankCandidate).where(BankCandidate.bank_id.in_(legacy_bank_ids)))
    generic = {"BANKING_INSTITUTION": ("Banking institution", "مؤسسة مصرفية"), "FINANCIAL_INSTITUTION": ("Financial institution", "مؤسسة مالية")}
    for row in rows:
        bank = session.get(Bank, row["bank_id"])
        levels = [("EXACT", 0, bank.name_en, bank.name_ar, None, True, True, False, None), ("FINANCE_MODEL", 1, bank.finance_model_label_en, bank.finance_model_label_ar, model_counts[bank.finance_model], False, False, False, bank.finance_model), ("BANKING_INSTITUTION", 2, generic["BANKING_INSTITUTION"][0], generic["BANKING_INSTITUTION"][1], len(rows), False, False, False, None), ("FINANCIAL_INSTITUTION", 3, generic["FINANCIAL_INSTITUTION"][0], generic["FINANCIAL_INSTITUTION"][1], len(rows), False, False, False, None), ("SUPPRESSED", 4, None, None, None, False, False, True, None)]
        for code, rank, en, ar, population, exact, local, suppression, model in levels:
            cid = f"{bank.bank_id}__{code}"
            _put(session, BankCandidate, cid, {"bank_id": bank.bank_id, "level_code": code, "specificity_rank": rank, "label_en": en, "label_ar": ar, "finance_model": model, "category_population_count": population, "is_exact": exact, "is_local_only": local, "is_suppression": suppression, "disclosure_approved": False, "evidence_status": bank.evidence_status, "verification_status": "PROVISIONAL", "source_id": master_source.source_id, "derivation_method": "derived:final-bank-master"})
    evidence_bank_ids = {r["bank_id"] for r in evidence_rows}
    metrics.update({"banks": len(rows), "bank_model_counts": dict(model_counts), "bank_evidence": len(evidence_rows), "bank_evidence_bank_ids": len(evidence_bank_ids), "bank_candidates": len(rows) * 5, "bank_arabic_master_names_blank": sum(not _text(r.get("bank_name_ar")) for r in rows), "bank_user_approved_aliases": len(approval_rows)})


def _import_organizations(session: Session, root: Path, metrics: dict):
    org_dir = root / "inputs/organizations"
    org_path = org_dir / "organizations_312_PENDING_VERIFICATION.csv"
    taxonomy_path = org_dir / "industry_taxonomy_ar_en.csv"
    mapping_path = org_dir / "wikidata_industry_qid_mapping.csv"
    exclusion_path = org_dir / "organization_religious_exclusions.csv"
    queue_path = org_dir / "organization_review_queue.csv"
    org_source = _source(session, "organizations_312_PENDING_VERIFICATION", org_path, license_text="Wikidata structured data CC0; candidate identities remain pending")
    taxonomy_source = _source(session, "industry_taxonomy_ar_en", taxonomy_path, license_text="Finaira-authored taxonomy")
    mapping_source = _source(session, "wikidata_industry_qid_mapping", mapping_path, license_text="Wikidata concept links; row-level review status retained")
    exclusion_source = _source(session, "organization_religious_exclusions", exclusion_path, license_text="Supplied review exclusions")
    queue_source = _source(session, "organization_review_queue", queue_path, license_text="Supplied review queue")
    categories = _read_csv(taxonomy_path)
    # The handoff intentionally treats ORGANIZATION as a virtual root.  It is
    # materialized only to satisfy the real self-FK while retaining all 63
    # source category rows unchanged.
    _put(session, IndustryCategory, "ORGANIZATION", {"parent_code": None, "label_en": "Organization", "label_ar": "منظمة", "category_kind": "ROOT", "license": "Finaira-authored taxonomy (virtual root)", "source_id": taxonomy_source.source_id})
    pending_categories = list(categories)
    while pending_categories:
        progressed = False
        for row in pending_categories[:]:
            parent = _text(row.get("parent_code")) or "ORGANIZATION"
            if parent == "ORGANIZATION" or session.get(IndustryCategory, parent) is not None:
                _put(session, IndustryCategory, row["category_code"], {"parent_code": parent, "label_en": row["label_en"], "label_ar": row["label_ar"], "category_kind": row["category_kind"], "license": row.get("licence"), "source_id": taxonomy_source.source_id})
                pending_categories.remove(row)
                progressed = True
        if not progressed:
            raise ValueError("INDUSTRY_CATEGORY_PARENT_MISSING")
    mappings = {}
    for row in _read_csv(mapping_path):
        qid = row["wikidata_industry_qid"]
        mid = _stable("industry", qid, row.get("sector_code"), row.get("subcategory_code"))
        mappings.setdefault(qid, []).append(mid)
        _put(session, IndustryQIDMapping, mid, {"industry_qid": qid, "source_industry_label_en": _text(row.get("source_industry_label_en")), "sector_code": _text(row.get("sector_code")), "subcategory_code": _text(row.get("subcategory_code")), "subcategory_label_en": _text(row.get("subcategory_label_en")), "subcategory_label_ar": _text(row.get("subcategory_label_ar")), "review_status": row["review_status"], "source_id": mapping_source.source_id})
    org_rows = _read_csv(org_path)
    for row in org_rows:
        qid = _qid(row.get("organization_qid") or row.get("organization"))
        if not qid:
            continue
        flags = _text(row.get("review_flags"))
        names = " ".join([row.get("nameEn", ""), row.get("industryNames", ""), row.get("finaira_sector_codes", "")]).lower()
        source_kind = "UNIVERSITY" if "university" in names or "EDU_UNIVERSITY" in names else "CORPORATION"
        # All organization-like records share the CORPORATION runtime entity.
        # Preserve the source classification for audit and later review.
        kind = "CORPORATION"
        source_kind_flag = f"source_semantic_kind={source_kind}"
        flags = f"{flags};{source_kind_flag}" if flags else source_kind_flag
        _put(session, Organization, qid, {"name_en": _text(row.get("nameEn")), "name_ar": _text(row.get("nameAr")), "semantic_kind": kind, "identity_verification_status": "PENDING_IDENTITY_VALIDATION", "import_decision": row.get("import_decision") or "CANDIDATE_PENDING_IDENTITY_VALIDATION", "import_status": _text(row.get("import_status")), "review_flags": flags, "source_id": org_source.source_id})
        for lang, field in (("en", "nameEn"), ("ar", "nameAr")):
            alias = _text(row.get(field))
            if alias:
                aid = _stable("org-alias", qid, lang, alias)
                _put(session, OrganizationAlias, aid, {"organization_qid": qid, "alias_text": alias, "normalized_alias": normalize(alias, lang), "language": lang, "enabled_for_lookup": True, "verification_status": "PENDING_IDENTITY_VALIDATION", "source_id": org_source.source_id})
        qids = _tokens(row.get("industryQIDs"))
        if not qids:
            qids = [x for x in _tokens(row.get("finaira_sector_codes")) if x]
        for industry_qid in qids:
            mids = mappings.get(industry_qid, [None])
            for mid in mids:
                mapping = session.get(IndustryQIDMapping, mid) if mid else None
                lid = _stable("org-industry", qid, industry_qid, mid, row.get("finaira_sector_codes"))
                _put(session, OrganizationIndustry, lid, {"organization_qid": qid, "mapping_id": mid, "industry_qid": industry_qid, "sector_code": mapping.sector_code if mapping else _text(row.get("final_sector_codes") or row.get("finaira_sector_codes")), "subcategory_code": mapping.subcategory_code if mapping else _text(row.get("final_subcategory_codes")), "mapping_status": mapping.review_status if mapping else "UNMAPPED", "import_decision": row.get("import_decision") or "CANDIDATE_PENDING_IDENTITY_VALIDATION", "verification_status": "REVIEW_ONLY", "source_id": mapping_source.source_id if mapping else org_source.source_id})
    for row in _read_csv(exclusion_path):
        qid = _qid(row.get("organization_qid") or row.get("organization"))
        eid = _stable("org-exclusion", qid or row.get("organization"), row.get("exclusion_reason"))
        _put(session, OrganizationExclusion, eid, {"organization_qid": qid, "name_en": _text(row.get("nameEn")), "name_ar": _text(row.get("nameAr")), "reason": row.get("exclusion_reason") or "REVIEW_EXCLUSION", "import_decision": row.get("import_decision") or "REVIEW_REQUIRED", "source_id": exclusion_source.source_id})
    for row in _read_csv(queue_path):
        qid = _qid(row.get("organization_qid") or row.get("organization"))
        rid = _stable("org-review", qid or row.get("organization"), row.get("import_decision"), row.get("review_reason"))
        _put(session, OrganizationReviewQueue, rid, {"organization_qid": qid, "import_status": _text(row.get("import_status")), "review_flags": _text(row.get("review_flags")), "import_decision": _text(row.get("import_decision")), "review_reason": _text(row.get("review_reason")), "source_id": queue_source.source_id})
    metrics.update({"organizations": len({q for q in (_qid(r.get("organization_qid") or r.get("organization")) for r in org_rows) if q}), "industry_categories_source_rows": len(categories), "industry_categories_materialized": len(categories) + 1, "industry_qid_mappings": len(_read_csv(mapping_path)), "organization_review_queue": len(_read_csv(queue_path)), "organization_exclusions": len(_read_csv(exclusion_path)), "organization_arabic_names_missing": sum(not _text(r.get("nameAr")) for r in org_rows)})


def _import_government(session: Session, root: Path, metrics: dict):
    gov_dir = root / "inputs/government"
    entity_path = gov_dir / "government_entities_SEED.csv"
    alias_path = gov_dir / "government_aliases_SEED.csv"
    category_path = gov_dir / "government_categories_ar_en.csv"
    candidate_path = gov_dir / "government_candidate_catalog_REVIEW.csv"
    queue_path = gov_dir / "government_review_queue.csv"
    entity_source = _source(session, "government_entities_SEED", entity_path, license_text="Supplied optional review-only seed")
    alias_source = _source(session, "government_aliases_SEED", alias_path, license_text="Supplied review-only aliases")
    approval_source = _source(session, "government_alias_user_approvals", GOVERNMENT_ALIAS_APPROVAL_CSV, license_text="Explicit user approval decisions; not external evidence") if GOVERNMENT_ALIAS_APPROVAL_CSV.exists() else None
    approval_rows = _read_csv(GOVERNMENT_ALIAS_APPROVAL_CSV) if GOVERNMENT_ALIAS_APPROVAL_CSV.exists() else []
    approvals = {r["alias_id"]: r for r in approval_rows}
    category_source = _source(session, "government_categories_ar_en", category_path, license_text="Finaira-authored bilingual category structure")
    candidate_source = _source(session, "government_candidate_catalog_REVIEW", candidate_path, license_text="Supplied review-only candidate catalog")
    queue_source = _source(session, "government_review_queue", queue_path, license_text="Supplied review queue")
    entity_rows = _read_csv(entity_path)
    for row in entity_rows:
        _put(session, GovernmentEntity, row["entity_id"], {"name_ar": row["name_ar"], "name_en_provisional": _text(row.get("name_en_provisional")), "country_iso": row["country_iso"], "organization_form_code": _text(row.get("organization_form_code")), "function_code": _text(row.get("function_code")), "wikidata_qid": _text(row.get("wikidata_qid")), "official_source_url": _text(row.get("official_source_url")), "identity_verification_status": row["identity_verification_status"], "function_verification_status": row["function_verification_status"], "english_name_verification_status": row["english_name_verification_status"], "enabled_for_specific_mapping": _bool(row.get("enabled_for_specific_mapping")), "dataset_status": _text(row.get("dataset_status")), "review_notes": _text(row.get("review_notes")), "source_id": entity_source.source_id})
    pending_categories = _read_csv(category_path)
    while pending_categories:
        progressed = False
        for row in pending_categories[:]:
            parent = _text(row.get("parent_category_code"))
            if not parent or session.get(GovernmentCategory, parent) is not None:
                _put(session, GovernmentCategory, row["category_code"], {"label_ar": row["label_ar"], "label_en": row["label_en"], "parent_category_code": parent, "reidentification_risk_hint": _text(row.get("reidentification_risk_hint")), "status": row["status"], "source_id": category_source.source_id})
                pending_categories.remove(row)
                progressed = True
        if not progressed:
            raise ValueError("GOVERNMENT_CATEGORY_PARENT_MISSING")
    for row in _read_csv(alias_path):
        approval = approvals.get(row["alias_id"])
        status = approval.get("approval_status") if approval else row["verification_status"]
        enabled = True if approval else _bool(row.get("enabled_for_lookup"))
        _put(session, GovernmentAlias, row["alias_id"], {"entity_id": row["entity_id"], "language": row["language"], "alias_text": row["alias"], "normalized_alias": normalize(row["alias"], row["language"]), "verification_status": status, "enabled_for_lookup": enabled, "source_url": _text(row.get("source_url")), "source_id": approval_source.source_id if approval and approval_source else alias_source.source_id})
    for row in _read_csv(candidate_path):
        _put(session, GovernmentCandidateReview, row["candidate_id"], {"entity_id": row["entity_id"], "level_code": row["level_code"], "dimension": row["dimension"], "specificity_rank_branch_local": int(row["specificity_rank_branch_local"]), "label_ar": _text(row.get("label_ar")), "label_en": _text(row.get("label_en")), "source_url": _text(row.get("source_url")), "verification_status": row["verification_status"], "requires_policy_approval": _bool(row.get("requires_policy_approval")), "is_local_only": _bool(row.get("is_local_only")), "is_suppression": _bool(row.get("is_suppression")), "default_visible": _bool(row.get("default_visible")), "source_id": candidate_source.source_id})
    category_codes = {r["category_code"] for r in _read_csv(category_path)}
    for row in entity_rows:
        for dimension, code, status in (("FUNCTION", row.get("function_code"), row.get("function_verification_status")), ("FORM", row.get("organization_form_code"), row.get("identity_verification_status"))):
            if code in category_codes:
                lid = _stable("gov-category", row["entity_id"], dimension, code)
                _put(session, GovernmentEntityCategory, lid, {"entity_id": row["entity_id"], "category_code": code, "dimension": dimension, "verification_status": status, "source_id": entity_source.source_id})
    for row in _read_csv(queue_path):
        _put(session, GovernmentReviewQueue, row["entity_id"], {"entity_id": row["entity_id"], "review_identity": _text(row.get("review_identity")), "review_current_status": _text(row.get("review_current_status")), "review_function_category": _text(row.get("review_function_category")), "review_english_name": _text(row.get("review_english_name")), "review_wikidata_qid": _text(row.get("review_wikidata_qid")), "specific_mapping_enabled": _bool(row.get("specific_mapping_enabled")), "source_id": queue_source.source_id})
    metrics.update({"government_entities": len(entity_rows), "government_categories": len(_read_csv(category_path)), "government_aliases": len(_read_csv(alias_path)), "government_user_approved_aliases": len(approval_rows), "government_review_candidates": len(_read_csv(candidate_path)), "government_review_queue": len(_read_csv(queue_path))})


def import_handoff(
    db_path: str | Path = ROOT / "data/processed/finaira_generalization.db",
    handoff_root: str | Path = DEFAULT_HANDOFF,
    report_dir: str | Path = ROOT / "reports",
    *,
    backup: bool = False,
) -> dict:
    """Import all authoritative handoff sources in one transaction."""
    db = Path(db_path)
    root = Path(handoff_root)
    report = Path(report_dir)
    report.mkdir(parents=True, exist_ok=True)
    if backup and db.exists():
        backup_path = db.with_name(f"{db.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db.suffix}")
        copy2(db, backup_path)
    engine = init_db(db)
    # The first development schema briefly used a normalized-alias UNIQUE
    # constraint.  It cannot preserve distinct source spellings that normalize
    # alike, so remove that empty pre-import table once and recreate it from the
    # current additive model.  A populated table is never dropped.
    with engine.begin() as connection:
        exists = connection.exec_driver_sql("SELECT 1 FROM sqlite_master WHERE type='table' AND name='nationality_aliases_v2'").first()
        if exists and connection.exec_driver_sql("SELECT COUNT(*) FROM nationality_aliases_v2").scalar() == 0:
            connection.exec_driver_sql("DROP TABLE nationality_aliases_v2")
            Base.metadata.create_all(engine)
    batch_id = f"handoff-2026-11-12-{_stable(root)[:12]}"
    metrics: dict = {"batch_id": batch_id, "handoff_root": str(root), "status": "COMPLETED"}
    with Session(engine) as session:
        batch = session.get(ImportBatch, batch_id)
        if batch is None:
            batch = ImportBatch(batch_id=batch_id, started_at=datetime.now(timezone.utc).isoformat(), status="RUNNING", manifest_path=str(root / "manifest.csv"))
            session.add(batch)
        else:
            batch.started_at = datetime.now(timezone.utc).isoformat()
            batch.status = "RUNNING"
            batch.error_text = None
        try:
            _import_nationality(session, root, metrics, report)
            _import_banks(session, root, metrics, report)
            _import_organizations(session, root, metrics)
            _import_government(session, root, metrics)
            batch.status = "COMPLETED"
            batch.completed_at = datetime.now(timezone.utc).isoformat()
            batch.counts_json = json.dumps(metrics, ensure_ascii=False, sort_keys=True)
            session.commit()
        except Exception as exc:
            session.rollback()
            failed = session.get(ImportBatch, batch_id)
            if failed is None:
                failed = ImportBatch(batch_id=batch_id, started_at=datetime.now(timezone.utc).isoformat(), status="FAILED", manifest_path=str(root / "manifest.csv"))
                session.add(failed)
            failed.status = "FAILED"
            failed.completed_at = datetime.now(timezone.utc).isoformat()
            failed.error_text = f"{type(exc).__name__}: {exc}"
            session.commit()
            raise
    (report / "handoff_import_report.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (report / "handoff_import_report.md").write_text("# Handoff import report\n\n" + "\n".join(f"- **{key}**: {value}" for key, value in metrics.items()), encoding="utf-8")
    return metrics

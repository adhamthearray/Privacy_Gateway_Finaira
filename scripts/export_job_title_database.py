"""Export the complete production JOB_TITLE/ESCO/ISCO inventory from SQLite."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira_generalization.db import DataSource, IscoGroup, Occupation, OccupationAlias, OccupationIscoRef, make_engine


def source_fields(source: DataSource | None) -> dict[str, str]:
    return {
        "source_name": source.name if source else "",
        "source_version": source.version if source else "",
        "source_url": source.source_url if source else "",
        "source_checksum": source.checksum if source else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/processed/finaira_generalization.db"))
    parser.add_argument("--output", type=Path, default=Path("reports/job_title_database"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with Session(make_engine(args.db)) as session:
        sources = {row.source_id: row for row in session.scalars(select(DataSource)).all()}
        groups = {row.isco_code: row for row in session.scalars(select(IscoGroup)).all()}
        refs = {row.occupation_id: row for row in session.scalars(select(OccupationIscoRef)).all()}
        occupations = list(session.scalars(select(Occupation).order_by(Occupation.isco_code, Occupation.occupation_id)).all())
        aliases = list(session.scalars(select(OccupationAlias).order_by(OccupationAlias.language, OccupationAlias.alias_text, OccupationAlias.alias_id)).all())

    taxonomy_fields = ["canonical_entity_type", "occupation_id", "label_en", "label_ar", "isco_code", "isco_label_en", "isco_label_ar", "isco_label_status", "occupation_review_status", "alias_count", "ar_alias_count", "en_alias_count", "source_name", "source_version", "source_url", "source_checksum"]
    aliases_by_occupation: dict[str, list[OccupationAlias]] = {}
    for alias in aliases:
        aliases_by_occupation.setdefault(alias.occupation_id, []).append(alias)
    taxonomy_rows = []
    for occupation in occupations:
        group = groups.get(occupation.isco_code or "")
        ref = refs.get(occupation.occupation_id)
        taxonomy_source = sources.get(ref.source_id) if ref and ref.source_id else sources.get(occupation.source_id)
        occupation_aliases = aliases_by_occupation.get(occupation.occupation_id, [])
        taxonomy_rows.append({
            "canonical_entity_type": "JOB_TITLE",
            "occupation_id": occupation.occupation_id,
            "label_en": occupation.label_en or "",
            "label_ar": occupation.label_ar or "",
            "isco_code": occupation.isco_code or "",
            "isco_label_en": group.label_en if group else "",
            "isco_label_ar": group.label_ar if group else "",
            "isco_label_status": group.arabic_label_status if group else "",
            "occupation_review_status": occupation.review_status,
            "alias_count": len(occupation_aliases),
            "ar_alias_count": sum(alias.language == "ar" for alias in occupation_aliases),
            "en_alias_count": sum(alias.language == "en" for alias in occupation_aliases),
            **source_fields(taxonomy_source),
        })

    alias_fields = ["canonical_entity_type", "alias_id", "alias_text", "normalized_alias", "language", "occupation_id", "label_en", "label_ar", "isco_code", "isco_label_en", "isco_label_ar", "alias_review_status", "occupation_review_status", "enabled_for_lookup", "source_name", "source_version", "source_url", "source_checksum"]
    alias_rows = []
    occupation_by_id = {row.occupation_id: row for row in occupations}
    for alias in aliases:
        occupation = occupation_by_id[alias.occupation_id]
        group = groups.get(occupation.isco_code or "")
        source = sources.get(alias.source_id)
        alias_rows.append({
            "canonical_entity_type": "JOB_TITLE",
            "alias_id": alias.alias_id,
            "alias_text": alias.alias_text,
            "normalized_alias": alias.normalized_alias,
            "language": alias.language,
            "occupation_id": alias.occupation_id,
            "label_en": occupation.label_en or "",
            "label_ar": occupation.label_ar or "",
            "isco_code": occupation.isco_code or "",
            "isco_label_en": group.label_en if group else "",
            "isco_label_ar": group.label_ar if group else "",
            "alias_review_status": alias.review_status,
            "occupation_review_status": occupation.review_status,
            "enabled_for_lookup": int(alias.review_status in {"OFFICIAL", "REVIEWED"} and occupation.review_status in {"OFFICIAL", "REVIEWED"}),
            **source_fields(source),
        })

    def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(args.output / "job_title_taxonomy.csv", taxonomy_fields, taxonomy_rows)
    write_csv(args.output / "job_title_aliases.csv", alias_fields, alias_rows)
    write_csv(args.output / "job_title_aliases_en.csv", alias_fields, [row for row in alias_rows if row["language"] == "en"])
    write_csv(args.output / "job_title_aliases_ar.csv", alias_fields, [row for row in alias_rows if row["language"] == "ar"])

    summary = [
        "# Production JOB_TITLE database inventory",
        "",
        f"Database: `{args.db}`",
        "",
        f"- Canonical occupations: **{len(taxonomy_rows):,}**",
        f"- Aliases: **{len(alias_rows):,}**",
        f"- English aliases: **{sum(row['language'] == 'en' for row in alias_rows):,}**",
        f"- Arabic aliases: **{sum(row['language'] == 'ar' for row in alias_rows):,}**",
        f"- Enabled aliases: **{sum(row['enabled_for_lookup'] == 1 for row in alias_rows):,}**",
        "",
        "`job_title_taxonomy.csv` is one row per canonical ESCO occupation. `job_title_aliases.csv` is the full lookup inventory, one row per alias, including language, ISCO code, review status, and source provenance. Language-specific copies are `job_title_aliases_en.csv` and `job_title_aliases_ar.csv`.",
        "",
        "The runtime accepts `OCCUPATION` as a compatibility input but exposes all records as canonical `JOB_TITLE`.",
    ]
    (args.output / "README.md").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()

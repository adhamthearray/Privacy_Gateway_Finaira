"""Export one deterministic bilingual test row per canonical bank."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/processed/finaira_generalization.db"
DEFAULT_OUTPUT = ROOT / "reports/bank_official_names_en_ar.csv"


def export_bank_names(db_path: Path, output_path: Path) -> int:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT bank_id, name_en, name_ar, finance_model,
                   finance_model_label_en, finance_model_label_ar,
                   evidence_status, source_id
            FROM banks
            ORDER BY bank_id
            """
        ).fetchall()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "bank_id",
                "official_name_en",
                "official_name_ar",
                "finance_model",
                "finance_model_label_en",
                "finance_model_label_ar",
                "evidence_status",
                "source_id",
            ]
        )
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(f"exported={export_bank_names(args.db, args.output)} output={args.output}")


if __name__ == "__main__":
    main()

"""Export exact bank-alias collisions for evidence-based research."""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/processed/finaira_generalization.db"
OUT = ROOT / "reports/gcc_bank_audit/bank_alias_collision_research_queue.csv"


def export(db_path: Path = DB, output_path: Path = OUT) -> dict:
    connection = sqlite3.connect(db_path)
    rows = connection.execute(
        """
        SELECT a.normalized_alias, a.alias_text, a.language, a.bank_id,
               b.name_en, b.name_ar, b.finance_model,
               COALESCE(c.country_code, 'EG') AS country_code,
               COALESCE(c.country, 'Egypt') AS country,
               COALESCE(c.banking_model, b.finance_model) AS banking_model,
               COALESCE(c.entity_kind, 'LEGACY') AS entity_kind,
               COALESCE(c.operational_status, 'LEGACY') AS operational_status,
               COALESCE(c.license_status, 'LEGACY') AS license_status,
               COALESCE(c.review_action, '') AS review_action,
               a.review_status, a.enabled_for_lookup
        FROM bank_aliases a
        JOIN banks b ON b.bank_id = a.bank_id
        LEFT JOIN bank_audit_classifications c ON c.bank_id = a.bank_id
        WHERE a.enabled_for_lookup = 1
        ORDER BY a.language, a.normalized_alias, a.bank_id
        """
    ).fetchall()
    connection.close()

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row[0], row[2])].append(row)

    output_rows = []
    for (normalized_alias, language), members in grouped.items():
        bank_ids = sorted({row[3] for row in members})
        if len(bank_ids) < 2:
            continue
        models = sorted({row[9] for row in members})
        statuses = sorted({row[12] for row in members})
        kinds = sorted({row[10] for row in members})
        same_model = len(models) == 1
        if same_model and any(kind == "Foreign bank branch" for kind in kinds):
            collision_class = "SAME_MODEL_BRANCH_FAMILY_RESEARCH"
            question = "Verify parent identity, legal branch relationship, and whether this alias can resolve to a grouped family without merging legal records."
        elif same_model:
            collision_class = "SAME_MODEL_COLLISION_RESEARCH"
            question = "Verify whether these are the same institution family or unrelated entities sharing an alias; preserve separate IDs until evidenced."
        else:
            collision_class = "MODEL_OR_STATUS_CONFLICT_RESEARCH"
            question = "Determine whether these are distinct entities, a parent/branch family, a successor, or a historical alias; do not group until model and status are reconciled."
        member_payload = []
        seen_member_ids = set()
        for row in members:
            if row[3] in seen_member_ids:
                continue
            seen_member_ids.add(row[3])
            member_payload.append({
                "bank_id": row[3],
                "name_en": row[4],
                "name_ar": row[5],
                "finance_model": row[6],
                "country_code": row[7],
                "country": row[8],
                "banking_model": row[9],
                "entity_kind": row[10],
                "operational_status": row[11],
                "license_status": row[12],
                "review_action": row[13],
                "review_status": row[14],
                "enabled_for_lookup": bool(row[15]),
            })
        output_rows.append({
            "alias_text": members[0][1],
            "normalized_alias": normalized_alias,
            "language": language,
            "collision_class": collision_class,
            "member_count": len(bank_ids),
            "bank_ids": "|".join(bank_ids),
            "banking_models": "|".join(models),
            "license_statuses": "|".join(statuses),
            "research_question": question,
            "members_json": json.dumps(member_payload, ensure_ascii=False, sort_keys=True),
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        fields = list(output_rows[0]) if output_rows else []
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    counts = defaultdict(int)
    for row in output_rows:
        counts[row["collision_class"]] += 1
    return {"collision_groups": len(output_rows), "classes": dict(counts), "output": str(output_path)}


if __name__ == "__main__":
    print(json.dumps(export(), ensure_ascii=False, indent=2, sort_keys=True))

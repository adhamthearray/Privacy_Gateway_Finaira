from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from common import DATA, ENTITY_TYPES, stable_id, write_jsonl


KEYWORDS = {
    "CORPORATION": ["company", "corporation", "employer", "شركة"],
    "BANK": ["bank", "financial institution", "بنك", "مصرف"],
    "GOVERNMENT_ENTITY": ["government", "regulator", "authority", "وزارة", "هيئة"],
    "DATE": ["date", "when", "deadline", "تاريخ", "موعد", "إمتى"],
    "OCCUPATION": ["occupation", "profession", "مهنة", "مجال"],
    "JOB_TITLE": ["job title", "position", "rank", "مسمى", "منصب"],
    "NATIONALITY": ["nationality", "citizenship", "جنسية"],
    "AGE": ["age", "years old", "عمر", "سن"],
    "MONETARY_AMOUNT": ["amount", "salary", "balance", "loan value", "مبلغ", "راتب", "رصيد"],
    "COUNTRY": ["country", "jurisdiction", "residence", "بلد", "دولة", "إقامة"],
}


def read_input(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else [value]
    return [{"user_prompt": line.strip()} for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prompt_from(row: dict) -> str:
    for key in ["user_prompt", "prompt", "instruction", "task", "text"]:
        if row.get(key):
            return str(row[key]).strip()
    return ""


def detect_language(prompt: str) -> tuple[str, str]:
    has_ar = bool(re.search(r"[\u0600-\u06ff]", prompt))
    has_en = bool(re.search(r"[A-Za-z]", prompt))
    if has_ar and has_en:
        return "Mixed Arabic-English", "ar_en_mixed"
    if has_ar:
        return "Arabic", "ar_unknown_pending_review"
    return "English", "en"


def suggest(prompt: str, entity: str) -> tuple[str, str]:
    text = prompt.casefold()
    hits = [term for term in KEYWORDS[entity] if term.casefold() in text]
    if hits:
        return "RELEVANT", f"Lexical importer suggestion triggered by {hits[0]!r}; human semantic review required."
    return "IRRELEVANT", "No lexical trigger found; this is only an importer suggestion and requires human review."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=DATA / "pending_review" / "imported_entity_decisions.jsonl")
    args = parser.parse_args()
    records = []
    for source_index, source in enumerate(read_input(args.input), 1):
        prompt = prompt_from(source)
        if not prompt:
            continue
        language, code = detect_language(prompt)
        prompt_id = stable_id("IMPORTED_PROMPT", str(args.input.resolve()), str(source_index), prompt)
        for entity in ENTITY_TYPES:
            label, reason = suggest(prompt, entity)
            records.append(
                {
                    "sample_id": stable_id("IMPORTED_SAMPLE", prompt_id, entity),
                    "prompt_id": prompt_id,
                    "user_prompt": prompt,
                    "task_requirements": str(source.get("task_requirements", "")),
                    "target_entity_type": entity,
                    "proposed_label": label,
                    "approved_gold_label": None,
                    "proposed_reason": reason,
                    "approved_reason": None,
                    "language": language,
                    "language_code": code,
                    "source_provenance": f"imported from {args.input.resolve()}",
                    "annotation_status": "PENDING_REVIEW",
                    "ambiguity_status": "NOT_FLAGGED",
                    "reviewer_id": None,
                    "reviewer_notes": None,
                }
            )
    write_jsonl(args.output, records)
    print(f"Imported {len(records) // 10} prompts as {len(records)} pending-review decisions")


if __name__ == "__main__":
    main()


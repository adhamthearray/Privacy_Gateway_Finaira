from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"

ENTITY_TYPES = [
    "CORPORATION",
    "BANK",
    "GOVERNMENT_ENTITY",
    "DATE",
    "OCCUPATION",
    "JOB_TITLE",
    "NATIONALITY",
    "AGE",
    "MONETARY_AMOUNT",
    "COUNTRY",
]
LABELS = ["RELEVANT", "SEMI_RELEVANT", "IRRELEVANT"]
LANGUAGES = ["en", "ar_msa", "ar_egy", "ar_en_mixed"]

QUESTION = {
    "entity_type_relevance": {
        "type": "choice",
        "instructions": (
            "For the user's requested task, how relevant is information belonging to the target "
            "entity type? Evaluate the information type, not a particular value or document occurrence."
        ),
        "criteria": {
            "IRRELEVANT": "Contributes nothing meaningfully useful or is explicitly excluded.",
            "SEMI_RELEVANT": "Adds meaningful optional context, but is not required to complete the task correctly.",
            "RELEVANT": "The task explicitly asks for or materially requires this information type.",
        },
    }
}

ENTITY_DESCRIPTIONS = {
    "CORPORATION": "A company, incorporated business, or other commercial organization.",
    "BANK": "A bank or regulated financial institution as an organization.",
    "GOVERNMENT_ENTITY": "A ministry, regulator, public authority, or government agency.",
    "DATE": "A calendar date, deadline, period boundary, or event time.",
    "OCCUPATION": "A broad profession or field of work.",
    "JOB_TITLE": "A specific position or rank held by a person.",
    "NATIONALITY": "A person's nationality or citizenship affiliation.",
    "AGE": "A person's age or age-related eligibility information.",
    "MONETARY_AMOUNT": "A quantity of money such as salary, balance, loan amount, or installment.",
    "COUNTRY": "A country or jurisdiction, including residence, incorporation, or transaction location.",
}


def ensure_dirs() -> None:
    for path in [
        DATA / "task_specs",
        DATA / "seeds",
        DATA / "generated",
        DATA / "pending_review",
        DATA / "approved",
        DATA / "rejected",
        REPORTS,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_prompt(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def laya_state(record: dict[str, Any]) -> str:
    # Official Laya hard-label JSONL examples use a textual state. Keeping this
    # text deterministic also prevents research metadata from leaking to inputs.
    return "\n".join(
        [
            f"User task: {record['user_prompt']}",
            f"Task requirements: {record['task_requirements'] or 'No additional rules supplied.'}",
            f"Target entity type: {record['target_entity_type']}",
            f"Entity description: {ENTITY_DESCRIPTIONS[record['target_entity_type']]}",
        ]
    )


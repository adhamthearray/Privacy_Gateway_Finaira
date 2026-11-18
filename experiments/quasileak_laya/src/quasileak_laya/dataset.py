"""Official QuasiLeak-Bench loading, split checks, and audit helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


ATTRIBUTES = ("age", "gender", "nationality", "education", "occupation", "income", "relationship", "health")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows_for_split(rows: Iterable[dict], manifest: dict, split: str) -> list[dict]:
    ids = set(manifest["membership"][split])
    return [row for row in rows if row["sample_id"] in ids]


def validate_rows(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    errors: list[str] = []
    sample_ids = {r.get("sample_id") for r in rows}
    for row in rows:
        if set(row.get("profile", {})) - set(ATTRIBUTES) - {"profile_id"}:
            errors.append(f"{row.get('sample_id')}: unexpected profile fields")
        if set(sum((row.get("policy", {}).get(k, []) for k in ("hide", "keep", "neutral")), [])) != set(ATTRIBUTES):
            errors.append(f"{row.get('sample_id')}: policy is not a complete partition")
        document = row.get("document", "")
        spans = {s["span_id"]: s for s in row.get("gold", {}).get("spans", [])}
        for span in spans.values():
            if document[span["start"] : span["end"]] != span["text"]:
                errors.append(f"{row.get('sample_id')}: offset mismatch {span.get('span_id')}")
        for group in row.get("gold", {}).get("groups", []):
            if group["attribute"] not in ATTRIBUTES:
                errors.append(f"{row.get('sample_id')}: unknown attribute {group['attribute']}")
            if not 2 <= len(group["cue_ids"]) <= 4:
                errors.append(f"{row.get('sample_id')}: invalid group arity")
            if group["attribute"] not in row["policy"]["hide"] + row["policy"]["keep"] + row["policy"]["neutral"]:
                errors.append(f"{row.get('sample_id')}: group attribute absent from policy")
    return {"rows": len(rows), "unique_sample_ids": len(sample_ids), "errors": errors, "valid": not errors}


def audit_dataset(dataset_path: str | Path, manifest_path: str | Path, metadata_path: str | Path) -> dict:
    rows = load_rows(dataset_path)
    manifest = load_manifest(manifest_path)
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    row_check = validate_rows(rows)
    split_counts = {k: len(v) for k, v in manifest["membership"].items() if isinstance(v, list)}
    split_profiles = {k: set(v) for k, v in manifest["profiles"].items() if isinstance(v, list)}
    disjoint = all(not (split_profiles[a] & split_profiles[b]) for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")))
    by_id = {r["sample_id"]: r for r in rows}
    missing = {k: [sid for sid in ids if sid not in by_id] for k, ids in manifest["membership"].items() if isinstance(ids, list)}
    result = {
        "dataset_path": str(Path(dataset_path)),
        "dataset_sha256": sha256_file(dataset_path),
        "metadata_expected_sha256": metadata["files"]["sha256"],
        "metadata_expected_bytes": metadata["files"]["bytes"],
        "row_check": row_check,
        "split_counts": split_counts,
        "profile_counts": {k: len(v) for k, v in split_profiles.items()},
        "profile_disjoint_train_validation_test": disjoint,
        "missing_membership_ids": {k: len(v) for k, v in missing.items()},
        "metadata": metadata,
    }
    result["valid"] = bool(row_check["valid"] and disjoint and not any(missing.values()) and result["dataset_sha256"] == metadata["files"]["sha256"])
    return result

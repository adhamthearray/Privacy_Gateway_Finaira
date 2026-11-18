"""Audit the released QuasiLeak-Bench corpus and split integrity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quasileak_laya.dataset import audit_dataset  # noqa: E402


def markdown(report: dict) -> str:
    meta = report["metadata"]["dataset"]
    split = report["split_counts"]
    profiles = report["profile_counts"]
    status = "PASS" if report["valid"] else "FAIL"
    lines = [
        "# QuasiLeak-Bench dataset audit",
        "",
        f"Status: **{status}**",
        "",
        "This audit uses the released full corpus and the repository's released profile-disjoint manifest. It does not create a new split.",
        "",
        "## Dataset identity",
        "",
        f"- Documents: {meta['documents']}",
        f"- Profiles: {meta['unique_profiles']}",
        f"- Contexts: {meta['unique_contexts']}",
        f"- Groups: {meta['groups']}",
        f"- Cues/spans: {meta['spans']}",
        f"- Distractors: {meta['distractors']}",
        f"- SHA-256 observed: `{report['dataset_sha256']}`",
        f"- SHA-256 expected by metadata: `{report['metadata_expected_sha256']}`",
        "",
        "## Released membership",
        "",
        "| view | rows | profiles |",
        "|---|---:|---:|",
    ]
    for view in ("train", "validation", "test", "subset_non_revealing", "policy_shift", "sft_policy_shift"):
        if view in split:
            lines.append(f"| {view} | {split[view]} | {profiles.get(view, 'paired/see manifest')} |")
    lines += [
        "",
        f"- Train/validation/test profile-disjoint: **{report['profile_disjoint_train_validation_test']}**",
        f"- Missing membership IDs: `{report['missing_membership_ids']}`",
        "",
        "## Validation checks",
        "",
        f"- Row and offset checks: **{report['row_check']['valid']}** ({len(report['row_check']['errors'])} errors)",
        "- Offsets are interpreted as half-open Unicode code-point offsets, as required by the release.",
        "- The 1,000-row convenience subset is not used as QLB-Test.",
        "",
        "## License",
        "",
        "The benchmark data are CC BY-NC-SA 4.0. The vendored source code is MIT. Keep the data separate from model redistribution and retain attribution.",
        "",
    ]
    if report["row_check"]["errors"]:
        lines += ["## Errors", ""] + [f"- {e}" for e in report["row_check"]["errors"][:50]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--json-out", type=Path, required=True)
    ap.add_argument("--markdown-out", type=Path, required=True)
    args = ap.parse_args()
    report = audit_dataset(args.dataset, args.manifest, args.metadata)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("valid", "dataset_sha256", "split_counts", "profile_counts", "profile_disjoint_train_validation_test")}, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

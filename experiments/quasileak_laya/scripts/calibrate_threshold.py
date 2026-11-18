"""Select an answer-confidence threshold on validation only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "QuasiLeak-Bench"
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(VENDOR))
from quasileak_laya.adapter import prediction_from_answers  # noqa: E402
from quasileak_laya.candidates import CandidateGroup, CandidateSpan  # noqa: E402
from quasileak_laya.dataset import load_manifest, load_rows, rows_for_split  # noqa: E402
from scorer.score import score  # noqa: E402


def _group(item: dict) -> CandidateGroup:
    return CandidateGroup(item["group_id"], tuple(CandidateSpan(s["span_id"], s["text"], s["start"], s["end"]) for s in item["spans"]), item.get("source", "document_only"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = {r["sample_id"]: r for r in rows_for_split(load_rows(args.dataset), load_manifest(args.manifest), "validation")}
    raw = [json.loads(x) for x in args.raw.open(encoding="utf-8") if x.strip()]
    thresholds = [round(x / 100, 2) for x in range(0, 101, 5)]
    records = []
    for threshold in thresholds:
        predictions = []
        for item in raw:
            row = rows.get(item["sample_id"])
            if not row: continue
            predictions.append(prediction_from_answers(row, [_group(g) for g in item["candidate_groups"]], item.get("answers", {}), threshold=threshold))
        pred_path = args.out.with_suffix(f".{threshold:.2f}.jsonl")
        pred_path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in predictions) + "\n", encoding="utf-8")
        metrics = score(pred_path, args.dataset, split="validation")
        records.append({"threshold": threshold, **metrics})
    # Prefer P-GF1, then lower FAR, then higher precision.  This is frozen
    # before the held-out test run.
    best = max(records, key=lambda r: (r.get("P-GF1", -1), -(r.get("FAR") if r.get("FAR") is not None else 1e9), r.get("P-GP", -1))) if records else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"split": "validation", "records": records, "recommended": best}, indent=2), encoding="utf-8")
    print(json.dumps({"recommended": best}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

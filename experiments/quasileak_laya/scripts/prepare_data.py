"""Build Laya typed-decision rows from official QuasiLeak data.

Training rows contain supervised gold positives. Validation and test rows use
only text-derived proposals, preserving the detector's real proposal problem.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quasileak_laya.candidates import mine_groups, mine_spans, training_groups  # noqa: E402
from quasileak_laya.dataset import load_manifest, load_rows, rows_for_split  # noqa: E402
from quasileak_laya.adapter import build_request  # noqa: E402


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _proposal_stats(row: dict, groups) -> dict:
    gold_spans = {(s["start"], s["end"]) for s in row["gold"]["spans"]}
    gold_groups = {
        tuple(sorted((next(s for s in row["gold"]["spans"] if s["span_id"] == cue)["start"], next(s for s in row["gold"]["spans"] if s["span_id"] == cue)["end"]) for cue in g["cue_ids"]))
        for g in row["gold"]["groups"] if g["attribute"] in row["policy"]["hide"]
    }
    proposed_spans = {(s.start, s.end) for g in groups for s in g.spans}
    proposed_groups = {tuple(sorted((s.start, s.end) for s in g.spans)) for g in groups}
    return {
        "gold_hidden_groups": len(gold_groups),
        "hidden_groups_recalled": len(gold_groups & proposed_groups),
        "group_recall": (len(gold_groups & proposed_groups) / len(gold_groups)) if gold_groups else 1.0,
        "gold_spans": len(gold_spans),
        "spans_recalled": len(gold_spans & proposed_spans),
        "span_recall": (len(gold_spans & proposed_spans) / len(gold_spans)) if gold_spans else 1.0,
        "candidate_groups": len(groups),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--split", choices=("train", "validation", "test"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-groups", type=int, default=512)
    ap.add_argument("--training-positives", action="store_true")
    args = ap.parse_args()

    rows = rows_for_split(load_rows(args.dataset), load_manifest(args.manifest), args.split)
    out_rows = []
    stats = []
    for row in rows:
        text_only_groups = mine_groups(mine_spans(row["document"]), max_groups=args.max_groups)
        if args.training_positives:
            groups = training_groups(row, max_groups=args.max_groups)
        else:
            groups = text_only_groups
        out_rows.append(build_request(row, groups, training=args.training_positives))
        stat = _proposal_stats(row, groups)
        if args.training_positives:
            text_stat = _proposal_stats(row, text_only_groups)
            stat["text_only_span_recall"] = text_stat["span_recall"]
            stat["text_only_group_recall"] = text_stat["group_recall"]
            stat["text_only_hidden_groups_recalled"] = text_stat["hidden_groups_recalled"]
        stats.append(stat)
    _write_jsonl(args.out, out_rows)
    manifest = {
        "dataset_split": args.split,
        "training_positives": args.training_positives,
        "rows": len(rows),
        "candidate_groups_total": sum(s["candidate_groups"] for s in stats),
        "avg_candidate_groups": sum(s["candidate_groups"] for s in stats) / len(stats) if stats else 0.0,
        "span_recall_mean": sum(s["span_recall"] for s in stats) / len(stats) if stats else 0.0,
        "group_recall_mean": sum(s["group_recall"] for s in stats) / len(stats) if stats else 0.0,
        "cases_with_any_hidden_group_recalled": sum(s["hidden_groups_recalled"] > 0 for s in stats),
        "text_only_span_recall_mean": sum(s.get("text_only_span_recall", s["span_recall"]) for s in stats) / len(stats) if stats else 0.0,
        "text_only_group_recall_mean": sum(s.get("text_only_group_recall", s["group_recall"]) for s in stats) / len(stats) if stats else 0.0,
        "text_only_cases_with_any_hidden_group_recalled": sum(s.get("text_only_hidden_groups_recalled", s["hidden_groups_recalled"]) > 0 for s in stats),
        "per_case": stats,
    }
    manifest_path = args.out.with_suffix(args.out.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in manifest if k != "per_case"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

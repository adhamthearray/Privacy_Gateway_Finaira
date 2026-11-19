"""Run original or fine-tuned Laya on an official split.

The script is resumable.  It stores the raw typed answers and the exact
candidate groups used for each document before producing official predictions.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "QuasiLeak-Bench"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor" / "laya"))

from quasileak_laya.adapter import build_request, prediction_from_answers  # noqa: E402
from quasileak_laya.candidates import CandidateGroup, mine_groups, mine_spans, oracle_groups  # noqa: E402
from quasileak_laya.dataset import load_manifest, load_rows, rows_for_split  # noqa: E402


def _groups(row: dict, max_groups: int, mode: str) -> list[CandidateGroup]:
    if mode == "oracle":
        return oracle_groups(row)
    return mine_groups(mine_spans(row["document"]), max_groups=max_groups)


def _load_completed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                done.add(json.loads(line)["sample_id"])
    return done


def _load_agent(model: str, device: str):
    try:
        import laya
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("Laya is not installed; install vendor/laya or run the Kaggle workflow") from exc
    return laya.load(model, device=device, backend="eager")


def _merge_usage(total: dict, current: dict) -> dict:
    """Aggregate usage from multiple bounded Laya calls."""
    for key, value in (current or {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total[key] = total.get(key, 0) + value
        elif key not in total:
            total[key] = value
    return total


def _write_score(predictions: Path, dataset: Path, split: str, out: Path) -> None:
    import subprocess
    cmd = [sys.executable, str(VENDOR / "scorer" / "score.py"), "--predictions", str(predictions), "--dataset", str(dataset), "--split", split]
    proc = subprocess.run(cmd, cwd=VENDOR, text=True, capture_output=True, check=False)
    out.write_text(proc.stdout or proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"official scorer failed ({proc.returncode}): {proc.stderr[-1000:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--split", choices=("validation", "test"), required=True)
    ap.add_argument("--model", required=True, help="local Laya checkpoint or Hugging Face id")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--max-groups", type=int, default=256)
    ap.add_argument("--candidate-mode", choices=("mined", "oracle"), default="mined")
    ap.add_argument("--chunk-size", type=int, default=64)
    ap.add_argument("--groups-per-call", type=int, default=8, help="Maximum candidate groups sent to one Laya call; keeps GPU memory bounded")
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--progress-every", type=int, default=1, help="Print progress after this many completed documents")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.groups_per_call < 1:
        ap.error("--groups-per-call must be at least 1")
    if args.chunk_size < 1:
        ap.error("--chunk-size must be at least 1")
    if args.progress_every < 1:
        ap.error("--progress-every must be at least 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import torch
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        cuda_available = False
    if args.device in ("auto", "cuda") and not cuda_available:
        status = {"status": "PENDING_GPU", "reason": "Laya evaluation was not started because the requested auto/cuda lane has no CUDA device.", "model": args.model, "split": args.split}
        (args.output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2
    raw_path = args.output_dir / "raw_responses.jsonl"
    prediction_path = args.output_dir / "predictions.jsonl"
    latency_path = args.output_dir / "per_request_latency.csv"
    rows = rows_for_split(load_rows(args.dataset), load_manifest(args.manifest), args.split)
    if args.limit:
        rows = rows[: args.limit]

    completed = _load_completed(raw_path) if args.resume else set()
    initial_completed = sum(row["sample_id"] in completed for row in rows)
    newly_completed = 0
    progress_started = time.perf_counter()
    print(
        f"Starting {args.split}: {len(rows)} documents; "
        f"already complete: {initial_completed}; "
        f"max groups: {args.max_groups}; groups/call: {args.groups_per_call}; "
        f"window batch: {args.chunk_size}",
        flush=True,
    )
    mode = "w" if not args.resume else "a"
    try:
        agent = _load_agent(args.model, args.device)
    except Exception as exc:
        status = {"status": "BLOCKED", "reason": str(exc), "model": args.model, "split": args.split}
        (args.output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2

    latency_exists = latency_path.exists() and args.resume
    with raw_path.open(mode, encoding="utf-8", newline="\n") as raw, latency_path.open("a" if latency_exists else "w", encoding="utf-8", newline="") as lat:
        writer = csv.DictWriter(lat, fieldnames=["sample_id", "model", "candidate_groups", "question_count", "input_tokens", "windows", "model_ms", "end_to_end_ms", "parse_ms", "success", "error_type", "device"])
        if not latency_exists:
            writer.writeheader()
        for row in rows:
            if row["sample_id"] in completed:
                continue
            started = time.perf_counter_ns()
            groups = _groups(row, args.max_groups, args.candidate_mode)
            answers = {}
            usage = {}
            error = None
            model_start = time.perf_counter_ns()
            for offset in range(0, len(groups), args.groups_per_call):
                group_chunk = groups[offset : offset + args.groups_per_call]
                request = build_request(row, group_chunk)
                try:
                    result = agent.predict_long(request["state"], request["questions"], batch_size=args.chunk_size)
                    usage = _merge_usage(usage, result.get("usage", {}))
                    chunk_answers = result.get("answers", {})
                    for local_index in range(len(group_chunk)):
                        local_key = f"group_{local_index:05d}"
                        if local_key in chunk_answers:
                            answers[f"group_{offset + local_index:05d}"] = chunk_answers[local_key]
                except Exception as exc:  # keep failed requests for audit/resume
                    error = f"{type(exc).__name__}: {exc}"
                    break
            model_ms = (time.perf_counter_ns() - model_start) / 1_000_000
            parse_start = time.perf_counter_ns()
            prediction = prediction_from_answers(row, groups, answers, threshold=args.threshold) if not error else {"sample_id": row["sample_id"], "evidence": []}
            parse_ms = (time.perf_counter_ns() - parse_start) / 1_000_000
            end_to_end = (time.perf_counter_ns() - started) / 1_000_000
            raw_row = {
                "sample_id": row["sample_id"], "model": args.model, "split": args.split,
                "candidate_groups": [g.as_dict() for g in groups], "answers": answers,
                "result_usage": usage, "prediction": prediction,
                "success": not bool(error), "error": error,
            }
            raw.write(json.dumps(raw_row, ensure_ascii=False, separators=(",", ":")) + "\n"); raw.flush(); os.fsync(raw.fileno())
            writer.writerow({
                "sample_id": row["sample_id"], "model": args.model, "candidate_groups": len(groups),
                "question_count": len(groups), "input_tokens": usage.get("input_tokens"),
                "windows": usage.get("windows"), "model_ms": round(model_ms, 4),
                "end_to_end_ms": round(end_to_end, 4), "parse_ms": round(parse_ms, 4),
                "success": not bool(error), "error_type": type(error).__name__ if error else "", "device": args.device,
            }); lat.flush(); os.fsync(lat.fileno())
            newly_completed += 1
            if newly_completed % args.progress_every == 0 or initial_completed + newly_completed == len(rows):
                done = initial_completed + newly_completed
                elapsed = time.perf_counter() - progress_started
                rate = newly_completed / elapsed if elapsed > 0 else 0.0
                remaining = (len(rows) - done) / rate if rate > 0 else None
                eta = f", ETA {remaining / 60:.1f} min" if remaining is not None else ""
                print(
                    f"[{done}/{len(rows)}] {args.split} progress; "
                    f"last={row['sample_id']}; model={model_ms:.1f} ms; "
                    f"rate={rate:.2f} docs/s{eta}",
                    flush=True,
                )

    with raw_path.open(encoding="utf-8") as fh, prediction_path.open("w", encoding="utf-8", newline="\n") as pred:
        for line in fh:
            item = json.loads(line)
            pred.write(json.dumps(item["prediction"], ensure_ascii=False, separators=(",", ":")) + "\n")
    _write_score(prediction_path, args.dataset, args.split, args.output_dir / "official_metrics.json")
    status = {"status": "COMPLETE", "model": args.model, "split": args.split, "rows": len(rows), "predictions": str(prediction_path), "threshold": args.threshold, "candidate_mode": args.candidate_mode, "diagnostic_only": args.candidate_mode == "oracle"}
    (args.output_dir / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

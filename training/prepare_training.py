from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def count_jsonl(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) if path.exists() else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print the verified Laya schema-validation command.")
    args = parser.parse_args()
    train = ROOT / "data" / "train.jsonl"
    validation = ROOT / "data" / "validation.jsonl"
    counts = {"train": count_jsonl(train), "validation": count_jsonl(validation)}
    command = [
        "laya-train", "--data", str(train), "--eval", str(validation),
        "--out", str(ROOT / "artifacts" / "laya_relevance"),
        "--base", "multilingual", "--loss", "soft-ce", "--shuffle-options",
        "--label-smoothing", "0.05", "--epochs", "3", "--micro-batch", "8",
        "--grad-accum", "8", "--encoder-lr", "2.5e-5", "--head-lr", "1e-4",
        "--seed", "20261126",
    ]
    if args.dry_run:
        command.append("--dry-run")
    print(json.dumps({"approved_counts": counts, "command": shlex.join(command)}, indent=2))
    if counts["train"] == 0 or counts["validation"] == 0:
        raise SystemExit("Refusing to train: approved train/validation exports are empty.")
    if not args.dry_run:
        print("Command prepared only. This script intentionally does not start expensive training.")


if __name__ == "__main__":
    main()


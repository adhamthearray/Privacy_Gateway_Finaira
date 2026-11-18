"""Run the released QuasiLeak LoRA recipe without changing its code."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "QuasiLeak-Bench"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--dev", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        import torch
        gpu = torch.cuda.is_available()
    except Exception:
        gpu = False
    if not gpu:
        status = {"status": "PENDING_GPU", "reason": "Qwen3.5-4B LoRA requires CUDA/BF16 for the released recipe; no CUDA device is available locally.", "model_id": args.model_id}
        (args.out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2
    cmd = [sys.executable, str(VENDOR / "training" / "train_lora.py"), "--model-id", args.model_id, "--train", str(args.train), "--dev", str(args.dev), "--out", str(args.out), "--epochs", str(args.epochs), "--seed", str(args.seed), "--batch", str(args.batch), "--grad-accum", str(args.grad_accum), "--max-len", str(args.max_len)]
    if args.merge:
        cmd.append("--merge")
    proc = subprocess.run(cmd, cwd=VENDOR, text=True, capture_output=False)
    status = {"status": "COMPLETE" if proc.returncode == 0 else "FAILED", "returncode": proc.returncode, "command": cmd}
    (args.out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

"""Fine-tune Laya with the official typed-decision training API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "laya"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--dev", type=Path, required=True)
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--micro-batch", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20261119)
    ap.add_argument("--loss", choices=("rlcd", "soft-ce"), default="rlcd")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    import torch
    if not args.dry_run and not torch.cuda.is_available() and args.device in ("auto", "cuda"):
        status = {"status": "PENDING_GPU", "reason": "Laya fine-tuning requires a CUDA-capable device for the planned run; this machine exposes CPU-only PyTorch.", "model_dir": str(args.model_dir)}
        (args.out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return 2

    from laya.train import TrainConfig, dry_run, finetune
    config = TrainConfig(epochs=args.epochs, micro_batch=args.micro_batch, grad_accum=args.grad_accum, seed=args.seed, loss=args.loss, eval_data=str(args.dev))
    if args.dry_run:
        result = dry_run(str(args.train), str(args.model_dir), config)
    else:
        result = finetune(str(args.train), str(args.model_dir), str(args.out), config, device=args.device)
    status = {"status": "COMPLETE", "config": config.__dict__, "result": result}
    (args.out / "status.json").write_text(json.dumps(status, indent=2, default=str), encoding="utf-8")
    print(json.dumps(status, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

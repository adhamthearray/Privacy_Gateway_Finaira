"""Download and record immutable model artifacts for a GPU run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", action="append", required=True)
    ap.add_argument("--out-root", type=Path, required=True)
    ap.add_argument("--revision")
    args = ap.parse_args()
    from huggingface_hub import snapshot_download

    args.out_root.mkdir(parents=True, exist_ok=True)
    records = []
    for model_id in args.model_id:
        name = model_id.replace("/", "__")
        destination = args.out_root / name
        path = snapshot_download(repo_id=model_id, revision=args.revision, local_dir=str(destination), local_dir_use_symlinks=False)
        records.append({"model_id": model_id, "revision": args.revision, "path": str(path)})
    (args.out_root / "download_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

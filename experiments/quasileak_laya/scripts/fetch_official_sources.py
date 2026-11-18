"""Fetch the pinned official sources and extract the released corpus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def clone(url: str, destination: Path, revision: str | None) -> str:
    if not (destination / ".git").exists():
        subprocess.check_call(["git", "clone", "--depth", "1", "--filter", "blob:none", url, str(destination)])
    if revision:
        subprocess.check_call(["git", "fetch", "--depth", "1", "origin", revision], cwd=destination)
        subprocess.check_call(["git", "checkout", revision], cwd=destination)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--quasileak-ref", default="75987cdf029fac5fecce160bea218b458ed46dbb")
    ap.add_argument("--laya-ref", default="d1282e791d71e92f24f816ff3836e4fd1c2ded4a")
    args = ap.parse_args()
    vendor = args.root / "vendor"; vendor.mkdir(parents=True, exist_ok=True)
    qlb = clone("https://github.com/Yufannnn/QuasiLeak-Bench.git", vendor / "QuasiLeak-Bench", args.quasileak_ref)
    laya = clone("https://github.com/NandhaKishorM/laya.git", vendor / "laya", args.laya_ref)
    archive = vendor / "QuasiLeak-Bench/data/quasileak_bench_data.zip"
    full = vendor / "QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl"
    if archive.exists() and not full.exists():
        subprocess.check_call([sys.executable, "-m", "zipfile", "-e", str(archive), str(archive.parent)])
    manifest = {"quasileak_repository": qlb, "laya_repository": laya, "dataset_archive": str(archive), "dataset_extracted": str(full)}
    (args.root / "results/source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

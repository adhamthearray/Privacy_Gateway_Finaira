"""Create a comparison table from actually executed result directories."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def _metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and "metrics" in value:
            return value["metrics"]
        return value
    except json.JSONDecodeError:
        return {"raw_metrics_file": str(path)}


def _latency(path: Path) -> dict:
    if not path.exists():
        return {}
    values = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                values.append(float(row["end_to_end_ms"]))
            except (KeyError, TypeError, ValueError):
                pass
    if not values:
        return {}
    values.sort()
    pct = lambda p: values[min(len(values) - 1, int(round((len(values) - 1) * p)))]
    return {"mean_latency_ms": statistics.mean(values), "p50_latency_ms": pct(.50), "p95_latency_ms": pct(.95), "p99_latency_ms": pct(.99), "n_latency": len(values)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    models = {"C0_BASE_LAYA": "laya_base", "C1_QUASILEAK_LAYA": "laya_finetuned", "C2_QWEN_STANDARD_REPRODUCED": "qwen_standard", "C3_QWEN_AUGMENTED_REPRODUCED": "qwen_augmented"}
    fields = ["model", "P-GF1", "P-GP", "P-GR", "E-GF1", "B-GF1", "FAR", "mean_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "status"]
    rows = []
    for model, dirname in models.items():
        directory = args.results_root / dirname
        status = json.loads((directory / "status.json").read_text(encoding="utf-8")) if (directory / "status.json").exists() else {"status": "NOT_RUN"}
        row = {"model": model, **{k: None for k in fields if k not in ("model", "status")}, "status": status.get("status")}
        row.update({k: v for k, v in _metrics(directory / "official_metrics.json").items() if k in fields})
        row.update({k: v for k, v in _latency(directory / "per_request_latency.csv").items() if k in fields})
        rows.append(row)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    (args.out.with_suffix(".json")).write_text(json.dumps({"models": rows}, indent=2), encoding="utf-8")
    print(json.dumps({"models": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

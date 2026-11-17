"""Run the deterministic V2 synthetic-size benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finaira.v2 import run_benchmarks


def main() -> None:
    rows = run_benchmarks()
    output_dir = ROOT / "reports" / "v2_optimizer"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "benchmark_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

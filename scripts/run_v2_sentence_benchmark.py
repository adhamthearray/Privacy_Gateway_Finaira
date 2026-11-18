"""Run the large exact/direct sentence benchmark."""

from __future__ import annotations

import json
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finaira.v2 import run_sentence_benchmark  # noqa: E402


def main() -> None:
    result = run_sentence_benchmark(count=100, max_utility_loss=1.0)
    output_dir = ROOT / "reports" / "v2_optimizer"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sentence_benchmark_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "sentence_benchmark_sentences.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "language", "task", "document", "entities_json"])
        writer.writeheader()
        for request in result["requests"]:
            writer.writerow({"case_id": request["case_id"], "language": request["metadata"]["language"], "task": request["task"], "document": request["document"], "entities_json": json.dumps(request["entities"], ensure_ascii=False)})
    print(json.dumps({"manifest": result["manifest"], "summary": result["summary"], "elapsed_ms": result["elapsed_ms"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

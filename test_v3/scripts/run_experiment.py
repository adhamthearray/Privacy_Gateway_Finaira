from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from test_v3.controller import run_case
from test_v3.detector import SyntheticRuleDetector
from test_v3.reporting import summarize, write_html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=ROOT / "cases" / "synthetic_cases.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-iterations", type=int, default=8)
    ap.add_argument("--max-detector-calls", type=int, default=40)
    args = ap.parse_args()
    cases = [json.loads(line) for line in args.cases.open(encoding="utf-8") if line.strip()]
    if args.limit:
        cases = cases[: args.limit]
    detector = SyntheticRuleDetector()
    results = []
    for index, case in enumerate(cases, 1):
        result = run_case(case, detector, max_iterations=args.max_iterations, max_detector_calls=args.max_detector_calls)
        results.append(result)
        print(f"[{index}/{len(cases)}] {case['case_id']} {result['status']} loss={result['normalized_loss']:.4f} calls={result['detector_calls']}", flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    summary = summarize(results)
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_html(results, summary, args.out / "report.html")
    failures = [result for result in results if result["status"].startswith("UNRESOLVED")]
    with (args.out / "failures.jsonl").open("w", encoding="utf-8") as handle:
        for result in failures:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

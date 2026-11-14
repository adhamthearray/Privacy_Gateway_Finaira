"""Benchmark JOB_TITLE coverage against independent occupational title sources.

This report is deliberately separate from the Finaira NER audit. It measures
recognition of external title inventories and never imports those titles into
the production database.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit_ner_generalization_coverage import CoverageIndex


@dataclass(frozen=True)
class BenchmarkTitle:
    source: str
    source_kind: str
    language: str
    value: str
    external_code: str = ""
    external_title: str = ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _field(row: dict[str, str], *names: str) -> str:
    lowered = {str(key).strip().casefold(): (value or "").strip() for key, value in row.items()}
    for name in names:
        if lowered.get(name.casefold()):
            return lowered[name.casefold()]
    return ""


def load_onet(path: Path, kind: str) -> list[BenchmarkTitle]:
    rows: list[BenchmarkTitle] = []
    value_field = "Job Title" if kind == "job_titles" else "Reported Job Title"
    source_kind = "ONET_JOB_TITLE" if kind == "job_titles" else "ONET_REPORTED_TITLE"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            value = _field(row, value_field)
            if value:
                rows.append(BenchmarkTitle("O*NET 31.0", source_kind, "en", value, _field(row, "O*NET-SOC Code"), _field(row, "Title")))
    return rows


def load_generic_csv(path: Path, source: str, language: str, source_kind: str) -> list[BenchmarkTitle]:
    rows: list[BenchmarkTitle] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            value = _field(row, "value", "title", "job title", "occupation", "occupation title", "name", "arabic", "العنوان", "المهنة", "المسمى الوظيفي")
            if value:
                rows.append(BenchmarkTitle(source, source_kind, language, value, _field(row, "code", "occupation code", "source code"), _field(row, "english", "English", "title")))
    return rows


def load_bls(path: Path) -> list[BenchmarkTitle]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("BLS XLSX support requires pandas/openpyxl") from exc
    frame = pd.read_excel(path, dtype=str)
    rows: list[BenchmarkTitle] = []
    columns = {str(column).strip().casefold(): column for column in frame.columns}
    title_column = next((column for key, column in columns.items() if "direct match title" in key), None)
    code_column = next((column for key, column in columns.items() if "soc code" in key), None)
    occupation_column = next((column for key, column in columns.items() if "soc title" in key and "direct" not in key), None)
    if title_column is None:
        raise ValueError(f"Could not find BLS direct-match title column in {path}")
    for _, row in frame.iterrows():
        value = str(row.get(title_column, "") or "").strip()
        if value and value.casefold() != "nan":
            rows.append(BenchmarkTitle("BLS SOC 2018", "BLS_DIRECT_MATCH_TITLE", "en", value, str(row.get(code_column, "") or "").strip(), str(row.get(occupation_column, "") or "").strip()))
    return rows


def classify(result: dict) -> str:
    if result["resolution_status"] == "VERIFIED":
        return "LONGEST_PHRASE_CANDIDATE" if result["reason_code"] == "LONGEST_PHRASE_MATCH" else "VERIFIED_EXACT_OR_NORMALIZED"
    if result["resolution_status"] == "AMBIGUOUS":
        return "AMBIGUOUS"
    if result["resolution_status"] == "REVIEW_ONLY":
        return "REVIEW_ONLY"
    if result["resolution_status"] == "NOT_FOUND" and result["has_non_suppression_candidate"]:
        return "GENERIC_FALLBACK_ONLY"
    return "UNRESOLVED"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/processed/finaira_generalization.db"))
    parser.add_argument("--onet-job-titles", type=Path)
    parser.add_argument("--onet-reported-titles", type=Path)
    parser.add_argument("--bls-xlsx", type=Path)
    parser.add_argument("--capmas-csv", type=Path)
    parser.add_argument("--egypt-outlook-csv", type=Path)
    parser.add_argument("--asco-csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/job_occupation_benchmark"))
    args = parser.parse_args()

    titles: list[BenchmarkTitle] = []
    source_files: dict[str, dict] = {}
    optional_inputs = [
        ("onet_job_titles", args.onet_job_titles, lambda path: load_onet(path, "job_titles")),
        ("onet_reported_titles", args.onet_reported_titles, lambda path: load_onet(path, "reported_titles")),
        ("bls_direct_match_titles", args.bls_xlsx, load_bls),
        ("capmas_titles", args.capmas_csv, lambda path: load_generic_csv(path, "CAPMAS Unified Occupational Classification", "ar", "CAPMAS_ARABIC_TITLE")),
        ("egypt_occupational_outlook", args.egypt_outlook_csv, lambda path: load_generic_csv(path, "Egypt Occupational Outlook", "ar", "EGYPT_OUTLOOK_ARABIC_TITLE")),
        ("asco_titles", args.asco_csv, lambda path: load_generic_csv(path, "ASCO 2008", "ar", "ASCO_ARABIC_TITLE")),
    ]
    for key, path, loader in optional_inputs:
        if path is None:
            source_files[key] = {"status": "NOT_PROVIDED"}
            continue
        if not path.exists():
            source_files[key] = {"status": "MISSING", "path": str(path)}
            continue
        loaded = loader(path)
        titles.extend(loaded)
        source_files[key] = {"status": "LOADED", "path": str(path), "sha256": _sha256(path), "rows": len(loaded)}

    index = CoverageIndex(args.db)
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for title in titles:
        key = (title.source_kind, title.language, title.value)
        if key in seen:
            continue
        seen.add(key)
        result = index.lookup("JOB_TITLE", title.value)
        rows.append({
            "source": title.source,
            "source_kind": title.source_kind,
            "language": title.language,
            "value": title.value,
            "external_code": title.external_code,
            "external_title": title.external_title,
            "coverage_category": classify(result),
            **result,
        })
    index.close()

    args.output.mkdir(parents=True, exist_ok=True)
    fields = ["source", "source_kind", "language", "value", "external_code", "external_title", "coverage_category", "resolution_status", "reason_code", "lookup_language", "canonical_id", "candidate_levels", "has_exact_candidate", "has_non_suppression_candidate", "verification_statuses"]
    with (args.output / "benchmark_values.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["source_kind"], row["language"], row["value"])))

    summary: list[dict] = []
    for source_kind in sorted({row["source_kind"] for row in rows}):
        for language in sorted({row["language"] for row in rows if row["source_kind"] == source_kind}):
            subset = [row for row in rows if row["source_kind"] == source_kind and row["language"] == language]
            counts = Counter(row["coverage_category"] for row in subset)
            total = len(subset)
            exact = counts["VERIFIED_EXACT_OR_NORMALIZED"]
            phrase = counts["LONGEST_PHRASE_CANDIDATE"]
            summary.append({"source_kind": source_kind, "language": language, "unique_values": total, **{f"{category.lower()}_unique": counts[category] for category in ("VERIFIED_EXACT_OR_NORMALIZED", "LONGEST_PHRASE_CANDIDATE", "AMBIGUOUS", "REVIEW_ONLY", "GENERIC_FALLBACK_ONLY", "UNRESOLVED")}, "exact_pct": round(100 * exact / total, 2) if total else 0, "candidate_recall_pct": round(100 * (exact + phrase) / total, 2) if total else 0})
    with (args.output / "benchmark_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]) if summary else ["source_kind", "language", "unique_values"])
        writer.writeheader()
        writer.writerows(summary)

    missing = [row for row in rows if row["coverage_category"] not in {"VERIFIED_EXACT_OR_NORMALIZED", "LONGEST_PHRASE_CANDIDATE"}]
    with (args.output / "benchmark_missing_or_ambiguous.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(missing, key=lambda row: (row["source_kind"], row["coverage_category"], row["value"])))

    report = [
        "# Independent job-title and occupation benchmark",
        "",
        "This benchmark is separate from the Finaira NER corpus. It measures the existing JOB_TITLE resolver against external occupational title inventories and does not import any title into the production database.",
        "",
        "## Source status",
        "",
        "```json",
        json.dumps(source_files, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Coverage",
        "",
        "| Source | Language | Unique | Exact/normalized | Phrase candidate | Ambiguous | Generic fallback | Exact + phrase |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        recognized = item["verified_exact_or_normalized_unique"] + item["longest_phrase_candidate_unique"]
        report.append(f"| {item['source_kind']} | {item['language']} | {item['unique_values']:,} | {item['verified_exact_or_normalized_unique']:,} ({item['exact_pct']:.2f}%) | {item['longest_phrase_candidate_unique']:,} | {item['ambiguous_unique']:,} | {item['generic_fallback_only_unique']:,} | {recognized:,} ({item['candidate_recall_pct']:.2f}%) |")
    report += [
        "",
        "## Interpretation",
        "",
        "`VERIFIED_EXACT_OR_NORMALIZED` means the external title is already covered by an official/reviewed ESCO alias in the current database. `LONGEST_PHRASE_CANDIDATE` means only a contiguous phrase inside the external title matched and must not be counted as exact coverage. `AMBIGUOUS` must not be promoted without context. `GENERIC_FALLBACK_ONLY` is usable for safe generalization but is not evidence that the occupation was recognized.",
        "",
        "The O*NET and BLS sources are English and therefore test breadth independently of the Arabic NER corpus. CAPMAS and ASCO inputs are supported as Arabic CSVs when the official files are supplied. No missing source is silently replaced by another source.",
    ]
    (args.output / "benchmark_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "loaded_rows": len(rows), "source_files": source_files}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

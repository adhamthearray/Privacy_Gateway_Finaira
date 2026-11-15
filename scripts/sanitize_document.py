"""Prepare a placeholder document and print its policy JSON package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira.document_sanitizer import prepare_document  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON input file; stdin when omitted")
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument(
        "--hide-review-candidates",
        action="store_true",
        help="omit review-only candidates instead of returning them with production_eligible=false",
    )
    args = parser.parse_args()
    raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    request = json.loads(raw)
    result = prepare_document(
        request,
        args.db,
        include_review_candidates=not args.hide_review_candidates,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


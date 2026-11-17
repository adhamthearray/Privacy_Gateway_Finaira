"""Run the NER -> policy -> JEV handoff adapter locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finaira.integration import NERPolicyJEVGateway  # noqa: E402
from finaira.policy_config import PolicyConfig  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="NER JSON file; stdin when omitted")
    parser.add_argument("--db", type=Path, default=ROOT / "data/processed/finaira_generalization.db")
    parser.add_argument("--policy-config", type=Path, default=ROOT / "config/policy_actions.json")
    parser.add_argument("--hide-review-candidates", action="store_true")
    args = parser.parse_args()
    raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
    payload = json.loads(raw)
    config = PolicyConfig.from_file(args.policy_config)
    result = NERPolicyJEVGateway(
        args.db,
        include_review_candidates=not args.hide_review_candidates,
        policy_config=config,
    ).prepare(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


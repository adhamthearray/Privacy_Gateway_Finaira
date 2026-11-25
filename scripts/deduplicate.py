from __future__ import annotations

import csv
from collections import defaultdict
from difflib import SequenceMatcher

from common import DATA, REPORTS, normalize_prompt, read_jsonl


def main() -> None:
    prompts = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    exact = defaultdict(list)
    for row in prompts:
        exact[normalize_prompt(row["user_prompt"])].append(row["prompt_id"])
    findings = []
    for normalized, ids in exact.items():
        if len(ids) > 1:
            findings.append({"kind": "exact", "left": ids[0], "right": ids[1], "score": 1.0, "normalized": normalized})
    for index, left in enumerate(prompts):
        for right in prompts[index + 1 :]:
            if left["language_code"] != right["language_code"]:
                continue
            if left["prompt_family_id"] == right["prompt_family_id"]:
                continue
            score = SequenceMatcher(None, normalize_prompt(left["user_prompt"]), normalize_prompt(right["user_prompt"])).ratio()
            if score >= 0.88:
                findings.append({"kind": "near", "left": left["prompt_id"], "right": right["prompt_id"], "score": round(score, 4), "normalized": ""})
    path = REPORTS / "duplicate_report.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["kind", "left", "right", "score", "normalized"])
        writer.writeheader()
        writer.writerows(findings)
    print(f"Wrote duplicate report with {len(findings)} findings; no rows were deleted")


if __name__ == "__main__":
    main()


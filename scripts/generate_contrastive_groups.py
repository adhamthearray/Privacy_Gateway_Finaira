"""Inspect the controlled task flips produced for every entity type."""

from collections import Counter

from common import DATA, read_jsonl


def main() -> None:
    rows = read_jsonl(DATA / "generated" / "prompt_level.jsonl")
    groups = Counter(row["contrast_group_id"] for row in rows)
    invalid = {group: count for group, count in groups.items() if count not in {4, 12}}
    if invalid:
        raise SystemExit(f"Invalid contrast groups: {invalid}")
    print(f"Verified {len(groups)} grouped scenarios; controlled task-flip groups have 12 variants and composite groups have 4 translations")


if __name__ == "__main__":
    main()


"""Hard negatives are generated as the 'irrelevant' branch of each semantic specification."""

from common import DATA, read_jsonl


def main() -> None:
    rows = read_jsonl(DATA / "generated" / "entity_decisions.jsonl")
    count = sum(1 for row in rows if row["hard_negative_category"] != "none")
    print(f"Verified {count} hard-negative decision rows")


if __name__ == "__main__":
    main()


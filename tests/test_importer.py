import subprocess
import sys
from pathlib import Path

from common import ENTITY_TYPES, read_jsonl


ROOT = Path(__file__).resolve().parents[1]


def test_plain_text_import_is_pending_review(tmp_path: Path):
    source = tmp_path / "prompts.txt"
    output = tmp_path / "imported.jsonl"
    source.write_text("Identify the customer's bank.\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "import_examples.py"), str(source), "--output", str(output)],
        check=True,
        cwd=ROOT,
    )
    rows = read_jsonl(output)
    assert len(rows) == 10
    assert {row["target_entity_type"] for row in rows} == set(ENTITY_TYPES)
    assert all(row["annotation_status"] == "PENDING_REVIEW" for row in rows)
    assert all(row["approved_gold_label"] is None for row in rows)


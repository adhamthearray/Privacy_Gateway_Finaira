import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sqlite_store_is_append_only_and_resumable(tmp_path: Path):
    script = r'''
from annotation_store import append_adjudication, append_review, initialize, latest_adjudication_rows, latest_annotation_rows, latest_review
initialize()
append_review("P1", "alice", "SAVE_REVIEW", "prompt", "note", "2026-01-01T00:00:00+00:00", [{"entity_type":"AGE","reviewer_label":"RELEVANT","approved_reason":"required","ambiguous":False}])
append_review("P1", "bob", "SAVE_REVIEW", "prompt", "note", "2026-01-01T00:01:00+00:00", [{"entity_type":"AGE","reviewer_label":"IRRELEVANT","approved_reason":"not required","ambiguous":False}])
append_adjudication("P1", "AGE", "carol", "RELEVANT", "final", "2026-01-01T00:02:00+00:00")
assert latest_review("P1", "alice")[0]["label"] == "RELEVANT"
assert len(latest_annotation_rows()) == 2
assert latest_adjudication_rows()[0]["adjudicator_id"] == "carol"
print("store-ok")
'''
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["ANNOTATION_DB_PATH"] = str(tmp_path / "annotations.sqlite3")
    env["PYTHONPATH"] = str(ROOT / "scripts")
    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=ROOT, text=True, capture_output=True, check=True)
    assert "store-ok" in result.stdout


def test_postgres_url_uses_psycopg_and_ssl():
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://user:password@example.neon.tech/db"
    env["PYTHONPATH"] = str(ROOT / "scripts")
    result = subprocess.run(
        [sys.executable, "-c", "from annotation_store import DATABASE_URL; print(DATABASE_URL)"],
        env=env,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.strip() == "postgresql+psycopg://user:password@example.neon.tech/db?sslmode=require"


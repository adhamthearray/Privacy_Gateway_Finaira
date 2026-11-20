from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
payload = ROOT / "kaggle_payload"
payload.mkdir(exist_ok=True)
for source in (ROOT / "src", ROOT / "cases", ROOT / "scripts"):
    destination = payload / source.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
for filename in ("README.md", "config.yaml", "requirements.txt", "kaggle_one_cell.py", "kaggle_one_cell.ipynb"):
    source = ROOT / filename
    if source.exists():
        shutil.copy2(source, payload / filename)
archive = shutil.make_archive(str(ROOT / "test_v3_kaggle_payload"), "zip", root_dir=payload)
print(archive)

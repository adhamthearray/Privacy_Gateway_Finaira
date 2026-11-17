"""Build a focused ZIP handoff for the NER -> policy -> JEV integration."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = "Finaira_NER_Policy_JEV_Handoff_POC4"


def files_to_package() -> list[Path]:
    paths = [
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "config/policy_actions.json",
        ROOT / "data/processed/finaira_generalization.db",
        ROOT / "docs/ner_policy_jev_handoff.md",
        ROOT / "examples/ner_policy_jev_handoff_sample.json",
        ROOT / "scripts/run_ner_policy_jev_gateway.py",
        ROOT / "scripts/run_document_sanitizer_ui.py",
        ROOT / "tests/test_integration.py",
        ROOT / "tests/test_document_sanitizer.py",
        ROOT / "tests/test_document_sanitizer_ui.py",
    ]
    paths.extend(path for folder in (ROOT / "finaira", ROOT / "finaira_generalization") for path in folder.rglob("*.py"))
    return sorted({path for path in paths if path.is_file()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Finaira_NER_Policy_JEV_Handoff_POC4.zip")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        for path in files_to_package():
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, f"{PACKAGE_ROOT}/{relative}")
    print(f"Created {args.output}")
    print(f"Files: {len(files_to_package())}")
    print(f"Bytes: {args.output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


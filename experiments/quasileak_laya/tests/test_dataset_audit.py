from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quasileak_laya.dataset import audit_dataset, load_manifest, load_rows, rows_for_split


def test_released_hash_and_splits_are_valid():
    report = audit_dataset(
        ROOT / "vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl",
        ROOT / "vendor/QuasiLeak-Bench/data/splits/split_manifest.json",
        ROOT / "vendor/QuasiLeak-Bench/data/metadata/quasileak_bench_data_full.json",
    )
    assert report["valid"]
    assert report["split_counts"]["train"] == 3500
    assert report["split_counts"]["validation"] == 500
    assert report["split_counts"]["test"] == 1000
    assert report["profile_disjoint_train_validation_test"]


def test_split_filter_does_not_create_new_membership():
    rows = load_rows(ROOT / "vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl")
    manifest = load_manifest(ROOT / "vendor/QuasiLeak-Bench/data/splits/split_manifest.json")
    assert len(rows_for_split(rows, manifest, "test")) == 1000

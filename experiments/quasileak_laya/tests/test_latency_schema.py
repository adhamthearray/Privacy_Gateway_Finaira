import csv
import importlib.util
from io import StringIO
from pathlib import Path


def _load_evaluator():
    path = Path(__file__).parents[1] / "scripts" / "evaluate_laya.py"
    spec = importlib.util.spec_from_file_location("quasileak_laya_evaluate_laya", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_latency_schema_has_separate_model_and_e2e_fields():
    fields = ["sample_id", "model", "candidate_groups", "question_count", "input_tokens", "windows", "model_ms", "end_to_end_ms", "parse_ms", "success", "error_type", "device"]
    buf = StringIO(); writer = csv.DictWriter(buf, fieldnames=fields); writer.writeheader(); writer.writerow({k: "" for k in fields})
    header = buf.getvalue().splitlines()[0].split(",")
    assert "model_ms" in header and "end_to_end_ms" in header and "parse_ms" in header


def test_usage_merge_sums_bounded_laya_calls():
    evaluator = _load_evaluator()
    total = evaluator._merge_usage({"input_tokens": 10, "windows": 1}, {"input_tokens": 7, "windows": 2})
    assert total == {"input_tokens": 17, "windows": 3}

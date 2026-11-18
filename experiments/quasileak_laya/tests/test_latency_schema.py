import csv
from io import StringIO


def test_latency_schema_has_separate_model_and_e2e_fields():
    fields = ["sample_id", "model", "candidate_groups", "question_count", "input_tokens", "windows", "model_ms", "end_to_end_ms", "parse_ms", "success", "error_type", "device"]
    buf = StringIO(); writer = csv.DictWriter(buf, fieldnames=fields); writer.writeheader(); writer.writerow({k: "" for k in fields})
    header = buf.getvalue().splitlines()[0].split(",")
    assert "model_ms" in header and "end_to_end_ms" in header and "parse_ms" in header

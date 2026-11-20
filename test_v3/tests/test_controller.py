import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from test_v3.controller import run_case
from test_v3.detector import DetectorResponse, SyntheticRuleDetector


def test_controller_repairs_verified_synthetic_risk():
    case = json.loads(next((Path(__file__).parents[1] / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8")))
    result = run_case(case, SyntheticRuleDetector(), max_iterations=8, max_detector_calls=40)
    assert result["status"] in {"NO_RISK_AFTER_REPAIR", "NO_RISK_DETECTED"}
    assert result["normalized_loss"] >= 0
    assert result["privacy_claim"] == "NO_GUARANTEE_FROM_NO_DETECTION"


def test_controller_keeps_controls_non_risky():
    rows = [json.loads(line) for line in (Path(__file__).parents[1] / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8") if line.strip()]
    control = next(row for row in rows if not row["gold"]["verified_groups"])
    result = run_case(control, SyntheticRuleDetector())
    assert result["status"] == "NO_RISK_DETECTED"


def test_missing_evidence_uses_bounded_subset_probing():
    class HiddenEvidenceDetector(SyntheticRuleDetector):
        def predict(self, case, rendered):
            response = super().predict(case, rendered)
            if response.decision == "RISK":
                return DetectorResponse("RISK", response.protected_attribute, [], "hidden-evidence", response.latency_seconds)
            return response

    case = json.loads(next((Path(__file__).parents[1] / "cases" / "synthetic_cases.jsonl").open(encoding="utf-8")))
    result = run_case(case, HiddenEvidenceDetector(), max_iterations=4, max_detector_calls=40)
    assert result["iterations"][0].get("subset_probes")

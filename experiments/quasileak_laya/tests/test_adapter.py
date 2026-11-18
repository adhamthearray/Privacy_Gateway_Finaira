from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quasileak_laya.adapter import build_request, prediction_from_answers
from quasileak_laya.candidates import CandidateGroup, CandidateSpan, mine_groups, mine_spans, training_groups


DATA = ROOT / "vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl"


def row():
    return json.loads(DATA.open(encoding="utf-8").readline())


def test_text_only_spans_have_valid_codepoint_offsets():
    r = row(); spans = mine_spans(r["document"], max_spans=64)
    assert spans
    assert all(r["document"][s.start:s.end] == s.text for s in spans)


def test_group_proposals_are_non_overlapping_and_bounded():
    groups = mine_groups(mine_spans(row()["document"], max_spans=64), max_groups=32)
    assert len(groups) <= 32
    for group in groups:
        assert 2 <= len(group.spans) <= 4
        assert all(a.end <= b.start for a, b in zip(group.spans, group.spans[1:]))


def test_training_union_contains_hidden_gold_group():
    r = row(); groups = training_groups(r, max_groups=32)
    gold = {tuple(sorted((next(s for s in r["gold"]["spans"] if s["span_id"] == c)["start"], next(s for s in r["gold"]["spans"] if s["span_id"] == c)["end"]) for c in g["cue_ids"])): g["attribute"] for g in r["gold"]["groups"]}
    proposed = {tuple(sorted((s.start, s.end) for s in g.spans)) for g in groups}
    assert set(gold) <= proposed


def test_adapter_emits_finite_choice_questions_and_exact_evidence():
    r = row(); spans = r["gold"]["spans"][:2]
    group = CandidateGroup("test", tuple(CandidateSpan(s["span_id"], s["text"], s["start"], s["end"]) for s in spans), "test")
    request = build_request(r, [group], training=True)
    assert set(request["questions"]) == {"group_00000"}
    assert request["gold"]["group_00000"]["probabilities"]
    attr = r["policy"]["hide"][0]
    prediction = prediction_from_answers(r, [group], {"group_00000": {"choice": attr, "answer_confidence": 0.9}})
    assert prediction["sample_id"] == r["sample_id"]
    assert prediction["evidence"][0]["spans"] == [s["text"] for s in spans]


def test_inference_state_does_not_expose_gold_annotations():
    r = row(); groups = mine_groups(mine_spans(r["document"], max_spans=32), max_groups=4)
    request = build_request(r, groups, training=False)
    assert "gold" not in request
    assert "gold" not in request["state"]
    assert all("verification" not in q["instructions"] for q in request["questions"].values())


def test_low_confidence_and_keep_labels_are_not_emitted():
    r = row(); spans = r["gold"]["spans"][:2]
    group = CandidateGroup("test", tuple(CandidateSpan(s["span_id"], s["text"], s["start"], s["end"]) for s in spans))
    answer = {"group_00000": {"choice": r["policy"]["keep"][0], "answer_confidence": 0.99}}
    assert prediction_from_answers(r, [group], answer)["evidence"] == []

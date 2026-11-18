"""Conversion between QuasiLeak rows and Laya typed decisions."""

from __future__ import annotations

from typing import Iterable

from .candidates import CandidateGroup


def _state(row: dict) -> dict:
    # These are the model-facing inputs authorized by the official prompt:
    # document, reference profile, and policy. Candidate group text is put in
    # the question, not in gold labels or hidden annotations.
    profile = {key: row["profile"][key] for key in ("age", "gender", "nationality", "education", "occupation", "income", "relationship", "health")}
    return {"document": row["document"], "profile": profile, "policy": row["policy"]}


def _criteria(row: dict) -> dict[str, str]:
    hide = row["policy"]["hide"]
    return {"NONE": "none of these hidden attributes is jointly revealed"} | {
        attr: f"the candidate spans jointly reveal the hidden {attr} value"
        for attr in hide
    }


def _instruction(group: CandidateGroup) -> str:
    spans = "; ".join(f"{s.span_id}={s.text!r} [{s.start},{s.end})" for s in group.spans)
    return (
        "Decide which hidden profile attribute, if any, is jointly revealed by this complete candidate "
        "evidence group. Each span is weak alone; select NONE unless the spans together support one hidden "
        "attribute. Candidate spans are verbatim document text. Group: " + spans
    )


def _gold_label(row: dict, group: CandidateGroup) -> str:
    target = tuple(sorted((s.start, s.end) for s in group.spans))
    spans = {s["span_id"]: s for s in row["gold"]["spans"]}
    hidden = set(row["policy"]["hide"])
    for gold in row["gold"]["groups"]:
        key = tuple(sorted((spans[c]["start"], spans[c]["end"]) for c in gold["cue_ids"]))
        if key == target and gold["attribute"] in hidden:
            return gold["attribute"]
    return "NONE"


def build_request(row: dict, groups: Iterable[CandidateGroup], *, training: bool = False) -> dict:
    groups = list(groups)
    questions = {}
    gold = {}
    for index, group in enumerate(groups):
        qid = f"group_{index:05d}"
        questions[qid] = {"type": "choice", "instructions": _instruction(group), "criteria": _criteria(row)}
        if training:
            label = _gold_label(row, group)
            gold[qid] = {"probabilities": {key: float(key == label) for key in questions[qid]["criteria"]}}
    result = {"sample_id": row["sample_id"], "state": _state(row), "questions": questions}
    if training:
        result["gold"] = gold
    return result


def prediction_from_answers(row: dict, groups: Iterable[CandidateGroup], answers: dict, *, threshold: float = 0.55) -> dict:
    groups = list(groups)
    evidence = []
    for index, group in enumerate(groups):
        answer = answers.get(f"group_{index:05d}") or {}
        label = answer.get("choice")
        confidence = float(answer.get("answer_confidence", answer.get("confidence", 0.0)) or 0.0)
        if label and label != "NONE" and label in row["policy"]["hide"] and confidence >= threshold:
            evidence.append({"attribute": label, "spans": [s.text for s in group.spans]})
    return {"sample_id": row["sample_id"], "evidence": evidence}

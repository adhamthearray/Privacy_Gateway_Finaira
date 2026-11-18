"""Finaira's isolated QuasiLeak-Bench/Laya experiment adapter.

This package deliberately does not modify Finaira's production generalization or
MILP code.  It turns the released QuasiLeak rows into typed Laya decisions and
then converts those decisions back to the official evidence schema.
"""

from .adapter import build_request, prediction_from_answers
from .candidates import CandidateGroup, CandidateSpan, mine_groups, mine_spans, oracle_groups
from .dataset import load_rows, rows_for_split

__all__ = [
    "CandidateGroup",
    "CandidateSpan",
    "build_request",
    "load_rows",
    "mine_groups",
    "mine_spans",
    "oracle_groups",
    "prediction_from_answers",
    "rows_for_split",
]

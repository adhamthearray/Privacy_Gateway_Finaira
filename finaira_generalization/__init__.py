"""Offline, deterministic bilingual generalization reference engine."""

from .engine import Generalizer, Result
from .build import build_database
from .candidates import GeneralizationDB
from .handoff import import_handoff
from .date_detector import DateDetection, detect_date
from .monetary import DEFAULT_BUCKETS, generalize_threshold, interpret_and_generalize_money

__all__ = ["Generalizer", "Result", "GeneralizationDB", "build_database", "import_handoff", "DateDetection", "detect_date", "DEFAULT_BUCKETS", "generalize_threshold", "interpret_and_generalize_money"]

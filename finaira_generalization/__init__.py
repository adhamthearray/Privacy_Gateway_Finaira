"""Offline, deterministic bilingual generalization reference engine."""

from .engine import Generalizer, Result
from .build import build_database
from .candidates import GeneralizationDB
from .handoff import import_handoff

__all__ = ["Generalizer", "Result", "GeneralizationDB", "build_database", "import_handoff"]

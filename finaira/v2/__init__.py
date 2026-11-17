"""Finaira V2 task-aware document generalization optimizer.

This package is intentionally separate from the existing request pipeline. It
accepts upstream annotations, performs exact/direct local database lookup, and
returns explainable V1/greedy/V2 comparisons without calling an LLM.
"""

from .core import (
    CaseScopedPseudonymizer,
    Candidate,
    EntitySpec,
    EvaluationTargets,
    OptimizationRequest,
    TaskProfile,
    V2Optimizer,
    build_real_examples,
    exhaustive_optimum,
    export_csv,
    make_golden_fixture,
)
from .benchmark import run_benchmarks, synthetic_benchmark_request

__all__ = [
    "CaseScopedPseudonymizer",
    "Candidate",
    "EntitySpec",
    "EvaluationTargets",
    "OptimizationRequest",
    "TaskProfile",
    "V2Optimizer",
    "build_real_examples",
    "exhaustive_optimum",
    "export_csv",
    "make_golden_fixture",
    "run_benchmarks",
    "synthetic_benchmark_request",
]

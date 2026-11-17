# Finaira V2 executed results

These results were produced locally on 18 November 2026 from the current
repository and the current `data/processed/finaira_generalization.db`.

## Baseline and golden fixture

The untouched repository baseline before V2 changes was **97 passed in 72.40s**.

The required fixed synthetic golden fixture produced:

| Run | Selection | Utility | Specificity | Structural reduction |
|---|---|---:|---:|---:|
| Independent V1 | AGE pseudonym; IT Professional; Cairo | 0 | 1.40 | — |
| V2, U-max=1 | AGE pseudonym; IT Professional; Egypt | 1 | 1.00 | 28.5714% |
| V2, U-max=2 | AGE pseudonym; IT Professional; location pseudonym | 2 | 0.80 | 42.8571% |

The same V2 objective was verified by the independent exhaustive enumerator
for the small fixture. These scores are fixed synthetic test values required
by the specification, not database-derived privacy claims.

## Real policy/database examples

The real scenario loader generated English and Arabic scenarios only after
checking each value against the local database with exact/direct lookup and a
`MATCHED` or `VERIFIED` result. The checked entity types were `AGE`,
`JOB_TITLE`, `BANK`, and `NATIONALITY`. No substring-only or review-only value
was used to construct a production example.

The English professional scenario was feasible at `U-max=1`; V1 and V2 both
selected broad zero-utility-loss configured/database representations in this
task profile, so the observed structural reduction was 0%. This is a valid
comparison result, not evidence that V2 is universally better.

The Arabic scenario used a demographic task profile and was also feasible;
Arabic candidates with missing verified translations correctly fell back to
typed pseudonyms rather than inventing Arabic labels.

## Benchmark sizes

The deterministic synthetic benchmark ran 5, 10, 20, 50, and 100 entities ×
5 candidates. Results are in `benchmark_results.json`. The V2 MILP runs were
feasible with solver status 0 and used 25, 50, 100, 250, and 500 decision
variables respectively. This benchmark is for solver scaling only and does
not represent real database coverage.

## Evaluation status

No downstream task ground-truth evaluator was supplied, so the dashboard and
comparison reports use:

`OPTIMIZATION_COMPARISON_ONLY — TASK PERFORMANCE NOT YET VALIDATED`

The specificity label is **Structural Disclosure Reduction**, never
re-identification risk reduction.

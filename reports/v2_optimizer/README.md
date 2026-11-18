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

## Sentence benchmark

The added sentence benchmark creates 100 deterministic English/Arabic
sentences using five annotated policy-generalizable entities per sentence:
`AGE`, `JOB_TITLE`, `BANK`, `NATIONALITY`, and `COUNTRY`. Database-backed
values are admitted only after exact/direct `MATCHED` or `VERIFIED` lookup;
the template text is synthetic, but the protected entity values are real local
source values. It records every sentence, offset, source record, lookup mode,
V1/greedy/V2 status, utility, specificity, pseudonym count, and runtime.

Executed result for the 100-sentence run:

- 100 sentences / 500 annotated entities.
- 50 English and 50 Arabic sentences.
- 400 database-backed values passed exact/direct validation.
- 100 AGE values came from deterministic Finaira configuration.
- V1 feasible: 50/100.
- Greedy feasible: 50/100.
- V2 feasible: 50/100.
- Average V1 specificity: 0.375.
- Average V2 specificity: 0.250.
- Average structural reduction among comparable feasible cases: 33.3333%.
- Average V2 runtime: 4.403 ms per sentence after lookup caching; total benchmark elapsed time was 38.236 seconds.
- V2 pseudonymized entities: 134.
- Arabic cases were infeasible because some exact Arabic nationality aliases
  had no usable non-exact Arabic generalization candidate. V2 returned a clear
  `NO_ALLOWED_CANDIDATE` result rather than inventing a translation.
- The 50 infeasible cases were all Arabic demographic cases and were blocked
  at the nationality entity; the English 50/50 cases were feasible.
- Corporation and government pools were empty after exact/direct admission and
  were therefore not silently included.

This is the important coverage finding: exact alias recognition succeeded for
the admitted values, but recognition does not guarantee a usable same-language
generalization form. The Arabic infeasibility is a database breadth gap, not
an optimizer crash.

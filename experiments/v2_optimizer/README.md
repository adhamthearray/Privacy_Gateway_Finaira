# Finaira V2 Optimizer

This is an isolated local playground for Finaira V2. It receives a
semi-sanitized document and upstream entity annotations; it does not perform
NER, subject association, Laya inference, cloud calls, or changes to the
production sanitizer/database.

The production scenario loader in `finaira.v2.core.build_real_examples()`
uses only entity types whose current policy action is `GENERALIZE` and checks
each value with `GeneralizationDB.get_candidates(..., input_language=...)`.
It requires a `MATCHED` or `VERIFIED` result and an exact/direct alias before
the example is created. Exact/raw values are never selectable. Review-only,
suppressed, local-only, unavailable, and unverified candidates are excluded.

The V2 adapter adds a typed pseudonym candidate for every generalizable entity
and reserves it before V1, greedy, or V2 selection. Mappings are case-scoped,
stable by upstream identity/canonical database ID, and use existing
`__FN_TYPE_0001__` placeholders. Direct identifiers already present in the
semi-sanitized text are preserved.

## Run

```powershell
py -X utf8 experiments/v2_optimizer/app.py
```

Open `http://127.0.0.1:7862`. Override the port with `$env:FINAIRA_V2_PORT`.

The UI exposes candidate inventory, utility loss, structural specificity,
terminal pseudonyms, V1/greedy/V2 transformed documents, MILP status, a utility
budget sweep, and CSV/JSON export.

## APIs and tests

```powershell
py -X utf8 -m pytest -q tests/test_v2_optimizer.py
py -X utf8 scripts/run_v2_sentence_benchmark.py
py -X utf8 -c "from finaira.v2 import run_benchmarks; import json; print(json.dumps(run_benchmarks(), indent=2))"
py -X utf8 -m pytest -q
```

The sentence benchmark generates 100 synthetic sentences from real repository
values. Banks, countries, nationalities, occupations, corporations, and
government values are admitted only after an exact/direct `MATCHED` or
`VERIFIED` lookup; configured AGE/DATE values are labeled as configuration
inputs. Each sentence carries upstream offsets and 5 policy-generalizable
entities, alternating English and Arabic. Results are written to
`reports/v2_optimizer/sentence_benchmark_results.json`.

`V2Optimizer.independent_baseline()` chooses independently by utility, then
specificity. `greedy_baseline()` applies global changes within the same budget.
`V2Optimizer.v2_milp()` uses SciPy MILP with exactly-one, mandatory-fact,
utility-budget, and optional detailed-QI constraints, followed by a
lexicographic utility stage. `exhaustive_optimum()` is for small tests only.

The required golden fixture is isolated in `make_golden_fixture()`. It uses
the specification's fixed synthetic AGE/JOB/LOCATION scores; `LOCATION` is not
in the current production policy table and is deliberately not offered by the
real scenario loader or UI.

## Scope and limitations

Finaira V2 performs task-constrained, document-level structural information
minimization. Its specificity metric is not a population-based
re-identification probability. The system does not yet detect all higher-order
semantically revealing combinations of quasi-identifiers. Document-level
aggregation can combine QIs belonging to unrelated individuals because subject
association is intentionally outside V2's scope.

If no deterministic task evaluator is supplied, the dashboard labels results
`OPTIMIZATION_COMPARISON_ONLY — TASK PERFORMANCE NOT YET VALIDATED` and does
not claim that V2 is better. The configurable target thresholds are research
targets, not banking or privacy safety standards.

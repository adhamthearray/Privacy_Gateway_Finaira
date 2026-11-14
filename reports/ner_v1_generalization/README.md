# NER generalization coverage exports

Generated from `finaira_ner_v1` with:

```powershell
py scripts/audit_ner_generalization_coverage.py `
  --dataset C:\path\to\finaira_ner_v1\finaira_ner_v1 `
  --db data\processed\finaira_generalization.db
```

`coverage_summary.csv` contains percentages by entity. `coverage_values.csv` contains one row per distinct value with its annotated span count, source split/origin, resolution status, candidate levels, fallback state, and next action. `missing_<entity>.csv` contains every value that is not `MATCHED_OR_VERIFIED`. The Markdown report includes the highest-frequency gaps.

The audit covers database generalization entities only: BANK, COUNTRY, NATIONALITY, CORPORATION, ORGANIZATION, UNIVERSITY, GOVERNMENT_ENTITY, JOB_TITLE, AGE, and DATE. Source `OCCUPATION` spans are accepted for compatibility and merged into canonical `JOB_TITLE`; they are not reported as a separate production entity. Other NER labels are masking or privacy-pipeline labels, not current reference-database lookup types.

# NER-v1 generalization coverage: before and after

Dataset: `C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1`

The audit counts distinct annotated values and annotated spans. Only the 11 permitted generalization labels are included. Values outside these labels remain outside this database/API.

| Entity | Before matched values | After matched values | Before span coverage | After span coverage | Change made |
|---|---:|---:|---:|---:|---|
| BANK | 0.00% | 0.00% | 0.00% | 0.00% | Kept 37-bank authority and review-only Arabic aliases; generated queue for evidence review |
| COUNTRY | 49.78% | 62.45% | 80.03% | 92.82% | Added verified Wikidata labels/aliases linked to Natural Earth QIDs |
| NATIONALITY | 35.65% | 35.65% | 55.52% | 55.52% | Preserved P1549 source and unresolved demonyms; no guesses |
| CORPORATION | 0.00% | 0.00% | 0.00% | 0.00% | Kept organization identity approval gate; queued corpus values |
| ORGANIZATION | 0.00% | 0.00% | 0.00% | 0.00% | No values in the supplied dataset |
| UNIVERSITY | 0.00% | 0.00% | 0.00% | 0.00% | No values in the supplied dataset |
| GOVERNMENT_ENTITY | 0.00% | 0.00% | 0.00% | 0.00% | Kept seed identities review-only; queued unresolved values |
| JOB_TITLE | 0.86% | 0.86% | 1.84% | 1.84% | Preserved ESCO/ISCO source and aliases; no runtime fuzzy matching |
| OCCUPATION | 0.85% | 0.85% | 1.27% | 1.27% | Preserved ESCO/ISCO source and aliases; no fabricated mappings |
| AGE | 100.00% | 100.00% | 100.00% | 100.00% | Preserved deterministic age configuration |
| DATE | 24.65% | 79.10% | 24.68% | 79.10% | Added deterministic year-first/day-first parsing and explicit-format support; ambiguous dates remain unresolved |

Exact values and counts are in `coverage_summary.csv` and `coverage_values.csv`. The review queue contains 5,638 non-matched or gated distinct values covering 22,636 spans. Each row has frequency, source context, reason, source-backed reviewer guidance, and a pending review decision. It is not imported into production tables.

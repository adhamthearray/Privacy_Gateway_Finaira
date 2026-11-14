# NER-v1 generalization coverage: before and after

Dataset: `C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1`

The audit counts distinct annotated values and annotated spans. Only the 11 permitted generalization labels are included. Values outside these labels remain outside this database/API.

| Entity | Before matched values | After matched values | Before span coverage | After span coverage | Change made |
|---|---:|---:|---:|---:|---|
| BANK | 0.00% | 0.00% | 0.00% | 0.00% | Kept 37-bank authority and review-only Arabic aliases; generated queue for evidence review |
| COUNTRY | 62.45% | 75.98% | 92.82% | 96.51% | Added 31 approved current-country review rows, deduplicated to 30 runtime aliases; historical, ambiguous, city/region, and malformed values remain suppressed |
| NATIONALITY | 35.65% | 86.96% | 55.52% | 84.18% | Approved 59 verified reviewed variants; corrected one stale Palestine plan QID; held 15 values |
| CORPORATION | 0.00% | 0.00% | 0.00% | 0.00% | Kept organization identity approval gate; queued corpus values |
| ORGANIZATION | 0.00% | 0.00% | 0.00% | 0.00% | No values in the supplied dataset |
| UNIVERSITY | 0.00% | 0.00% | 0.00% | 0.00% | No values in the supplied dataset |
| GOVERNMENT_ENTITY | 0.00% | 0.00% | 0.00% | 0.00% | Kept seed identities review-only; queued unresolved values |
| JOB_TITLE | 0.86% | 0.86% | 1.84% | 1.84% | Preserved ESCO/ISCO source and aliases; no runtime fuzzy matching |
| OCCUPATION | 0.85% | 0.85% | 1.27% | 1.27% | Preserved ESCO/ISCO source and aliases; no fabricated mappings |
| AGE | 100.00% | 100.00% | 100.00% | 100.00% | Preserved deterministic age configuration |
| DATE | 24.65% | 79.10% | 24.68% | 79.10% | Added deterministic year-first/day-first parsing and explicit-format support; ambiguous dates remain unresolved |

Exact values and counts are in `coverage_summary.csv` and `coverage_values.csv`. The country review queue contains 86 baseline gaps: 31 approved rows covering 111 spans, 25 pending rows covering 41 spans, and 30 rejected rows covering 64 spans. The final COUNTRY audit has 55 suppressed values covering 105 spans. The nationality adjudication queue has 15 unresolved values covering 96 spans. Each row has frequency, source context, reason, source-backed reviewer guidance, and a review decision. Only approved current-country rows are imported into production.

## Job-title/occupation resolver update (2026-11-14)

The runtime now merges the source labels `JOB_TITLE` and `OCCUPATION` into canonical `JOB_TITLE`. The old audit had separate rows (2,214 job-title values / 9,444 spans and 236 occupation values / 472 spans). The regenerated merged audit contains 2,442 unique values and 9,916 spans: 31 values / 203 spans are verified ESCO/ISCO matches, including 10 values / 19 spans found through longest-phrase matching; 5 values / 6 spans are ambiguous; and 2,406 values / 9,707 spans receive the configured generic fallback. The fallback is not a unique pseudonym and does not promote any unverified value.

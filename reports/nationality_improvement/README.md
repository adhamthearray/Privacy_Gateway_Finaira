# Nationality improvement workflow

The current production source contains 857 source-verified Arabic/English Wikidata `P1549` aliases plus 59 reviewed Arabic variants. The remaining NER-v1 misses are mostly unresolved QIDs, spelling/source gaps, and malformed or context-dependent forms.

The original review queue contained 74 missing corpus values and 82 suggestion rows. Verification approved 59 unique corpus values covering 174 spans. Duplicate derivations are retained in provenance but collapse to one runtime alias per normalized value/QID. Fifteen values remain pending and one stale plan QID is rejected.

## Review procedure

1. Open `nationality_variant_review_queue.csv` with UTF-8 encoding.
2. Check each `REVIEW_ONLY` row against the source-backed base alias and the actual corpus context.
3. Set `review_decision` to `APPROVED` only when the derived form is valid for the nationality label.
4. Add an evidence URL or file reference in `evidence_reference`.
5. Leave uncertain rows as `PENDING`, or mark them `REJECTED`.
6. Run `scripts/verify_nationality_adjudication.py --apply` after any manual review change. It rechecks the source/QID/context gates and updates the authoritative queue.
7. Run the handoff import. Only approved rows with evidence are imported as `REVIEWED` aliases.

```powershell
py -X utf8 scripts/build_nationality_variant_review.py
py -X utf8 scripts/verify_nationality_adjudication.py --apply
py -X utf8 -m finaira_generalization.cli import-handoff
py -X utf8 scripts/audit_ner_generalization_coverage.py --dataset C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1 --db data\processed\finaira_generalization.db --output reports\ner_v1_generalization
py -X utf8 scripts/build_nationality_variant_review.py
py -X utf8 -m pytest -q
```

The importer is idempotent and records the review CSV checksum in `data_sources`. Pending suggestions never affect runtime lookup. No country name is converted into a nationality, and no fuzzy or morphology-based runtime matching is enabled. The plan's Palestine `Q219060` proposal was rejected as not being the Natural Earth country QID; the independently verified current P1549 row for `فلسطينيون` under `Q23792` was imported instead.

## Current result

After import, NATIONALITY coverage is 100/115 distinct values (86.96%) and 511/607 spans (84.18%). The remaining 15 values covering 96 spans are still unresolved or intentionally held. Production contains 59 reviewed aliases with 67 derivation/provenance rows.

# Nationality improvement workflow

The current production source contains 857 source-verified Arabic/English Wikidata `P1549` aliases. The remaining NER-v1 misses are mostly Arabic surface-form variants such as definite-article, feminine, and plural forms.

The review queue contains 74 missing corpus values. It proposes 64 values covering 274 spans where a conservative surface-form reduction reaches one unique, already verified Wikidata demonym. The suggestions are not production aliases.

## Review procedure

1. Open `nationality_variant_review_queue.csv` with UTF-8 encoding.
2. Check each `REVIEW_ONLY` row against the source-backed base alias and the actual corpus context.
3. Set `review_decision` to `APPROVED` only when the derived form is valid for the nationality label.
4. Add an evidence URL or file reference in `evidence_reference`.
5. Leave uncertain rows as `PENDING`, or mark them `REJECTED`.
6. Run the handoff import. Only approved rows with evidence are imported as `REVIEWED` aliases.

```powershell
py -X utf8 scripts/build_nationality_variant_review.py
py -X utf8 -m finaira_generalization.cli import-handoff
py -X utf8 scripts/audit_ner_generalization_coverage.py --dataset C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1 --db data\processed\finaira_generalization.db --output reports\ner_v1_generalization
py -X utf8 scripts/build_nationality_variant_review.py
py -X utf8 -m pytest -q
```

The importer is idempotent and records the review CSV checksum in `data_sources`. Pending suggestions never affect runtime lookup. No country name is converted into a nationality, and no fuzzy or morphology-based runtime matching is enabled.

## Current result

Before approval, NATIONALITY remains 41/115 distinct values and 337/607 spans matched. The queue identifies 64 additional values for human review; it does not claim those values are correct until approved.

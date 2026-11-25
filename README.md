# Finaira Laya task-conditioned relevance dataset

This is an independent research project for classifying the relevance of exactly ten entity **types** from a user task. It does not read customer documents, connect to the Finaira/customer database, or alter production privacy policy. `MONETARY_AMOUNT` remains pseudonymized and `COUNTRY` remains allowed in the separate production policy; this project only studies task relevance.

The pilot contains 36 human-designed semantic task specifications, 144 multilingual prompts, and 1,440 prompt × entity-type decisions. Every generated decision is `PENDING_REVIEW`. Consequently, official Laya train/validation/test exports are intentionally empty until humans approve labels.

## Reproduce the pilot

Run from this directory on Windows:

```powershell
py -3.13 scripts/build_ontology.py
py -3.13 scripts/build_taxonomy.py
py -3.13 scripts/generate_task_specs.py
py -3.13 scripts/generate_prompt_variants.py
py -3.13 scripts/assign_splits.py
py -3.13 scripts/validate_semantics.py
py -3.13 scripts/deduplicate.py
py -3.13 scripts/generate_coverage_reports.py
py -3.13 scripts/export_laya.py
```

Grouped splitting assigns entire scenarios to train, validation, or test using an approximately 70/15/15 group ratio. All translations, relevance flips, and ten entity decisions stay together.

## Review locally

```powershell
py -3.13 annotation_ui/app.py --port 7862
```

The running instance for this workspace is at `http://127.0.0.1:7862` because ports 7860–7861 were already occupied. It displays one prompt and its complete ten-type matrix, filters, editable wording/rationales, contrast-group comparisons, append-only independent annotations, prompt rejection, agreement status, and adjudication. Annotation history is stored locally in `data/annotations.sqlite3`.

## Deploy for shared annotation

Use the included `Dockerfile` and `render.yaml` to deploy this directory as an independent password-protected Render Free service backed by Neon Free PostgreSQL. Follow [DEPLOY_RENDER.md](DEPLOY_RENDER.md). The deployed login username is automatically used as the reviewer identity, and annotations survive Render restarts because they are stored outside its ephemeral filesystem.

## Import future examples

```powershell
py -3.13 scripts/import_examples.py path\to\examples.csv
```

CSV, JSON, JSONL, and plain text are accepted. Prompt-like fields are detected, provenance is retained, and every suggestion stays pending review.

## Gold export and training preparation

`scripts/export_laya.py` excludes unreviewed and ambiguous rows. Laya receives only the user task, explicit task requirements, target entity type, and neutral type description. Research metadata and rationales never enter `state`.

Run `py -3.13 training/prepare_training.py --dry-run` after approved exports exist. Expensive fine-tuning is intentionally not launched in this phase.

## Known limitation

This predicts prompt-conditioned type relevance, not occurrence relevance. `COUNTRY` and `MONETARY_AMOUNT` each cover several semantic roles, so a type-level prediction cannot imply that every matching occurrence in a document should be retained.


# Laya schema validation

Validated on 2026-11-26 with the isolated PyPI package `laya==0.5.4` and its actual `laya-train --help` output.

Command:

```powershell
laya-train --data tests/fixtures/laya_schema_fixture.jsonl --base multilingual --loss soft-ce --shuffle-options --seed 20261126 --dry-run
```

Observed result:

```text
dry-run: 1 rows read, 1 valid items, skipped: {}
dry-run: optimizer budget: 1 train item(s), effective batch up to 64 (micro_batch 8 x grad_accum 8), 4 optimizer updates over 4 epoch(s)
```

The fixture is explicitly schema-only and is never included in train/validation/test exports. Laya 0.5.4 confirmed the supported flags `--data`, `--eval`, `--out`, `--base`, `--loss`, `--label-smoothing`, `--shuffle-options`, `--epochs`, `--micro-batch`, `--grad-accum`, `--encoder-lr`, `--head-lr`, `--seed`, and `--dry-run`. The dry-run downloaded tokenizer/configuration files for the named base but did not train or load model weights.


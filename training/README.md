# Fine-tuning preparation

The project uses Laya's documented hard-label JSONL form: a textual `state`, constant `questions`, and `expected` containing the selected choice. `gold` probability distributions are not fabricated. The `multilingual` built-in base is selected.

After human review and export:

```powershell
py -3.13 scripts/export_laya.py
py -3.13 training/prepare_training.py --dry-run
```

Then run the printed `laya-train` command in an environment where Laya is installed. Keep option shuffling enabled, evaluate on validation, reserve test for final reporting, and fit any temperature/calibration parameter on an independent held-out calibration set. The preparation script refuses all training preparation while approved train or validation data is empty; use the explicit test fixture command recorded in `reports/laya_schema_validation.md` to verify only the schema.

Checkpoint/resume behavior should be selected from the installed Laya version's `laya-train --help` before a real run; this repository does not invent version-specific flags.


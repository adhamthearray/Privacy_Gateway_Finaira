# Finaira V3 — QLB-guided minimal generalization

This is an isolated experiment under `test_v3/`. It does not modify Finaira V2 or the production generalization database.

The controller starts with the raw semi-sanitized observation, renders the complete document, sends it to the fine-tuned QuasiLeak-Bench Qwen detector, converts a detected evidence group into an exact no-good constraint, and solves for the minimum sum of normalized ladder loss. Raw exact values are observation-only and are excluded from optimizer ladders. It stops after a bounded number of iterations or detector calls.

The objective is **minimum normalized generalization loss**, not task utility and not a calibrated privacy probability. A `NO_RISK_DETECTED` result means only that this detector did not report a prohibited group. It is never reported as a guarantee of privacy.

## Files

- `src/test_v3/ladder.py`: policy-filtered ladders and normalized loss.
- `src/test_v3/solver.py`: OR-Tools CP-SAT path with deterministic exhaustive fallback for small local tests.
- `src/test_v3/detector.py`: explicit synthetic test detector and real QLB Qwen/PEFT adapter.
- `src/test_v3/controller.py`: bounded detector → cut → solve loop.
- `src/test_v3/reporting.py`: JSON summary and searchable RTL-capable HTML report.
- `cases/synthetic_cases.jsonl`: exactly 50 deterministic cases: 36 Arabic, 9 mixed, 5 English; 30 verified synthetic-rule positives and 20 controls. Annotated AGE, JOB_TITLE, BANK, NATIONALITY, COUNTRY and DATE values are admitted through one MATCHED/VERIFIED exact/direct lookup against the local Finaira DB; candidate provenance is retained.
- `scripts/generate_cases.py`: regenerates and revalidates the cases with seed 42 from the current DB.
- `scripts/run_experiment.py`: local synthetic-detector run; no model claim.
- `scripts/package_for_kaggle.py`: builds the upload payload.
- `kaggle_one_cell.py`: real-model Kaggle runner.
- `kaggle_one_cell.ipynb`: one-cell wrapper for the runner.

## Local tests

```powershell
py test_v3/scripts/generate_cases.py
py -m pytest -q test_v3/tests
py test_v3/scripts/run_experiment.py --limit 3 --out test_v3/results_smoke
```

The local run uses `SyntheticRuleDetector` only to test controller, solver, rendering, cache, and report behavior. Its 1.0 precision/recall is only against the explicit finite synthetic rules; it is not a Qwen result and not a real-world privacy result. The committed `results_db_backed/` directory is the executed local artifact.

## Kaggle preparation

Run:

```powershell
py test_v3/scripts/package_for_kaggle.py
```

Upload the resulting `test_v3_kaggle_payload.zip` contents, together with the real adapter directory, as a Kaggle dataset named `test_v3`. The adapter must contain `adapter_config.json`, `adapter_model.safetensors`, and preferably `best_metadata.json`. A merged Hugging Face checkpoint with `config.json` and weights is also accepted.

The cell discovers nested checkpoint directories under `/kaggle/input`, validates the base model, removes Kaggle's incompatible optional `torchao` package before importing PEFT, performs a real smoke inference, and then runs the configured 50 cases. It writes only to `/kaggle/working/test_v3_results/` and packages the result zip.

## Interpretation limits

The QLB model detects policy-conditioned quasi-evidence groups. It is not an identity re-identification proof system. Synthetic positives are verified against explicit finite fixture rules, not claims about real people. Unsupported, malformed, uncertain, or unparseable model output remains unresolved and is never converted to `SAFE`. No real Qwen/Kaggle result is claimed until the uploaded checkpoint completes the runner.

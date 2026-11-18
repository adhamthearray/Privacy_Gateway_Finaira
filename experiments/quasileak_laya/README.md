# Finaira QuasiLeak-Bench / Laya experiment

This is an isolated research experiment. It does not modify Finaira's production database, generalization resolver, pseudonym vault, or V2 MILP pipeline.

The experiment answers whether the local non-autoregressive Laya decision model can be adapted to QuasiLeak-Bench's policy-conditioned joint evidence-group recovery task and compared fairly with the released Qwen3.5-4B LoRA recipe.

## Current state

- Official QuasiLeak-Bench repository is vendored at `vendor/QuasiLeak-Bench` at commit `75987cdf029fac5fecce160bea218b458ed46dbb`.
- Full 5,000-row data archive is extracted locally and audited.
- The released split contains 3,500 train, 500 validation, and 1,000 test rows over disjoint 350/50/100 profiles.
- Official scorer, renderer, training builder, and split manifest are retained unchanged.
- Official Laya source is vendored at `vendor/laya` at commit `d1282e791d71e92f24f816ff3836e4fd1c2ded4a`.
- Laya is confirmed to be a typed, non-autoregressive ModernBERT decision engine—not a generative LM. See `MODEL_DISCOVERY.md`.
- Text-only span/group proposal and Laya choice-question adapters are implemented.
- The current machine has CPU-only PyTorch and no CUDA GPU. C0/C1/C2/C3 full runs are therefore pending GPU; no accuracy or timing result is claimed.

## Files

- `src/quasileak_laya/candidates.py`: deterministic text-only span/group proposals and training-positive union.
- `src/quasileak_laya/adapter.py`: official row → Laya typed questions → official evidence.
- `src/quasileak_laya/dataset.py`: row validation, official split and hash audit.
- `scripts/audit_dataset.py`: reproducible dataset audit.
- `scripts/prepare_data.py`: training/dev adapter JSONL builder.
- `scripts/evaluate_laya.py`: resumable C0/C1 evaluation with raw answers, per-request latency, and official scoring.
- `scripts/train_laya.py`: official `laya.train` fine-tuning wrapper.
- `scripts/train_qwen.py`: released QuasiLeak Qwen LoRA wrapper with a hard CUDA gate.
- `scripts/download_models.py`: model download and provenance manifest.
- `scripts/compare_results.py`: no-fabrication comparison table; missing runs remain null.
- `tests/`: adapter, split, proposal, and latency-record tests.
- `kaggle/quasileak_laya_experiment.ipynb`: GPU workflow.
- `DATASET_AUDIT.md`, `MODEL_DISCOVERY.md`, `METHODOLOGY.md`, `REPRODUCE.md`: audit and method records.

## Important scientific limitation

The candidate proposer is deterministic and text-only. It does not receive gold cues at validation or test time. Proposal recall is reported separately. A low official score can therefore come from proposal recall, Laya decisions, or thresholding; the raw artifacts preserve enough detail to distinguish them.

For an upper-bound diagnostic only, `evaluate_laya.py --candidate-mode oracle` supplies released gold groups to Laya and labels the result `diagnostic_only`. It must not be presented as the primary detector result.

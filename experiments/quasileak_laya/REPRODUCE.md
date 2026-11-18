# Reproduce the experiment

Run from the Finaira repository root.

## Fetch pinned official sources

The official source checkouts and CC BY-NC-SA data are kept out of the Finaira commit. Recreate them with:

```powershell
py experiments/quasileak_laya/scripts/fetch_official_sources.py --root experiments/quasileak_laya
```

This checks out the recorded QuasiLeak-Bench and Laya commits, extracts the official archive, and writes `results/source_manifest.json`.

## Local data audit and adapters

```powershell
py experiments/quasileak_laya/scripts/audit_dataset.py `
  --dataset experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl `
  --manifest experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/splits/split_manifest.json `
  --metadata experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/metadata/quasileak_bench_data_full.json `
  --json-out experiments/quasileak_laya/results/dataset_audit.json `
  --markdown-out experiments/quasileak_laya/DATASET_AUDIT.md

py experiments/quasileak_laya/scripts/prepare_data.py ... --split train --training-positives --out experiments/quasileak_laya/results/laya_train.jsonl
py experiments/quasileak_laya/scripts/prepare_data.py ... --split validation --out experiments/quasileak_laya/results/laya_dev.jsonl
```

Use `--max-groups 64` for a quick CPU smoke adapter and 256 or higher for a GPU run. The training JSONL contains gold positives; validation/test JSONL does not.

## Download model artifacts

```powershell
py experiments/quasileak_laya/scripts/download_models.py --model-id convaiinnovations/laya --out-root experiments/quasileak_laya/models
```

Qwen is downloaded only on a GPU machine or Kaggle because the official training recipe requires BF16 CUDA.

## Fine-tune and evaluate Laya

```powershell
py experiments/quasileak_laya/scripts/train_laya.py `
  --train experiments/quasileak_laya/results/laya_train.jsonl `
  --dev experiments/quasileak_laya/results/laya_dev.jsonl `
  --model-dir experiments/quasileak_laya/models/convaiinnovations__laya `
  --out experiments/quasileak_laya/results/laya_finetuned

py experiments/quasileak_laya/scripts/evaluate_laya.py `
  --dataset experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl `
  --manifest experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/splits/split_manifest.json `
  --split test --model experiments/quasileak_laya/models/convaiinnovations__laya `
  --output-dir experiments/quasileak_laya/results/laya_base --device cuda

py experiments/quasileak_laya/scripts/evaluate_laya.py ... `
  --split test --model experiments/quasileak_laya/results/laya_finetuned `
  --output-dir experiments/quasileak_laya/results/laya_finetuned --device cuda --resume
```

The first evaluation should also be run on validation and passed to threshold calibration before the final test run.

## Qwen reference arms

Use the released builder and training script unchanged:

```powershell
py experiments/quasileak_laya/vendor/QuasiLeak-Bench/training/build_examples.py `
  --dataset experiments/quasileak_laya/vendor/QuasiLeak-Bench/data/quasileak_bench_data_full.jsonl `
  --out experiments/quasileak_laya/results/qwen_training

py experiments/quasileak_laya/scripts/train_qwen.py --model-id Qwen/Qwen3.5-4B `
  --train experiments/quasileak_laya/results/qwen_training/train_A.jsonl `
  --dev experiments/quasileak_laya/results/qwen_training/dev_A.jsonl `
  --out experiments/quasileak_laya/results/qwen_standard --merge
```

The augmented arm uses `train_B.jsonl`, one epoch as specified by the release. Qwen evaluation must use `prompts/render.py --shots 0`, greedy decoding, thinking disabled where supported, and the official scorer. The wrapper marks the run pending rather than silently changing these requirements.

## Kaggle

Attach the Finaira repository as a Kaggle dataset at `/kaggle/input/finaira-poc-4`, enable Internet, select a CUDA GPU (preferably 2×T4 for the Laya recipe), and run the notebook in `kaggle/quasileak_laya_experiment.ipynb`. It is resumable and writes all raw outputs under `/kaggle/working/finaira_quasileak_results`.

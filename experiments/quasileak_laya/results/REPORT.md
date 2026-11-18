# Current experiment report

## Status: PENDING_GPU

This report intentionally contains no fabricated model metrics. The machine used for this run has CPU-only PyTorch 2.10.0, four logical CPUs, about 20 GiB RAM, and no `nvidia-smi`. The Laya and Qwen model runs are therefore not complete.

## Completed locally

- Official QuasiLeak-Bench source pinned at `75987cdf029fac5fecce160bea218b458ed46dbb`.
- Official Laya source pinned at `d1282e791d71e92f24f816ff3836e4fd1c2ded4a`.
- Full dataset SHA-256 verified as `9af4c3e4fc59f664d124448e81e514012b8608bfa3ee6ba0faba9c6b9b27a965`.
- Official memberships verified: train 3,500; validation 500; test 1,000; profile counts 350/50/100; train/validation/test disjoint.
- Official row, policy, group-arity, and Unicode offset checks passed.
- Laya typed-decision training adapter rows built for all 3,500 train rows and 500 validation rows.
- Adapter unit tests: 9 passed.
- Official QuasiLeak tests: 164 passed, 3 terminal-rendering tests failed because the Windows/Rich rendering emitted square corners (`┌`) where the release test expects rounded corners (`╭`). No scorer/data failure was observed.

## Proposal audit

The validation adapter was run with 256 mined groups per document. It produced 128,000 groups, mean text span recall 13.0051%, mean all-group recall 49.6%, and zero hidden-group recalls across 500 validation rows under this bounded first implementation. This is a genuine proposal-stage limitation and is not presented as a Laya accuracy result. The training builder unions gold groups only for supervised train positives; validation/test proposals remain text-only.

An `oracle` candidate mode exists only to measure Laya's typed-choice stage separately. It is labelled `diagnostic_only` and must not be used as the primary detector result.

## Not measured yet

| Run | Status | Why |
|---|---|---|
| C0 original Laya | PENDING_GPU | no CUDA test pass |
| C1 QuasiLeak-fine-tuned Laya | PENDING_GPU | no CUDA fine-tuning |
| C2 standard Qwen3.5-4B LoRA | PENDING_GPU | no CUDA/BF16 training |
| C3 augmented Qwen3.5-4B LoRA | PENDING_GPU | no CUDA/BF16 training |
| same-hardware latency | PENDING_GPU | no GPU runtime |

The machine-readable table is `comparison.csv`; missing values are null by design.

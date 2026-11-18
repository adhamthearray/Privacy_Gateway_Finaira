# Laya discovery record

## Local repository audit

Finaira does not contain an Laya implementation, a Laya checkpoint, tokenizer, or QuasiLeak-Bench data. The only pre-existing local model code is the unrelated masked-LM multi-token completion experiment; it is not used here.

The isolated experiment vendors the official Laya source at:

- `vendor/laya/`
- commit `d1282e791d71e92f24f816ff3836e4fd1c2ded4a`
- package version in its `pyproject.toml`: `0.4.37`

The intended base checkpoint is `convaiinnovations/laya`. The official source describes it as a 421M-parameter ModernBERT-large encoder checkpoint. The typed-decision fine-tuning output is a new checkpoint produced by the official Laya training loop; it is not confused with the separately published `convaiinnovations/laya-typed-decisions` benchmark checkpoint.

## Architecture

Laya is not a causal language model. Its local source defines a bidirectional ModernBERT encoder and a typed decision head. A request supplies a state and a question map. The supported question types are:

- `choice`: select one of finite criteria;
- `score`: select an ordinal level;
- `noul`: return a calibrated probability for a yes/no statement.

The model returns structured answer dictionaries and never generates free-form evidence text. The exact model-side objects are visible in `vendor/laya/laya/common.py` (`DecisionModel`) and `vendor/laya/laya/agent.py` (`Agent.predict`/`predict_long`).

## QuasiLeak adaptation

The official task requires complete groups of 2–4 verbatim spans bound to a HIDE attribute. We therefore use a two-stage, architecture-compatible adapter:

1. A deterministic text-only proposal stage mines bounded n-gram spans and non-overlapping span groups. It has no access to gold annotations at inference.
2. Laya receives the authorized document, reference profile, policy, and each proposed group through a `choice` question: one hidden attribute or `NONE`.
3. Accepted choices are mapped back to the proposal's exact Unicode offsets/text and emitted as the official `evidence` JSON.

Training rows may union gold groups as supervised positives. Validation and test rows do not. Proposal span/group recall is measured separately because a scorer result cannot distinguish a missed proposal from a bad Laya decision.

This is a real adapter limitation to report, not a hidden use of gold annotations.

## Local capability

The current machine has Python 3.13, CPU-only PyTorch 2.10.0, four logical CPUs, about 20 GiB RAM, and no `nvidia-smi`. Full Laya/Qwen test inference, fine-tuning, and same-GPU latency comparison are therefore marked `PENDING_GPU`; no timing or accuracy numbers are invented.

## Official references

- Laya source: https://github.com/NandhaKishorM/laya
- Laya checkpoint: https://huggingface.co/convaiinnovations/laya
- QuasiLeak-Bench source: https://github.com/Yufannnn/QuasiLeak-Bench
- Qwen base candidate: https://huggingface.co/Qwen/Qwen3.5-4B

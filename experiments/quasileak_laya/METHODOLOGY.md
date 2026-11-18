# Methodology

## Evaluation identities

The experiment keeps these identities separate:

| ID | Meaning | Status locally |
|---|---|---|
| C0 | original `convaiinnovations/laya` | pending GPU/model download |
| C1 | Laya fine-tuned on QuasiLeak typed-decision rows | pending GPU |
| C2 | Qwen3.5-4B LoRA, official own-policy recipe A | pending GPU |
| C3 | Qwen3.5-4B LoRA, official augmented-policy recipe B | pending GPU |
| QWEN_PAPER_PUBLISHED | published reference accuracy only | reference-only; not local measurement |

No other model is substituted for Laya.

## Data protocol

The official full JSONL and `data/splits/split_manifest.json` are used. The primary held-out test is the 1,000-row `test` membership, not the convenience `quasileak_bench_data_1k.jsonl`. The official profile split is 350 train profiles, 50 validation profiles, and 100 test profiles, with disjoint profile IDs. The exact file hash and checks are in `results/dataset_audit.json` and `DATASET_AUDIT.md`.

The official renderer is retained for the Qwen baseline. It supplies document, reference profile, and HIDE/KEEP/NEUTRAL policy in the authors' format. Laya's adapter serializes the same authorized inputs as a structured state.

## Primary metrics

The unchanged official scorer is called for every completed run. It reports P-GP, P-GR, P-GF1, B-GF1, E-GF1, E_R, DSR, FAR, and prediction counts. P-GF1 is the primary metric. The adapter additionally records proposal span recall, proposal group recall, JSON/answer success, and failures.

Structural group recovery is not replaced with a binary SAFE/UNSAFE task. A prediction is only useful if it emits complete verbatim span groups bound to the correct HIDE attribute.

## Threshold and fairness

The default `answer_confidence` threshold is 0.55. Before a final test run, `calibrate_threshold.py` must sweep thresholds on validation only and freeze the selected value. The same threshold and candidate proposal configuration are then used by C0 and C1. If calibration is not run, the result is explicitly exploratory.

Laya uses greedy typed-choice decoding. C1 changes weights only; it does not get different candidates, a different test split, gold spans, or a post-hoc test threshold.

## Latency

`evaluate_laya.py` records per-document model and end-to-end latency with `time.perf_counter_ns()`, batch size 1 at the document level, and every candidate group question chunk. A production GPU pass should warm the model first, synchronize CUDA before/after timing, and record cold loading separately. The current CPU run cannot establish the requested GPU comparison.

Qwen timing uses the same test rows, order, batch size, concurrency, decoding cap, and hardware where possible. Published Qwen accuracy values never fill locally measured latency columns.

## Higher-order inference limitation

QuasiLeak-Bench evaluates released evidence groups. It does not by itself establish real-world re-identification risk. The official score and this adapter must not be described as anonymity proof. A later Finaira QI stress test may be reported separately, but it does not change the QuasiLeak scorer objective.

An optional oracle-candidate run is an upper-bound diagnostic: it supplies released gold groups to Laya, is marked `diagnostic_only`, and is never the primary test result. This separates typed-decision classification from the proposal stage without pretending that gold spans are available in deployment.

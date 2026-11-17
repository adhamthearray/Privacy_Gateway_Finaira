# Experiment results

## Environment

The playground was implemented as a local Gradio application with the
`BASELINE_MASKED_LM_BEAM_SEARCH` method. The default checkpoint is
`bert-base-multilingual-cased`; the checkpoint is loaded lazily and cached.
The official SS-MTC checkpoint was not available from the cited public paper
materials, so no official SS-MTC result is claimed.

## Verification performed

- The model module imports successfully with the repository's installed
  PyTorch and Transformers versions.
- The application builds without modifying Finaira production modules.
- Input validation covers missing documents, missing spans, occurrence
  selection, unsupported entity types, mask truncation, and invalid settings.
- The UI exposes English and Arabic samples, model/device controls, fixed and
  adaptive masking, candidate counts, JSON export, and deterministic DB
  comparison.
- Focused playground tests: **7 passed in 11.33s**.
- UI construction succeeded as a Gradio `Blocks` application.
- HTTP smoke test succeeded with `HTTP 200` on local port `7861`; port `7860`
  was already occupied by the existing Finaira UI.

## Observed local inference

The following runs were executed locally with the downloaded
`bert-base-multilingual-cased` checkpoint on CPU. They are examples of model
completion, not approved anonymization decisions:

| Language | Span | Masking | Latency | Top candidates |
| --- | --- | --- | ---: | --- |
| English | `National Bank of Egypt` | adaptive, 4 masks | 43,178.32 ms | `A. A.`; `A. B.` |
| Arabic | `البنك الأهلي المصري` | adaptive, 7 masks | 10,376.75 ms | `.......`; `:......` |

Both outputs carried `MODEL_OUTPUT_NOT_SEMANTICALLY_VALIDATED` and
`MODEL_SCORE_IS_NOT_PRIVACY_OR_UTILITY_CONFIDENCE`. The Arabic example is
intentionally retained as a limitation: the baseline can emit punctuation-like
or semantically unsuitable text, so the UI does not present it as safe or
production-ready.

The first uncached English run used the earlier unbatched implementation and
took 219,473.70 ms. The current implementation batches beam states per mask
step; the table above records the current code path.

When a checkpoint is unavailable, the UI reports the loading error and does
not fabricate candidates. Results vary with CPU/GPU, checkpoint cache, and
model version.


# Finaira POC4

This is a small, local-only privacy gateway. It accepts a document plus entity annotations, protects annotated spans, sends only the protected document to a deterministic mock LLM, validates the answer, and restores only exact pseudonyms.

## Run

```powershell
py -m pytest -q
```

The public entry point is `finaira.PrivacyPipeline`. Each entity should include `type`, `original_value` (or `value`), and character `start`/`end` spans. Stable upstream `entity_id` values are preferred. Without an ID, the adapter conservatively treats occurrences as separate identities.

Each pipeline run is appended as one JSON line to `logs/pipeline.log`, including its status, error code, and output. To use another location, pass `AuditLogger`:

```python
from finaira.audit import AuditLogger
pipeline = PrivacyPipeline(logger=AuditLogger("my-log.jsonl"))
```

For privacy-sensitive deployments, use `AuditLogger("logs/pipeline.log", include_output=False)` so only status and error information is recorded.

For full development tracing, use the separate debug logger:

```python
from finaira.debug_logger import DebugLogger
pipeline = PrivacyPipeline(logger=DebugLogger("logs/debug.log", print_console=True))
```

This prints and records every step, including the original input, mapping, sanitized document, sanitized response, validation, restored output, and cleanup. It is for local testing only because it exposes sensitive values.

Only `PSEUDONYMIZE`, `GENERALIZE`, and `ALLOW` are supported. The vault is memory-only, request-scoped, never sent to the mock LLM, and cleared in `finally` on every exit path. Generalized values (country, nationality, age, date, company, bank, government entity, occupation, and job title) are intentionally not reversible. `ORGANIZATION` and `UNIVERSITY` are canonicalized to `CORPORATION` before policy evaluation. Database-backed generalization uses the broadest verified available representation; unresolved, ambiguous, review-only, suppressed, or unavailable cases fall back to a request-scoped pseudonym.

The current POC supports English and basic Arabic age expressions/digits, ISO dates at six configurable levels, and a controlled nationality alias set in `finaira/generalization.py`. Unknown or ambiguous values fail safely; no external detector or LLM is used. The mock adapter can be tested with `MockLLM("invent")` or `MockLLM("leak")`.

Known limitations: the nationality data is intentionally compact rather than a complete 195-country production reference, localization is rule-based, and relationship/coreference validation is outside this minimal POC. Expand those data tables before production use.

To test Arabic without PowerShell encoding problems:

```powershell
py -X utf8 examples/test_arabic.py
```

The trace is saved to `logs/arabic-debug.log`.

Run all unit tests and multiple end-to-end examples with one command:

```powershell
py -X utf8 examples/run_all_tests.py
```

This runs English, Arabic, mixed-language, invalid-annotation, and—when `GEMINI_API_KEY` is set—real Gemini tests. Results are saved to `logs/test-suite.log`.

To use a real OpenAI model instead of the mock, set your key and model:

```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_MODEL = "gpt-5-mini"
```

Then construct the pipeline with `OpenAIResponsesLLM`:

```python
from finaira.llm import OpenAIResponsesLLM
pipeline = PrivacyPipeline(
    llm=OpenAIResponsesLLM(),
    logger=DebugLogger("logs/arabic-debug.log", print_console=True),
)
```

The real adapter sends only the system instructions, task, and protected document. It does not send the mapping vault or original values. The API key is read from `OPENAI_API_KEY` and never logged.

To use Gemini instead, set:

```powershell
$env:GEMINI_API_KEY = "your-gemini-key"
$env:GEMINI_MODEL = "gemini-3.1-flash-lite"
py -X utf8 examples/test_arabic.py
```

When `GEMINI_API_KEY` is present, the Arabic example uses Gemini automatically. The adapter calls Gemini's `generateContent` endpoint with the protected document only. Google documents the API-key header and `generateContent` request format in the [Gemini API documentation](https://ai.google.dev/api/generate-content).

You can also use a `.env` file:

```powershell
Copy-Item .env.example .env
notepad .env
py -X utf8 examples/test_arabic.py
```

Put your real `GEMINI_API_KEY` in `.env`. The file is ignored by Git and the key is never written to the debug log.

To print multiple documents with their original, sanitized, Gemini response, and reversed response:

```powershell
py -X utf8 examples/multiple_documents.py
```

The detailed trace is saved to `logs/multiple-documents.log`.

## Placeholder document policy package

For an upstream detector that has already replaced entity spans with
placeholders, run:

```powershell
py -X utf8 scripts/sanitize_document.py examples/document_sanitizer_input.json
```

The JSON output preserves the placeholder document and returns one decision
per entity. `PSEUDONYMIZE` entities receive a request-scoped form such as
`__FN_PERSON_0001__`. `GENERALIZE` entities receive the local database
candidate chain, including review status and `production_eligible`; no
generalization candidate is selected. Use `--hide-review-candidates` only
when a caller explicitly wants the gated candidates omitted.

For a browser drag-and-drop interface:

```powershell
py -X utf8 scripts/run_document_sanitizer_ui.py
```

Open `http://127.0.0.1:8766/`, drop the JSON file, and click `Return policy JSON`.
For a broader test, use `examples/document_sanitizer_challenging_sample.json`; it
includes repeated placeholders, Arabic and English values, a review-only bank,
an ambiguous date, an unknown corporation, an age, a job title, and a monetary
amount.

For the upstream-NER and downstream-JEV integration contract, see
`docs/ner_policy_jev_handoff.md` and run:

```powershell
py -X utf8 scripts/run_ner_policy_jev_gateway.py examples/ner_policy_jev_handoff_sample.json
```

Build the focused handoff ZIP for another developer:

```powershell
py -X utf8 scripts/create_ner_policy_jev_handoff_zip.py
```

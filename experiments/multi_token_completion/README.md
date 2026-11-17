# Finaira Multi-Token Completion Playground

This is a standalone experiment. It does not modify or call the production
sanitizer, policy gateway, JEV integration, or database mutating paths.

## What is implemented

The playground performs real local masked-language-model inference. It masks
the selected entity span and fills multiple mask positions with a small beam
search. It supports English and Arabic input, fixed or adaptive mask lengths,
CPU/CUDA selection, multiple candidates, repeated-span occurrence selection,
optional multi-entity mode, JSON export, and read-only comparison with
Finaira's deterministic candidates.

This is explicitly a **baseline**, not official SS-MTC. The EACL 2026 paper
describes SS-MTC as a Longformer-based method that expands the decoder
vocabulary with sensitive spans selected from Wikipedia and trains an EMAT
decoder. The public Amazon repository linked in the task is the earlier 2023
MTC implementation, not an SS-MTC checkpoint. The official 2026 checkpoint was
not available through the cited materials when this playground was built.

## Install and run

From the repository root:

```powershell
py -m pip install -r experiments/multi_token_completion/requirements.txt
py -X utf8 experiments/multi_token_completion/app.py
```

Open `http://127.0.0.1:7860`.
If that port is already used, set `FINAIRA_MTC_PORT`, for example:

```powershell
$env:FINAIRA_MTC_PORT=7861
py -X utf8 experiments/multi_token_completion/app.py
```

The first use downloads the selected Hugging Face checkpoint if it is not
already cached. All inference after download is local. No document is sent to
an external API.

The default checkpoint is `bert-base-multilingual-cased`. English-only
`bert-base-uncased` and custom checkpoint names are also supported. A model
must expose a masked-language-model head and mask token.

## Input and output

Enter the exact span as it appears in the document. If it appears more than
once, choose its 1-based occurrence. The generated table contains the model
replacement, rank, log score, reconstructed text, and explicit warnings.

The score ranks model outputs only. It is not a privacy, semantic, or utility
confidence. Consistency, breadth, and privacy safety are marked unverified
until a separate validator checks them.

Multi-entity mode accepts:

```json
[
  {"entity_id":"E0001","span":"Alice Smith","entity_type":"PERSON_NAME","occurrence":1},
  {"entity_id":"E0002","span":"National Bank of Egypt","entity_type":"BANK","occurrence":1}
]
```

The playground generates candidate lists independently. It does not perform
Cartesian-product optimization across entities.

## Limitations

- Ordinary masked-LM beam completion is not SS-MTC.
- The model may produce fluent but incorrect or identifying replacements.
- Arabic quality depends on the selected multilingual checkpoint.
- No automatic semantic validator or privacy approval is performed.
- The deterministic Finaira comparison is read-only and does not select or
  overwrite model outputs.


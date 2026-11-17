# NER → Policy → JEV handoff

This boundary connects an upstream NER service to the local Finaira database
and a downstream JEV selector. It is local and deterministic; it does not call
JEV or an external model.

## Input

The gateway accepts either one document or the batch envelope emitted by the
NER phase:

```json
{
  "total_documents": 1,
  "completed_documents": 1,
  "handoffs": [
    {
      "document_id": "doc-001",
      "text": "[[E0001]] emailed [[E0002]].",
      "entity_map": {
        "E0001": {
          "label": "PERSON_NAME",
          "original_text": "Alice Smith",
          "placeholder": "[[E0001]]"
        },
        "E0002": {
          "label": "EMAIL_ADDRESS",
          "original_text": "alice@example.com",
          "placeholder": "[[E0002]]"
        }
      }
    }
  ]
}
```

The placeholders must occur in `text`, and each entity must have `label`,
`original_text`, and `placeholder`.

## Policy output

Each handoff returns an entity decision containing:

- `policy_action`: configured action from `config/policy_actions.json`.
- `effective_action`: actual current result.
- `pseudonymization_form`: request-scoped counter token when needed.
- `generalization_candidates`: database or monetary options.
- `production_eligible`: whether a candidate may be sent to JEV.
- `generalization.selected_candidate`: always `null` before JEV.

If a generalizable entity has no production-eligible replacement, the adapter
keeps its candidates for audit and supplies a pseudonym fallback such as
`__FN_COUNTRY_0001__`.

## JEV handoff

The batch response contains:

```json
{
  "jev_handoff": {
    "protocol": "finaira-policy-to-jev-v1",
    "requests": [
      {
        "request_id": "doc-001:E0003",
        "document_id": "doc-001",
        "entity_id": "E0003",
        "entity_type": "COUNTRY",
        "source_entity_type": "COUNTRY",
        "value": "Egypt",
        "placeholder": "[[E0003]]",
        "document": "...",
        "policy_action": "GENERALIZE",
        "candidates": [],
        "selected_candidate": null
      }
    ],
    "selection_contract": {
      "selection_field": "candidate_id",
      "allowed_candidate_rule": "candidate.production_eligible == true",
      "no_selection_behavior": "retain pseudonymization fallback",
      "selector_must_not_invent_candidates": true
    }
  }
}
```

JEV returns a `candidate_id` only. The gateway validates that the ID belongs
to an eligible candidate before applying it:

```python
from finaira.integration import NERPolicyJEVGateway

gateway = NERPolicyJEVGateway()
prepared = gateway.prepare(ner_payload)
final = gateway.apply_jev_selections(
    prepared,
    {"doc-001:E0003": "candidate-id-returned-by-jev"},
)
```

No candidate text may be invented by JEV. If JEV does not select a candidate,
the fallback pseudonym remains in effect.

## Policy configuration

The default action table is in `config/policy_actions.json`. The three valid
actions are `ALLOW`, `GENERALIZE`, and `PSEUDONYMIZE`.

Per-request overrides can be supplied as a top-level `policy_overrides` object
or as an entity-level `policy_action`. An entity ID override takes precedence
over an entity-type override.

## Commands

Run the gateway against the included NER sample:

```powershell
py -X utf8 scripts/run_ner_policy_jev_gateway.py examples/ner_policy_jev_handoff_sample.json
```

Use a different policy table:

```powershell
py -X utf8 scripts/run_ner_policy_jev_gateway.py input.json --policy-config my_policy.json
```

The browser UI at `http://127.0.0.1:8766/` accepts this batch envelope as
well as a single document.


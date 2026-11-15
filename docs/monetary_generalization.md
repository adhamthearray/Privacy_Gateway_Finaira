# Monetary interpretation and three representations

`finaira_generalization.monetary` handles one entity that has already been
classified upstream as `MONETARY_AMOUNT`. It does not scan documents, run NER,
choose a representation, or invoke JEV.

## API

```python
from finaira_generalization import interpret_and_generalize_money

result = interpret_and_generalize_money(
    "١٢٫٥ ألف ريال سعودي",
    context={
        "locale": "ar-SA",
        "start": 10,
        "end": 31,
        "metadata": {"source": "ner"},
    },
)
```

The result always contains `interpretation` and all three keys under
`representations`:

```text
range_based
order_of_magnitude
task_aware_threshold
```

`Decimal` is used throughout. Exact amounts are serialized as strings, and
the original text, supplied offsets, and supplied metadata are retained.
Currency is optional. Missing currency produces `currency: null` and does not
block range or magnitude representations.

## Supported interpretation families

- Plain numeric values with grouping and decimal separators: `12500`,
  `12,500.75`, `12.500,75`, `12 500,75`, `١٢٬٥٠٠٫٧٥`, and `.75`.
- Abbreviations and scales: `12k`, `2.5mn`, `1.2bn`, `12 lakh`, `2 crore`,
  `١٢٫٥ ألف`, `٢٫٥ مليون`, and `٢٫٥ مليار`.
- English and Arabic written numbers, including compositions such as
  `twelve thousand five hundred`, `اثنا عشر ألفًا وخمسمائة`, `مليون ونصف`,
  and `مليار ومئتا مليون`.
- Fractions and mixed fractions: `½`, `2½`, `half a million`, and `نصف مليون`.
- Signs and accounting notation: `-500`, `+500`, `500-`, and `(500)`.
- Approximate values, ranges, and constraints: `about 5000`, `1000-5000`,
  `10k to 20k`, `1000 ± 100`, `>=10000`, `at least 10000`, and their Arabic
  equivalents.
- Scientific values: `1.2e6`, `3 × 10^6`, and `10^9` with exponent limits.
- Optional currencies, prioritizing EGP, SAR, AED, KWD, BHD, QAR, and OMR,
  plus common ISO codes and aliases. Major/minor-unit forms such as
  `12 riyals and 50 halalas`, `3 dinars and 125 fils`, and
  `٥ جنيهات و٢٥ قرشًا` use currency-specific minor-unit scales.

When a single separator and three trailing digits have multiple plausible
meanings, the parser returns `AMBIGUOUS_NUMBER` unless locale context resolves
the convention. For example, bare `1,234` is ambiguous while `1,234` with
`locale="en-US"` is interpreted as `1234`.

## Representations

### RANGE_BASED

Uses deterministic currency-neutral half-open nominal buckets:

```text
[0, 1000), [1000, 5000), [5000, 10000), [10000, 25000),
[25000, 50000), [50000, 100000), [100000, 500000), [500000, 1000000)
```

Values at or above the last boundary use an explicit overflow label. Negative
values use the corresponding signed interval. These are nominal numerical
intervals, not economic-risk or purchasing-power classifications.

### ORDER_OF_MAGNITUDE

Returns bilingual numerical-scale labels such as `Hundreds`, `Tens of
thousands`, `Millions`, `عشرات الآلاف`, and `الملايين`. Zero and values below
one have separate labels. Currency is appended only when known.

### TASK_AWARE_THRESHOLD

`threshold_spec` is optional and is never inferred:

```python
result = interpret_and_generalize_money(
    "12500",
    threshold_spec={"operator": ">", "threshold": "10000"},
)
```

Without a threshold, the result is:

```json
{"status": "REQUIRES_THRESHOLD", "en": null, "ar": null}
```

Supported operators are `>`, `>=`, `<`, `<=`, `=`, `!=`, `BETWEEN`, and
`OUTSIDE_RANGE`. Currency mismatch returns `CURRENCY_MISMATCH`; a currency on
only one side requires explicit `same_unit_context`. No foreign-exchange
conversion is performed. Approximate values are indeterminate, while ranges
can return `TRUE` or `FALSE` when their known bounds prove the comparison.

The lower-level helper is also available:

```python
from finaira_generalization import generalize_threshold

generalize_threshold("12500", ">", "10000")
```

## Status and safety behavior

The interpretation status distinguishes `SUCCESS`, `AMBIGUOUS_NUMBER`,
`UNKNOWN_CURRENCY`, `CURRENCY_CONFLICT`, `INVALID_NUMBER`,
`UNSUPPORTED_PATTERN`, and `INVALID_ENTITY_TYPE`. Non-exact amounts retain
their qualifier and do not receive an exact range or magnitude representation.
All three representation objects remain present, with `UNAVAILABLE`,
`INDETERMINATE`, or `REQUIRES_THRESHOLD` when a safe output cannot be formed.

The module does not modify `finaira` policy behavior or automatically replace
monetary entities in the privacy pipeline.


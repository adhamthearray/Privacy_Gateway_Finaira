# Arabic nationality inflection policy v1

This policy is used only during offline review of the supplied NER nationality queue. It is not a runtime fuzzy matcher and it does not create aliases by itself.

## Allowed derivations

1. Remove one leading Arabic definite article `ال` when the remainder exactly matches the normalized verified Wikidata `P1549` base.
2. Remove one masculine sound plural ending `ين` or `ون` after the definite article or directly from the corpus form when the remainder exactly matches the verified base.
3. Remove one feminine ending `ة` when the remainder exactly matches the verified base.
4. Apply only the repository's existing conservative normalization for Arabic diacritics, hamza/alef variants, final alef-maqsura/ya, and ta-marbuta/ha spelling variants. These spelling equivalences are approved individually and are never enabled as a new global rewrite.

## Required evidence

Every approved queue row must point to a line in the versioned `data/sources/wikidata/wikidata_nationality_aliases_ar_en_v2.csv` where the base alias is attached to the same QID and has `source_property=wdt:P1549`. The approval reference also records the source SHA-256, this policy ID, the derivation rule, and the Natural Earth join status.

## Not allowed

- Arbitrary suffix stripping, fuzzy matching, transliteration guesses, or country-name-to-nationality conversion.
- Approving context-sensitive adjectives without NER-context review.
- Approving malformed/truncated spans.
- Treating an unresolved Natural Earth join as permission to invent regional candidates. Exact nationality resolution may remain available with an `EXACT_ONLY` limitation.
- Enabling aliases with a missing QID, collision, missing evidence, or unresolved review decision.

# Quality report

Structural validation is automated by `scripts/validate_semantics.py`. The pilot contains 144 prompts and 1440 complete entity-type decisions. Grouped splitting keeps all translations, three relevance task flips, and ten type decisions for a scenario together.

Synthetic labels are suggestions only. Official Laya exports contain 0 rows because no human approval has occurred. Semantic naturalness, especially Egyptian Arabic and code-switching, remains a human-review obligation. Duplicate findings are recorded without deleting source data. Baseline and model metrics remain blocked until approved gold labels exist.

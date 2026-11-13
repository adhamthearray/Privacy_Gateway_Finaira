FINAIRA NATIONALITY HANDOFF

1. Copy nationality_adjudication_plan.csv and CODEX_NATIONALITY_REVIEW_AND_DB_IMPORT.md to a folder Codex can read in your Finaira repo.
2. In Codex: "Read CODEX_NATIONALITY_REVIEW_AND_DB_IMPORT.md and implement it against the existing nationality_variant_review_queue.csv."
3. The CSV is a decision *plan* for the user's 82 pasted suggestion rows / 74 unique values, NOT a set of preapproved mappings. Its review_decision column remains PENDING by design.
4. Codex must verify against the actual original source row, Arabic rule, context, and normalized collisions before changing APPROVED/importing to SQLite.

This handoff does not modify your Windows repo or your local SQLite database directly.

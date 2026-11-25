# Research summary

The implemented method combines ontology-first specification (NLU++), multilingual semantic alignment and localization (MASSIVE and ArBanking77), narrow banking confusions (BANKING77), out-of-scope construction (CLINC150), synthetic generation with filtering rather than auto-approval (Self-Instruct), controlled complexity transformations (Evol-Instruct), rationale-aware human review (ERASER), and Laya's documented hard-label JSONL interface.

The resulting pilot is intentionally not a gold benchmark. It is a deterministic review queue with leakage-safe group assignments and an append-only annotation system. See `RESEARCH_FOUNDATIONS.md` for source-by-source limitations, provenance, and licensing notes.


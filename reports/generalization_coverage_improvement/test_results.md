# Test results

Baseline before the current improvement pass: `py -m pytest -q` — 21 passed in 17.12s.

Final verification: `py -X utf8 -m pytest -q` — 24 passed in 16.39s.

The added regression coverage checks:

- Natural Earth country aliases are source-verified and linked to the country resolver.
- COUNTRY and NATIONALITY remain separate runtime entity paths.
- Ambiguous date formats are rejected unless an explicit format is supplied.
- All 11 permitted entity types expose candidates, while `PERSON_NAME` remains unsupported.
- Bank counts/classification/evidence and disclosure flags remain unchanged.
- Organization approval gating, government review gating, unknown fallbacks, FK integrity, and idempotent handoff imports remain green.

Database integrity after import: `PRAGMA integrity_check = ok`; `PRAGMA foreign_key_check` returned zero rows.

Remaining provisional areas are intentionally visible in `alias_review_queue.csv`: Arabic bank names lack official evidence in the supplied master, organization identities remain pending, government seeds remain review-only, most corpus job-title/occupation strings are not exact ESCO aliases, unresolved Natural Earth joins remain unresolved, and ambiguous dates require format context.

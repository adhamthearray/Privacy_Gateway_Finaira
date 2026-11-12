# Test results

## Before integration

`py -m pytest -q` → 15 passed in 17.38s.

## After integration

`py -m pytest -q` → 20 passed in 15.42s.

Additional checks:

- `validate-levels` → PASS, no cycles or missing parents.
- `PRAGMA foreign_keys` → 1.
- `PRAGMA integrity_check` → `ok`.
- `PRAGMA foreign_key_check` → no rows.
- Second `import-handoff --no-backup` → COMPLETED with unchanged source/candidate counts.

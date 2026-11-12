# Finaira bilingual generalization engine

This repository contains an offline SQLite/SQLAlchemy reference database and deterministic candidate API beside the existing privacy POC.

Import the supplied handoff with:

```powershell
py -X utf8 -m finaira_generalization.cli import-handoff
py -X utf8 -m pytest -q
```

The current database contains 3,018 ESCO occupations, 1,149 ISCO groups, 848 Wikidata nationality aliases joined to Natural Earth Admin-0 1:10m v5.1.1, 37 banks, 312 pending organization candidates, and 12 review-only government seeds. Source checksums, Natural Earth join audits, candidate coverage, and schema exports are under `reports/`.

Legacy M49 tables remain for historical compatibility, but live nationality retrieval uses `nationality_aliases_v2` and `nationality_geo_joins` backed by Natural Earth. Unmatched or mismatched QIDs never receive guessed regions.

Examples:

```powershell
py -X utf8 -m finaira_generalization.cli candidates --type OCCUPATION --value "technical director" --language en
py -X utf8 -m finaira_generalization.cli candidates --type BANK --value "Banque Misr" --language en
py -X utf8 -m finaira_generalization.cli candidates --type NATIONALITY --value "Egyptian" --language en
```

Runtime does not call an LLM or the network. Unknown and ambiguous values return explicit status and safe generic/suppression candidates; they never echo the original as a generalized representation.

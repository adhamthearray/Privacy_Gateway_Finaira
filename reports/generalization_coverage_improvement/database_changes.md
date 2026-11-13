# Database changes and provenance

Database: `data/processed/finaira_generalization.db`

Backup created before the import work: `data/processed/finaira_generalization_backup_20261113_150509.db`.

Changes in this improvement pass:

- Added `natural_earth_country_aliases` with a stable primary key, Natural Earth foreign key, source foreign key, normalized alias/language uniqueness, verification status, and lookup enablement.
- Imported 2,174 deduplicated Arabic/English Wikidata country labels and aliases linked to Natural Earth by QID. Raw source CSV: `data/sources/wikidata/wikidata_country_aliases_ar_en_v1.csv`.
- Imported 59 reviewed nationality aliases from 67 approved derivation/evidence rows. Pending and rejected rows remain disabled; provenance is stored in `nationality_alias_review_provenance`.
- Imported 31 reviewed current-country variants through the existing handoff importer, deduplicated to 30 enabled `REVIEWED` runtime aliases. Historical, ambiguous, non-country, and malformed values remain suppressed.
- Kept NATIONALITY demonyms separate in `nationality_aliases_v2`; country labels do not become nationality aliases.
- Rebuilt country runtime lookup to use source-backed aliases, Natural Earth names, and validated ISO A2 only. No guessed regional labels are created.
- Added deterministic DATE parsing for ISO/year-first values, unambiguous day-first values, Arabic digits, and caller-supplied `date_format`. Ambiguous numeric dates remain rejected.
- Regenerated the NER-v1 audit and country review queue. The country queue contains 86 baseline gaps; the final audit retains 55 suppressed COUNTRY values covering 105 spans. Review queues are not imported unless explicitly approved.

Current high-level counts: 258 Natural Earth countries; 2,204 country aliases (2,174 source-verified plus 30 reviewed); 239 nationality QIDs; 857 source nationality aliases plus 59 reviewed variants; 37 banks; 3018 occupations; 36,992 occupation aliases; 312 organizations; 12 government seed entities.

The handoff importer is additive, transactional, idempotent, and uses stable IDs. `PRAGMA integrity_check` is `ok`, and `PRAGMA foreign_key_check` returns no rows after the final import.

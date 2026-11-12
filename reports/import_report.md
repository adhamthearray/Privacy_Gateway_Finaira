# Import report

The authoritative report for the 2026-11-12 handoff import is `handoff_import_report.json`.

- Natural Earth Admin-0 1:10m v5.1.1: 258 rows; 223 QID matches, 2 guarded ISO matches, 1 mismatch, 7 unresolved.
- Wikidata nationality aliases: 848 rows and 233 distinct QIDs.
- Banks: 37 (24 conventional, 9 mixed, 4 Islamic); 24 evidence rows; 185 regenerated candidates.
- Organizations: 312 pending identity candidates; 73 industry concept links; 63 bilingual source categories; 6 exclusions.
- Government: 12 review-required seeds; 17 bilingual categories; 63 review-only catalog rows.

All imported sources are checksum-stamped in `data_sources`. Reference-only government denormalized CSV was not ingested.

The old `import-all`/M49 report is historical and is not the active nationality path.

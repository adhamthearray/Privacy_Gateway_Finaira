# GCC bank audit migration report

Generated: 2026-11-14T21:50:53.754597+00:00

- **dry_run**: false
- **database**: "C:\\Users\\domma\\poc_4\\data\\processed\\finaira_generalization.db"
- **source_dir**: "C:\\Users\\domma\\poc_4\\data\\sources\\bank\\gcc_2026"
- **master_rows**: 266
- **alias_rows**: 1487
- **model_counts**: {"CONVENTIONAL": 175, "HISTORICAL": 16, "ISLAMIC": 43, "ISLAMIC_WINDOW": 5, "NOT_APPLICABLE": 7, "SPECIALIZED": 4, "UNKNOWN": 16}
- **review_action_counts**: {"ALIAS_ONLY_HISTORICAL": 16, "CHECK_CBB_ENTITY_LICENSE": 57, "DO_NOT_IMPORT_AS_LICENSED": 14, "DO_NOT_TREAT_AS_OPERATING": 3, "DUPLICATE_RECONCILIATION": 2, "EXCLUDE_FROM_LICENSED_BANK_COUNT": 1, "IMPORT_MODEL_WITH_CAUTION": 16, "IMPORT_WITH_2026_RECHECK": 21, "IMPORT_WITH_ENTITY_NOTE": 4, "IMPORT_WITH_LICENSE_CLASS": 84, "IMPORT_WITH_MODEL_SOURCE": 35, "LINK_TO_PARENT_BANK": 5, "REVERIFY_CURRENT_2026": 1, "SEPARATE_FROM_COMMERCIAL_BANKS": 6, "VERIFY_BANK_MODEL": 1}
- **unrecognized_review_actions**: []
- **duplicate_candidates**: [{"canonical_record_id": "BH-197", "source_record_id": "BH-241"}]
- **existing_bank_records_before**: 302
- **new_records_created**: 0
- **records_matched_existing**: 266
- **aliases_preserved_before**: 1569
- **new_aliases_imported**: 0
- **alias_rows_skipped**: 0
- **alias_duplicates_collapsed**: 2
- **parent_relationships_created**: 5
- **unresolved_parent_relationships**: []
- **license_status_counts**: {"CONFIRMED": 94, "HISTORICAL": 16, "LINKED_WINDOW": 5, "NOT_APPLICABLE": 7, "PROVISIONAL": 29, "RECHECK_REQUIRED": 40, "UNVERIFIED": 75}
- **operational_status_counts**: {"ACTIVE_LISTED": 94, "ACTIVE_REQUIRES_REVIEW": 138, "HISTORICAL": 16, "LICENSED_NOT_OPERATIONAL": 3, "LICENSE_UNVERIFIED": 14, "REQUIRES_2026_RECHECK": 1}
- **licensed_count_eligible**: 94
- **manual_review_records**: 149
- **aliases_preserved_after**: 1569

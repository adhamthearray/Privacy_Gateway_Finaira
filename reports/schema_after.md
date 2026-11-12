# Schema after layered migration

## `age_bands`

Rows: 7

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| band_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `age_bands`. |
| scheme | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `age_bands`. |
| min_age | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `age_bands`. |
| max_age | INTEGER |  | YES |  | Persisted Finaira reference data or layered metadata for `age_bands`. |
| label_ar | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `age_bands`. |
| label_en | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `age_bands`. |

## `age_scheme_rules`

Rows: 7

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| scheme_id | VARCHAR(80) | PK | NO | generalization_schemes.scheme_id | Persisted Finaira reference data or layered metadata for `age_scheme_rules`. |
| band_id | INTEGER | PK | NO | age_bands.band_id | Persisted Finaira reference data or layered metadata for `age_scheme_rules`. |

## `bank_aliases`

Rows: 86

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| bank_id | VARCHAR(30) |  | NO | banks.bank_id | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| alias_kind | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| review_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| enabled_for_lookup | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_aliases`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `bank_aliases`. |

Indexes: ix_bank_aliases_bank_id, ix_bank_aliases_language, ix_bank_aliases_normalized_alias

## `bank_candidates`

Rows: 185

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(120) | PK | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| bank_id | VARCHAR(30) |  | NO | banks.bank_id | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| level_code | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| specificity_rank | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| finance_model | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| category_population_count | INTEGER |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| is_exact | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| is_local_only | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| is_suppression | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| disclosure_approved | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| evidence_status | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| verification_status | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `bank_candidates`. |
| derivation_method | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_candidates`. |

Indexes: ix_bank_candidates_bank_id, ix_bank_candidates_level_code

## `bank_evidence`

Rows: 24

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| evidence_id | VARCHAR(80) | PK | NO |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| bank_id | VARCHAR(30) |  | NO | banks.bank_id | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| finance_model | VARCHAR(20) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| source_type | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| source_url | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| evidence_summary_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| source_publication_or_update | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| checked_on | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| source_strength | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| notes | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `bank_evidence`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `bank_evidence`. |

Indexes: ix_bank_evidence_bank_id

## `banks`

Rows: 37

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| bank_id | VARCHAR(30) | PK | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| cbe_list_number | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `banks`. |
| name_en | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| name_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `banks`. |
| finance_model | VARCHAR(20) |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| finance_model_label_en | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| finance_model_label_ar | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| classification_rule | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| evidence_status | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `banks`. |
| evidence_confidence | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `banks`. |
| as_of_date | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `banks`. |
| evidence_review_status | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `banks`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `banks`. |

Indexes: ix_banks_finance_model

## `build_metadata`

Rows: 1

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| key | TEXT | PK | YES |  | Persisted Finaira reference data or layered metadata for `build_metadata`. |
| value | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `build_metadata`. |

## `candidate_metadata`

Rows: 8609

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(160) | PK | NO | generalization_candidates.candidate_id | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| specificity_rank | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| taxonomy_depth | INTEGER |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| underlying_category_count | INTEGER |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| is_exact | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| is_suppression | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| is_local_only | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| preserves_exact_value | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| preserves_category | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| preserves_entity_identity | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| preserves_numeric_precision | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| representation_kind | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| verification_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| interval_start | VARCHAR(40) |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| interval_end | VARCHAR(40) |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |
| interval_width | INTEGER |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_metadata`. |

## `candidate_provenance`

Rows: 8609

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| provenance_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| candidate_id | VARCHAR(160) |  | NO | generalization_candidates.candidate_id | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| source_id | INTEGER |  | YES | data_sources.source_id | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| source_version | VARCHAR(100) |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| source_checksum | VARCHAR(64) |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| derivation_method | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| validation_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| review_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| review_date | VARCHAR(40) |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |
| notes | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `candidate_provenance`. |

Indexes: ix_candidate_provenance_candidate_id

## `countries`

Rows: 248

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| iso2 | VARCHAR(2) | PK | NO |  | Persisted Finaira reference data or layered metadata for `countries`. |
| country_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| country_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| m49_code | VARCHAR(3) |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| subregion_code | VARCHAR(3) |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| subregion_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| subregion_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| region_code | VARCHAR(3) |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| region_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |
| region_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `countries`. |

## `country_m49_links`

Rows: 248

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| iso2 | VARCHAR(2) | PK | NO | countries.iso2 | Persisted Finaira reference data or layered metadata for `country_m49_links`. |
| subregion_code | VARCHAR(3) |  | YES | m49_regions.code | Persisted Finaira reference data or layered metadata for `country_m49_links`. |
| region_code | VARCHAR(3) |  | YES | m49_regions.code | Persisted Finaira reference data or layered metadata for `country_m49_links`. |

## `data_sources`

Rows: 22

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| source_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| name | VARCHAR(200) |  | NO |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| version | VARCHAR(100) |  | YES |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| source_url | VARCHAR(500) |  | YES |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| retrieved_at | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| license | VARCHAR(300) |  | YES |  | Persisted Finaira reference data or layered metadata for `data_sources`. |
| checksum | VARCHAR(64) |  | YES |  | Persisted Finaira reference data or layered metadata for `data_sources`. |

## `date_rules`

Rows: 3

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| rule_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `date_rules`. |
| precision | VARCHAR(20) |  | NO |  | Persisted Finaira reference data or layered metadata for `date_rules`. |
| calendar | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `date_rules`. |
| enabled | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `date_rules`. |

## `date_scheme_rules`

Rows: 3

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| scheme_id | VARCHAR(80) | PK | NO | generalization_schemes.scheme_id | Persisted Finaira reference data or layered metadata for `date_scheme_rules`. |
| rule_id | INTEGER | PK | NO | date_rules.rule_id | Persisted Finaira reference data or layered metadata for `date_scheme_rules`. |

## `generalization_candidates`

Rows: 8609

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(160) | PK | NO |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| scheme_id | VARCHAR(80) |  | NO | generalization_schemes.scheme_id | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| level_id | INTEGER |  | NO | generalization_levels.level_id | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| canonical_entity_id | VARCHAR(300) |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| taxonomy_code | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| parent_candidate_id | VARCHAR(160) |  | YES | generalization_candidates.candidate_id | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| source_id | INTEGER |  | YES | data_sources.source_id | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| review_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| derivation_method | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |
| created_at | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_candidates`. |

Indexes: ix_generalization_candidates_canonical_entity_id, ix_generalization_candidates_level_id, ix_generalization_candidates_parent_candidate_id, ix_generalization_candidates_scheme_id, ix_generalization_candidates_taxonomy_code

## `generalization_levels`

Rows: 30

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| level_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| scheme_id | VARCHAR(80) |  | NO | generalization_schemes.scheme_id | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| level_code | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| specificity_rank | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| description | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| representation_kind | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| is_exact | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| is_suppression | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |
| default_local_only | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_levels`. |

Indexes: ix_generalization_levels_scheme_id

## `generalization_schemes`

Rows: 6

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| scheme_id | VARCHAR(80) | PK | NO |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| entity_type | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| scheme_name | VARCHAR(120) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| taxonomy_name | VARCHAR(80) |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| taxonomy_version | VARCHAR(40) |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| description | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| source_id | INTEGER |  | YES | data_sources.source_id | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |
| enabled | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `generalization_schemes`. |

Indexes: ix_generalization_schemes_entity_type

## `government_aliases`

Rows: 24

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| entity_id | VARCHAR(30) |  | NO | government_entities.entity_id | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| enabled_for_lookup | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| source_url | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_aliases`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_aliases`. |

Indexes: ix_government_aliases_entity_id, ix_government_aliases_language, ix_government_aliases_normalized_alias

## `government_candidate_reviews`

Rows: 63

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(100) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| entity_id | VARCHAR(30) |  | NO | government_entities.entity_id | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| level_code | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| dimension | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| specificity_rank_branch_local | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| source_url | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| requires_policy_approval | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| is_local_only | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| is_suppression | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| default_visible | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_candidate_reviews`. |

Indexes: ix_government_candidate_reviews_dimension, ix_government_candidate_reviews_entity_id

## `government_categories`

Rows: 17

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| category_code | VARCHAR(50) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_categories`. |
| label_ar | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `government_categories`. |
| label_en | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `government_categories`. |
| parent_category_code | VARCHAR(50) |  | YES | government_categories.category_code | Persisted Finaira reference data or layered metadata for `government_categories`. |
| reidentification_risk_hint | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_categories`. |
| status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_categories`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_categories`. |

Indexes: ix_government_categories_parent_category_code

## `government_entities`

Rows: 12

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| entity_id | VARCHAR(30) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| name_ar | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| name_en_provisional | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| country_iso | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| organization_form_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| function_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| wikidata_qid | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| official_source_url | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| identity_verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| function_verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| english_name_verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| enabled_for_specific_mapping | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| dataset_status | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| review_notes | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `government_entities`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_entities`. |

Indexes: ix_government_entities_country_iso, ix_government_entities_identity_verification_status

## `government_entity_categories`

Rows: 24

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| link_id | VARCHAR(100) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |
| entity_id | VARCHAR(30) |  | NO | government_entities.entity_id | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |
| category_code | VARCHAR(50) |  | NO | government_categories.category_code | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |
| dimension | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |
| verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_entity_categories`. |

Indexes: ix_government_entity_categories_category_code, ix_government_entity_categories_entity_id

## `government_review_queue`

Rows: 12

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| review_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| entity_id | VARCHAR(30) |  | NO | government_entities.entity_id | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| review_identity | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| review_current_status | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| review_function_category | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| review_english_name | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| review_wikidata_qid | VARCHAR(30) |  | YES |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| specific_mapping_enabled | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `government_review_queue`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `government_review_queue`. |

Indexes: ix_government_review_queue_entity_id

## `import_batches`

Rows: 1

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| batch_id | VARCHAR(100) | PK | NO |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| started_at | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| completed_at | VARCHAR(40) |  | YES |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| manifest_path | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| counts_json | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `import_batches`. |
| error_text | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `import_batches`. |

## `industry_categories`

Rows: 64

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| category_code | VARCHAR(50) | PK | NO |  | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| parent_code | VARCHAR(50) |  | YES | industry_categories.category_code | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| label_en | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| label_ar | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| category_kind | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| license | VARCHAR(100) |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_categories`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `industry_categories`. |

Indexes: ix_industry_categories_parent_code

## `industry_qid_mappings`

Rows: 73

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| mapping_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| industry_qid | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| source_industry_label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| sector_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| subcategory_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| subcategory_label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| subcategory_label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| review_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `industry_qid_mappings`. |

Indexes: ix_industry_qid_mappings_industry_qid, ix_industry_qid_mappings_review_status, ix_industry_qid_mappings_sector_code, ix_industry_qid_mappings_subcategory_code

## `isco_groups`

Rows: 1149

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| isco_code | VARCHAR(4) | PK | NO |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |
| parent_code | VARCHAR(4) |  | YES |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |
| level | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |
| arabic_label_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `isco_groups`. |

Indexes: ix_isco_groups_parent_code

## `m49_regions`

Rows: 23

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| code | VARCHAR(3) | PK | NO |  | Persisted Finaira reference data or layered metadata for `m49_regions`. |
| parent_code | VARCHAR(3) |  | YES | m49_regions.code | Persisted Finaira reference data or layered metadata for `m49_regions`. |
| level | INTEGER |  | NO |  | Persisted Finaira reference data or layered metadata for `m49_regions`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `m49_regions`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `m49_regions`. |

Indexes: ix_m49_regions_parent_code

## `nationality_alias_country_refs`

Rows: 833

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | INTEGER | PK | NO | nationality_aliases.alias_id | Persisted Finaira reference data or layered metadata for `nationality_alias_country_refs`. |
| iso2 | VARCHAR(2) |  | NO | countries.iso2 | Persisted Finaira reference data or layered metadata for `nationality_alias_country_refs`. |

Indexes: ix_nationality_alias_country_refs_iso2

## `nationality_aliases`

Rows: 844

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| country_iso2 | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |
| review_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases`. |

Indexes: ix_nationality_aliases_country_iso2, ix_nationality_aliases_language, ix_nationality_aliases_normalized_alias

## `nationality_aliases_v2`

Rows: 848

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_key | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| country_qid | VARCHAR(20) |  | NO | nationality_countries.country_qid | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| iso2 | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |
| verification_status | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_aliases_v2`. |

Indexes: ix_nationality_aliases_v2_country_qid, ix_nationality_aliases_v2_iso2, ix_nationality_aliases_v2_language, ix_nationality_aliases_v2_normalized_alias

## `nationality_candidate_refs`

Rows: 248

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(160) | PK | NO | generalization_candidates.candidate_id | Persisted Finaira reference data or layered metadata for `nationality_candidate_refs`. |
| iso2 | VARCHAR(2) |  | NO | countries.iso2 | Persisted Finaira reference data or layered metadata for `nationality_candidate_refs`. |

Indexes: ix_nationality_candidate_refs_iso2

## `nationality_countries`

Rows: 233

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| country_qid | VARCHAR(20) | PK | NO |  | Persisted Finaira reference data or layered metadata for `nationality_countries`. |
| iso2 | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_countries`. |
| country_label | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `nationality_countries`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `nationality_countries`. |
| verification_status | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_countries`. |

Indexes: ix_nationality_countries_iso2

## `nationality_geo_joins`

Rows: 233

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| country_qid | VARCHAR(20) | PK | NO | nationality_countries.country_qid | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| iso2 | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| natural_earth_id | VARCHAR(40) |  | YES | natural_earth_countries.natural_earth_id | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| join_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| match_method | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| audit_note | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `nationality_geo_joins`. |

Indexes: ix_nationality_geo_joins_iso2, ix_nationality_geo_joins_join_status, ix_nationality_geo_joins_natural_earth_id

## `natural_earth_countries`

Rows: 258

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| natural_earth_id | VARCHAR(40) | PK | NO |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| wikidata_qid | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| iso_a2 | VARCHAR(2) |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| name_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| name_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| subregion | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| region_un | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| continent | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |
| source_version | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `natural_earth_countries`. |

Indexes: ix_natural_earth_countries_iso_a2, ix_natural_earth_countries_wikidata_qid

## `occupation_aliases`

Rows: 36992

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | INTEGER | PK | NO |  | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| occupation_id | VARCHAR(300) |  | NO | occupations.occupation_id | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |
| review_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `occupation_aliases`. |

Indexes: ix_occupation_aliases_language, ix_occupation_aliases_normalized_alias, ix_occupation_aliases_occupation_id

## `occupation_candidate_refs`

Rows: 6036

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| candidate_id | VARCHAR(160) | PK | NO | generalization_candidates.candidate_id | Persisted Finaira reference data or layered metadata for `occupation_candidate_refs`. |
| occupation_id | VARCHAR(300) |  | NO | occupations.occupation_id | Persisted Finaira reference data or layered metadata for `occupation_candidate_refs`. |

Indexes: ix_occupation_candidate_refs_occupation_id

## `occupation_isco_refs`

Rows: 3018

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| occupation_id | VARCHAR(300) | PK | NO | occupations.occupation_id | Persisted Finaira reference data or layered metadata for `occupation_isco_refs`. |
| isco_code | VARCHAR(4) |  | NO | isco_groups.isco_code | Persisted Finaira reference data or layered metadata for `occupation_isco_refs`. |
| source_id | INTEGER |  | YES | data_sources.source_id | Persisted Finaira reference data or layered metadata for `occupation_isco_refs`. |

Indexes: ix_occupation_isco_refs_isco_code

## `occupations`

Rows: 3018

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| occupation_id | VARCHAR(300) | PK | NO |  | Persisted Finaira reference data or layered metadata for `occupations`. |
| label_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `occupations`. |
| label_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `occupations`. |
| isco_code | VARCHAR(4) |  | YES |  | Persisted Finaira reference data or layered metadata for `occupations`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `occupations`. |
| review_status | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `occupations`. |

Indexes: ix_occupations_isco_code

## `organization_aliases`

Rows: 566

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| alias_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| organization_qid | VARCHAR(20) |  | NO | organizations.organization_qid | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| alias_text | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| normalized_alias | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| language | VARCHAR(2) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| enabled_for_lookup | BOOLEAN |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_aliases`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `organization_aliases`. |

Indexes: ix_organization_aliases_language, ix_organization_aliases_normalized_alias, ix_organization_aliases_organization_qid

## `organization_exclusions`

Rows: 6

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| exclusion_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| organization_qid | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| name_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| name_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| reason | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| import_decision | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `organization_exclusions`. |

Indexes: ix_organization_exclusions_organization_qid

## `organization_industries`

Rows: 360

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| link_id | VARCHAR(100) | PK | NO |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| organization_qid | VARCHAR(20) |  | NO | organizations.organization_qid | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| mapping_id | VARCHAR(64) |  | YES | industry_qid_mappings.mapping_id | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| industry_qid | VARCHAR(40) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| sector_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| subcategory_code | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| mapping_status | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| import_decision | VARCHAR(70) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `organization_industries`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `organization_industries`. |

Indexes: ix_organization_industries_industry_qid, ix_organization_industries_mapping_id, ix_organization_industries_organization_qid

## `organization_review_queue`

Rows: 42

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| review_id | VARCHAR(64) | PK | NO |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| organization_qid | VARCHAR(20) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| import_status | VARCHAR(50) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| review_flags | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| import_decision | VARCHAR(70) |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| review_reason | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `organization_review_queue`. |

Indexes: ix_organization_review_queue_organization_qid

## `organizations`

Rows: 312

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| organization_qid | VARCHAR(20) | PK | NO |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| name_en | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| name_ar | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| semantic_kind | VARCHAR(30) |  | NO |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| identity_verification_status | VARCHAR(50) |  | NO |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| import_decision | VARCHAR(70) |  | NO |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| import_status | VARCHAR(70) |  | YES |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| review_flags | TEXT |  | YES |  | Persisted Finaira reference data or layered metadata for `organizations`. |
| source_id | INTEGER |  | NO | data_sources.source_id | Persisted Finaira reference data or layered metadata for `organizations`. |

Indexes: ix_organizations_identity_verification_status, ix_organizations_import_decision, ix_organizations_semantic_kind

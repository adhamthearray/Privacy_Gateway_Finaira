# Schema before layered migration

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

## `build_metadata`

Rows: 0

| Column | Type | Key | Nullable | References | Purpose |
|---|---|---|---|---|---|
| key | TEXT | PK | YES |  | Persisted Finaira reference data or layered metadata for `build_metadata`. |
| value | TEXT |  | NO |  | Persisted Finaira reference data or layered metadata for `build_metadata`. |

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

## `data_sources`

Rows: 5

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

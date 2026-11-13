# Generalization architecture

The runtime is a read-only candidate API. It resolves an entity type and normalized alias, applies source/verification gates, then returns every permitted candidate. It does not rank, select, pseudonymize, call an LLM, or perform runtime fuzzy matching.

```mermaid
flowchart TD
  A[NER span] --> B{One of 11 permitted types?}
  B -- no --> X[Remain outside generalization]
  B -- yes --> C[Unicode/Arabic normalization]
  C --> D{Typed resolver}
  D --> E[Source-backed exact alias]
  D --> F[Verified hierarchy / generic fallback]
  D --> G[Review-only or suppression]
  E --> H[Candidate objects]
  F --> H
  G --> H
  H --> I[Caller receives candidates; selected_candidate remains null]
```

```mermaid
erDiagram
  DATA_SOURCES ||--o{ NATURAL_EARTH_COUNTRIES : sources
  NATURAL_EARTH_COUNTRIES ||--o{ NATURAL_EARTH_COUNTRY_ALIASES : identifies
  NATIONALITY_COUNTRIES ||--o{ NATIONALITY_ALIASES_V2 : identifies
  NATURAL_EARTH_COUNTRIES ||--o{ NATIONALITY_GEO_JOINS : joins
  BANKS ||--o{ BANK_ALIASES : has
  BANKS ||--o{ BANK_CANDIDATES : materializes
  ORGANIZATIONS ||--o{ ORGANIZATION_ALIASES : has
  ORGANIZATIONS ||--o{ ORGANIZATION_INDUSTRIES : links
  GOVERNMENT_ENTITIES ||--o{ GOVERNMENT_ALIASES : has
  OCCUPATIONS ||--o{ OCCUPATION_ALIASES : has
  GENERALIZATION_SCHEMES ||--o{ GENERALIZATION_LEVELS : defines
  GENERALIZATION_LEVELS ||--o{ GENERALIZATION_CANDIDATES : materializes
```

The complete actual SQLite inventory, columns, foreign keys, indexes, and DDL are in `reports/schema_after.md`, `reports/database_schema.sql`, and `reports/database_erd.mmd`.

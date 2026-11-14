# Production JOB_TITLE database inventory

Database: `data\processed\finaira_generalization.db`

- Canonical occupations: **3,018**
- Aliases: **36,992**
- English aliases: **33,249**
- Arabic aliases: **3,743**
- Enabled aliases: **36,992**

`job_title_taxonomy.csv` is one row per canonical ESCO occupation. `job_title_aliases.csv` is the full lookup inventory, one row per alias, including language, ISCO code, review status, and source provenance. Language-specific copies are `job_title_aliases_en.csv` and `job_title_aliases_ar.csv`.

The runtime accepts `OCCUPATION` as a compatibility input but exposes all records as canonical `JOB_TITLE`.
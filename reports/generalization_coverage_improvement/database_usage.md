# Database usage

Run from the repository root:

```powershell
py -X utf8 -m finaira_generalization.cli candidates --type COUNTRY --value "Egypt" --language en
py -X utf8 -m finaira_generalization.cli candidates --type NATIONALITY --value "Egyptian" --language en
py -X utf8 -m finaira_generalization.cli candidates --type BANK --value "Banque Misr" --language en
py -X utf8 -m finaira_generalization.cli candidates --type DATE --value "03/04/2026" --language en --date-format "%d/%m/%Y"
py -X utf8 scripts/audit_ner_generalization_coverage.py --dataset C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1 --db data\processed\finaira_generalization.db --output reports\generalization_coverage_improvement
py -X utf8 -m finaira_generalization.cli show-schema
py -X utf8 -m pytest -q
```

```python
from finaira_generalization import GeneralizationDB

db = GeneralizationDB("data/processed/finaira_generalization.db")
country = db.get_candidates("COUNTRY", "Egypt", "en")
nationality = db.get_candidates("NATIONALITY", "Egyptian", "en")
date = db.get_candidates(
    "DATE", "03/04/2026", "en", context={"date_format": "%d/%m/%Y"}
)
for result in (country, nationality, date):
    for candidate in result["candidates"]:
        print(candidate["level_code"], candidate["representation"], candidate["source"], candidate["verification_status"])
```

```sql
SELECT a.alias_text, a.language, c.name_en, c.iso_a2, a.verification_status
FROM natural_earth_country_aliases AS a
JOIN natural_earth_countries AS c ON c.natural_earth_id = a.natural_earth_id
WHERE a.enabled_for_lookup = 1
ORDER BY a.language, a.alias_text;

SELECT b.finance_model, COUNT(*) AS banks
FROM banks AS b
GROUP BY b.finance_model;

SELECT o.organization_qid, o.identity_verification_status, o.import_decision,
       oi.industry_qid, oi.verification_status
FROM organizations AS o
LEFT JOIN organization_industries AS oi ON oi.organization_qid = o.organization_qid
WHERE o.import_decision NOT IN ('VERIFIED', 'APPROVED');
```

# finaira_ner_v1 generalization coverage audit

This report compares every distinct value in the supported generalization labels against the local SQLite database. Percentages are reported by unique value and by annotated span frequency.

Categories: `MATCHED_OR_VERIFIED` is production source/configuration coverage; `REVIEW_ONLY` is present but gated; `AMBIGUOUS` has a collision; `GENERIC_FALLBACK_ONLY` has a safe generic candidate but no exact identity; `SUPPRESSION_ONLY` has no usable non-suppression candidate; `OUT_OF_SCOPE` is not a current database entity type.

| Entity | Unique | Spans | Matched/verified | Review | Ambiguous | Generic fallback | Suppression/invalid | Out of scope |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BANK | 73 | 869 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 73 (100.00%) | 0 (0.00%) | 0 |
| COUNTRY | 229 | 3,009 | 143 (62.45%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 86 (37.55%) | 0 |
| NATIONALITY | 115 | 607 | 41 (35.65%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 74 (64.35%) | 0 |
| CORPORATION | 1,516 | 6,083 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 1,516 (100.00%) | 0 (0.00%) | 0 |
| ORGANIZATION | 0 | 0 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| UNIVERSITY | 0 | 0 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| GOVERNMENT_ENTITY | 870 | 4,221 | 0 (0.00%) | 8 (0.92%) | 0 (0.00%) | 862 (99.08%) | 0 (0.00%) | 0 |
| JOB_TITLE | 2,214 | 9,444 | 19 (0.86%) | 0 (0.00%) | 1 (0.05%) | 0 (0.00%) | 2,194 (99.10%) | 0 |
| OCCUPATION | 236 | 472 | 2 (0.85%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 234 (99.15%) | 0 |
| AGE | 97 | 595 | 97 (100.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| DATE | 2,823 | 5,937 | 2,233 (79.10%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 590 (20.90%) | 0 |

## Highest-frequency gaps

### BANK

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| البنك الأهلي المصري | 113 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك التجاري الدولي | 98 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك مصر | 94 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الرياض | 80 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| مصرف الراجحي | 52 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الأهلي | 46 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الأهلي السعودي | 32 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الاهلي السعودي | 21 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| الراجحي | 20 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الأهلي | 16 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| مصرف الرياض | 16 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الإسكندرية | 13 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الاهلي | 13 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك السعودي للاستثمار | 12 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الخليج | 11 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |

### COUNTRY

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| دولة فلسطين | 16 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| يمن | 15 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| بريطانيا | 10 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| الاتحاد السوفيتي | 9 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| مغرب | 8 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| المملكة الأردنية | 8 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| ولايات المتحدة | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| جزائر | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| نابلس | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| دولة الإمارات | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| UK | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| KSA | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| الأراضي الفلسطينية | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| بحرين | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| السلطنة | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |

### NATIONALITY

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| الفلسطيني | 32 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينيين | 31 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| السوريين | 17 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| اللبناني | 13 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينية | 11 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| اليمنيين | 11 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينيون | 9 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| فلسطينيين | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الإسرائيليين | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| العراقيين | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| عراقيين | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| المصريين | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الأردنيين | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الليبيين | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| بريطانيين | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |

### CORPORATION

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| شركة الحلول الذكية | 84 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة البناء الحديث | 70 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة العقارات المتحدة | 66 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الاتصالات المصرية | 53 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الحلول المتقدمة | 52 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الاتصالات السعودية | 51 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| مؤسسة البناء الحديث | 48 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة النخبة للمقاولات | 45 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الأفق | 45 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة النخبة للتجارة | 38 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| مؤسسة النخبة | 37 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الفهد للمقاولات | 36 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الأفق للمقاولات | 29 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركه العقارات المتحده | 28 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |
| شركة الوفاء للمقاولات | 28 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_ORGANIZATION | review organization identity and alias |

### GOVERNMENT_ENTITY

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| المرور | 359 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| الجوازات | 312 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزارة الصحة | 284 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| مرور | 117 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزاره الصحه | 95 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| الجمارك | 89 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزارة التجارة | 86 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| بلدية مدينة البيرة | 85 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| جوازات | 74 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| هيئة سوق رأس المال | 73 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزارة الداخلية | 68 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| هيئة سوق رأس المال الفلسطينية | 55 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| الشرطة | 41 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزاره الداخليه | 38 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |
| وزارة التعليم | 37 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_GOVERNMENT_ENTITY | review government identity and alias |

### JOB_TITLE

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| مدير الموارد البشرية | 310 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| سكرتير اللجنة القومية العربية في نابلس | 282 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المدير المالي | 271 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| رئيس اللجنة | 226 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| رئيس بلدية نابلس | 211 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المدير التنفيذي | 210 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مدير المشروع | 126 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مدير القسم | 119 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مدير المبيعات | 119 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مدير الموارد البشريه | 117 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مدير الفرع | 90 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| رئيس بلدية بيرزيت | 79 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مديرة المدرسة | 75 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| رئيس بلدية مدينة البيرة | 74 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المدير المباشر | 66 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |

### OCCUPATION

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| المذيع | 24 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المهندس | 15 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| الموظف | 12 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| مبرمج | 11 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| القاضي | 9 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المحامي | 9 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| قاضٍ | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| طالب | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| الأستاذ الدكتور | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المبرمج | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| طالبة | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| الصحفي | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| جندي | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| الحلاق | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |
| المعلم | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_OCCUPATION | add verified ESCO/ISCO alias |

### DATE

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| 08/02/1997 | 8 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 11/03/1970 | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| ٠١/١٠/١٩٩٤ | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 03-01-1982 | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 07-12-1945 | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 08/10/1994 | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| ٠٢/١٢/١٩٥٠ | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 07-06-2006 | 7 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| ١٠/٠٩/١٩٦٠ | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 08-03-1976 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 01-09-1999 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 01/10/1980 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 05/02/1962 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 05-05-2007 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |
| 03/06/1951 | 6 | INVALID_OR_UNRESOLVED | AMBIGUOUS_DATE | validate input format or source evidence |

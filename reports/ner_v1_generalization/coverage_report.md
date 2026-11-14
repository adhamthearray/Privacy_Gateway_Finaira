# finaira_ner_v1 generalization coverage audit

This report compares every distinct value in the supported generalization labels against the local SQLite database. Percentages are reported by unique value and by annotated span frequency.

Categories: `MATCHED_OR_VERIFIED` is production source/configuration coverage; `REVIEW_ONLY` is present but gated; `AMBIGUOUS` has a collision; `GENERIC_FALLBACK_ONLY` has a safe generic candidate but no exact identity; `SUPPRESSION_ONLY` has no usable non-suppression candidate; `OUT_OF_SCOPE` is not a current database entity type.

| Entity | Unique | Spans | Matched/verified | Review | Ambiguous | Generic fallback | Suppression/invalid | Out of scope |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BANK | 73 | 869 | 10 (13.70%) | 0 (0.00%) | 0 (0.00%) | 63 (86.30%) | 0 (0.00%) | 0 |
| COUNTRY | 229 | 3,009 | 174 (75.98%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 55 (24.02%) | 0 |
| NATIONALITY | 115 | 607 | 100 (86.96%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 15 (13.04%) | 0 |
| CORPORATION | 1,516 | 6,083 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 1,516 (100.00%) | 0 (0.00%) | 0 |
| ORGANIZATION | 0 | 0 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| UNIVERSITY | 0 | 0 | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| GOVERNMENT_ENTITY | 870 | 4,221 | 0 (0.00%) | 8 (0.92%) | 0 (0.00%) | 862 (99.08%) | 0 (0.00%) | 0 |
| JOB_TITLE | 2,442 | 9,916 | 268 (10.97%) | 0 (0.00%) | 8 (0.33%) | 2,166 (88.70%) | 0 (0.00%) | 0 |
| AGE | 97 | 595 | 97 (100.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 |
| DATE | 2,823 | 5,937 | 2,233 (79.10%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 590 (20.90%) | 0 |

## Highest-frequency gaps

### BANK

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| بنك الرياض | 80 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| مصرف الراجحي | 52 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الأهلي | 46 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الأهلي السعودي | 32 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الاهلي السعودي | 21 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| الراجحي | 20 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الأهلي | 16 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| مصرف الرياض | 16 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك الاهلي | 13 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك السعودي للاستثمار | 12 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الخليج | 11 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| Riyad Bank | 10 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| Saudi National Bank | 10 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| البنك العربي الوطني | 9 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |
| بنك الراجحي | 9 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_BANK | verify and add bank alias |

### COUNTRY

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| بريطانيا | 10 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| الاتحاد السوفيتي | 9 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| نابلس | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| KSA | 6 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| الأراضي الفلسطينية | 5 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| السلطنة | 4 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| مملكة | 3 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| جنوب اليمن | 3 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| نيجريا | 3 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| بغداد | 3 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| بالمنطقة المغاربية | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| روما | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| إمارات العربية المتحدة | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| UAE | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |
| واشنطن | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_COUNTRY | verify Natural Earth/Wikidata country alias or ISO mapping |

### NATIONALITY

| Value | Spans | Category | Reason | Next action |
|---|---:|---|---|---|
| الفلسطيني | 32 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينيين | 31 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينية | 11 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| فلسطينيين | 7 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الروسية | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| اللبنانيي | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| يبيين | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الأميركي | 2 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| لجيكيين | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الأميركيين | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الفلسطينيه | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| الإريتريين | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| اميركي | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| لبنانيي | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |
| أميركي | 1 | SUPPRESSION_ONLY | UNRECOGNIZED_NATIONALITY | add verified Wikidata P1549 demonym if available |

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
| رئيس اللجنة | 226 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس بلدية نابلس | 211 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| المدير التنفيذي | 210 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| مدير المشروع | 126 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| مدير الفرع | 90 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس بلدية بيرزيت | 79 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس بلدية مدينة البيرة | 74 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| المدير المباشر | 66 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس المجلس | 65 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| الرئيس | 62 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| مندوب المبيعات | 57 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| قائمقام رام الله | 55 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| مدير المشاريع | 54 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس القسم | 49 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |
| رئيس اللجنه | 46 | GENERIC_FALLBACK_ONLY | UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK | add verified alias |

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

# Independent job-title and occupation benchmark

This benchmark is separate from the Finaira NER corpus. It measures the existing JOB_TITLE resolver against external occupational title inventories and does not import any title into the production database.

## Source status

```json
{
  "onet_job_titles": {
    "status": "LOADED",
    "path": "C:\\Users\\domma\\Downloads\\finaira_benchmark_sources\\onet31_job_titles.csv",
    "sha256": "75a3b46d6edc5996117c10c9ed488c9a06f7495d02969e9d12873ab14a21540c",
    "rows": 54269
  },
  "onet_reported_titles": {
    "status": "LOADED",
    "path": "C:\\Users\\domma\\Downloads\\finaira_benchmark_sources\\onet31_sample_of_reported_titles.csv",
    "sha256": "5d76040b7b0602ea217660648f8363e7980edd1870f96574a2eeaa6a822d2666",
    "rows": 8189
  },
  "bls_direct_match_titles": {
    "status": "NOT_PROVIDED"
  },
  "capmas_titles": {
    "status": "NOT_PROVIDED"
  },
  "egypt_occupational_outlook": {
    "status": "NOT_PROVIDED"
  },
  "asco_titles": {
    "status": "NOT_PROVIDED"
  }
}
```

## Coverage

| Source | Language | Unique | Exact/normalized | Phrase candidate | Ambiguous | Generic fallback | Exact + phrase |
|---|---|---:|---:|---:|---:|---:|---:|
| ONET_JOB_TITLE | en | 44,779 | 3,880 (8.66%) | 12,883 | 10,288 | 17,728 | 16,763 (37.43%) |
| ONET_REPORTED_TITLE | en | 7,041 | 1,260 (17.90%) | 1,902 | 1,610 | 2,269 | 3,162 (44.91%) |

## Interpretation

`VERIFIED_EXACT_OR_NORMALIZED` means the external title is already covered by an official/reviewed ESCO alias in the current database. `LONGEST_PHRASE_CANDIDATE` means only a contiguous phrase inside the external title matched and must not be counted as exact coverage. `AMBIGUOUS` must not be promoted without context. `GENERIC_FALLBACK_ONLY` is usable for safe generalization but is not evidence that the occupation was recognized.

The O*NET and BLS sources are English and therefore test breadth independently of the Arabic NER corpus. CAPMAS and ASCO inputs are supported as Arabic CSVs when the official files are supplied. No missing source is silently replaced by another source.
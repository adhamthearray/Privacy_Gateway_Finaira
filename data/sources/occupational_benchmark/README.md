# Independent occupational benchmark sources

These files are benchmark inputs, not production generalization aliases. They
must never be imported into `occupation_aliases` without separate source
verification and approval.

The benchmark currently uses O*NET 31.0 files downloaded on 2026-11-14:

- `https://www.onetcenter.org/dl_files/database/db_31_0_csv/job_titles.csv`
- `https://www.onetcenter.org/dl_files/database/db_31_0_csv/sample_of_reported_titles.csv`

The BLS 2018 Direct Match Title File, CAPMAS Unified Occupational
Classification, Egypt Occupational Outlook export, and ASCO 2008 are supported by the benchmark script but were
not silently substituted when the current environment could not download them.
Provide their local CSV/XLSX files with the corresponding CLI options.

Run:

```powershell
py -3 scripts/benchmark_job_occupation_coverage.py `
  --onet-job-titles C:\path\job_titles.csv `
  --onet-reported-titles C:\path\sample_of_reported_titles.csv
```

The report is written to `reports/job_occupation_benchmark/`.

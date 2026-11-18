# QuasiLeak-Bench dataset audit

Status: **PASS**

This audit uses the released full corpus and the repository's released profile-disjoint manifest. It does not create a new split.

## Dataset identity

- Documents: 5000
- Profiles: 500
- Contexts: 20
- Groups: 9099
- Cues/spans: 23041
- Distractors: 12237
- SHA-256 observed: `9af4c3e4fc59f664d124448e81e514012b8608bfa3ee6ba0faba9c6b9b27a965`
- SHA-256 expected by metadata: `9af4c3e4fc59f664d124448e81e514012b8608bfa3ee6ba0faba9c6b9b27a965`

## Released membership

| view | rows | profiles |
|---|---:|---:|
| train | 3500 | 350 |
| validation | 500 | 50 |
| test | 1000 | 100 |
| subset_non_revealing | 1618 | paired/see manifest |
| policy_shift | 500 | paired/see manifest |
| sft_policy_shift | 500 | paired/see manifest |

- Train/validation/test profile-disjoint: **True**
- Missing membership IDs: `{'train': 0, 'validation': 0, 'test': 0, 'subset_non_revealing': 0, 'policy_shift': 0, 'sft_policy_shift': 0, 'smoke_train': 0}`

## Validation checks

- Row and offset checks: **True** (0 errors)
- Offsets are interpreted as half-open Unicode code-point offsets, as required by the release.
- The 1,000-row convenience subset is not used as QLB-Test.

## License

The benchmark data are CC BY-NC-SA 4.0. The vendored source code is MIT. Keep the data separate from model redistribution and retain attribution.


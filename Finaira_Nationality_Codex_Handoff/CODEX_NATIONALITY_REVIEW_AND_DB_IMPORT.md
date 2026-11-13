# CODEX TASK — FIN AIRA NATIONALITY VARIANTS: REVIEW, VERIFY, IMPORT, TEST

## Objective / authorization

In the existing `C:\Users\domma\poc_4` repository, branch `POC_4`, finish the **NATIONALITY-only** exact-alias expansion based on the user's supplied review queue. **Make the warranted code and database changes**, not just a plan. Do not auto-approve merely because a user-supplied row points to a QID. No other entity type, JEV, or pseudonymization changes.

## Files

1. Existing, authoritative repository queue: `reports/nationality_improvement/nationality_variant_review_queue.csv`.
2. Attached advisory adjudication plan: `nationality_adjudication_plan.csv` (74 unique `corpus_value` strings). Place both handoff files in a reachable repository folder, e.g. `reports/nationality_improvement/assistant_review/`, and read them.
3. Current implementation: `scripts/build_nationality_variant_review.py`, `finaira_generalization/candidates.py`, `handoff.py`, `db.py`, `normalization.py`, `scripts/refresh_wikidata_nationalities.py`, test files and any relevant repository documentation.
4. Dataset: `C:\Users\domma\Downloads\finaira_ner_v1\finaira_ner_v1`.

**The advisory CSV is NOT an approved-alias import file.** `review_decision=PENDING` in every row on purpose. It reflects an analysis of the user's pasted rows, NOT independently signed-off original P1549 records or individual context. Read its `recommended_action` and apply the evidence gates below.

## Actual analysis of pasted rows

- 82 source suggestion rows; 74 distinct corpus strings; 8 duplicate derivation pairs. The 74 unique frequencies sum to 270 spans.
- Reported baseline is 41/115 nationality values and 337/607 spans resolved. Thus 74/115 values and 270/607 spans were unresolved. The pasted suggestions *appear to cover the entire unresolved portion*, but confirm with the current version of the actual repository queue, dataset split, and audit.
- Group 1: `VERIFY_RULE_THEN_APPROVE`: 55 unique corpus strings; 241 spans. These have a stated Wikidata P1549 base + QID and plausible definite-article/masculine-plural transformations. **Not yet approved.** Verify the exact base, QID, and Arabic transformation with source-backed P1549 row and reviewed rules; check normalized collisions and that the corpus span is indeed NATIONALITY. When all conditions pass, you are authorized to update the authoritative queue `review_decision=APPROVED` with a REAL evidence reference, then import.
- Group 2: `CHECK_SPELLING_EQUIVALENCE`: 8 unique strings, 11 spans. Verify explicit spelling equivalences and collisions. Do not enable a global Arabic normalization rewrite just for these. Approve individually only with independent evidence or justified, tested, narrow orthographic equivalence. Values: `الاردني`, `الاسرائيليين`, `الاسترالي`, `الافغاني`, `الامريكى`, `الامريكية`, `الفرنسى`, `الفلسطينيه`.
- Group 3: `CHECK_CORPUS_CONTEXT`: `السورية` (4 spans). The candidate `Q858` is plausible, but the adjective/country sense can be context-dependent. Inspect actual NER contexts and original annotations. Keep pending if ambiguous. A NER tag alone is not independent proof of canonical nationality.
- Group 4: `HOLD_FIND_INDEPENDENT_SOURCE`: 6 unique strings, 8 spans. `الأميركي`, `أميركي`, `الأميركيين`, `اميركي`, `الروسية`, `الإريتريين`. The pasted queue deliberately supplies no unique source-backed QID. Do NOT fill those QIDs based on your language-model knowledge. Look for independently attested Arabic demonym aliases and country-QID linkage, plus context review where appropriate. Only then add an explicit reviewed candidate proposal and an evidence reference; otherwise keep PENDING. `الروسية` requires extra sense/annotation review.
- Group 5: `HOLD_MALFORMED_SPAN`: 4 unique strings, 6 spans. `اللبنانيي`, `لبنانيي`, `يبيين`, `لجيكيين`. Likely truncated/malformed annotations, but verify in JSONL source context and token offsets. Do not insert truncated strings as production nationality aliases just to improve coverage. Record annotation-boundary issues; leave unresolved unless credible evidence establishes the literal as a valid nationality form.
- Some source rows for `العراقيون`, `اليمنيون`, `الأمريكيون`, `السعوديون`, `السعوديين`, `الإسرائيليون`, `الإماراتيون`, and `اللبنانيون` appear twice due to different `base_alias` paths, **all pointing to the same QID**. Collapse to one eventual enabled alias per `(language, normalized corpus value, canonical country)` while preserving *both* derivation paths in audit/provenance. Use the shortest verifiable path as the primary source. Never sum `span_count` twice.
- France `Q142` appears in the supplied review queue with blank `candidate_iso2`. Expected ISO alpha-2 is `FR` (must validate from your trusted country reference and Natural Earth join before filling). A missing ISO field is not grounds for dropping a valid QID; don't invent other country joins.

## Verification gates (all mandatory before `APPROVED`)

A. Confirm the original `base_alias` appears in the actual versioned Arabic Wikidata P1549 source row under exactly the candidate country QID; store entity/source version and source reference (a QID wiki page alone without verifying the P1549 statement is not sufficient).

B. Derivation must be *exactly* reproducible: definite article `ال`, masculine sound plurals `ون/ين`, optional diacritic handling, or independently justified orthography. Reverse transformation must terminate at the verified base alias. Don't use arbitrary suffix stripping or broad fuzzy matching. Do not auto-generate or approve other unattested strings at runtime.

C. Verify QID ↔ nationality country record ↔ Natural Earth join status, QID-first. If join unresolved/mismatched, don't fabricate region candidates; exact alias resolution may be separate from region availability but report clearly.

D. Normalize conservatively and test collisions across countries. One normalized input matching multiple distinct QIDs is `AMBIGUOUS`, never `APPROVED` for default identity resolution.

E. Check the literal word against sampled source sentence(s), especially `السورية` and other adjectives. Wrong-tag annotations must not be 'fixed' by inventing an alias.

F. Add a real, inspectable `evidence_reference` for each approved row (e.g. a versioned source row reference plus an Arabic grammar derivation policy in repository documentation, and corroboration for nonregular forms). Don't use fake URLs, vague strings, or only the NER dataset as identity evidence.

G. Alias is enabled only after *all* checks. Keep human-review-only/ambiguous rows disabled, with explanatory `review_notes`. Do not treat bulk syntactic suggestions as automatically verified just because they look familiar.

## How to implement

1. Confirm branch and clean/dirty worktree; preserve unrelated changes. Do baseline tests, a backup of SQLite, and a frozen per-split audit. Establish current truth rather than assuming pasted snapshot is current.
2. Crosswalk the advisory CSV to the original review queue by literal `corpus_value`, `language`, and `candidate_qid` where present. For duplicate derivations, preserve originals and select one canonical approved alias, not duplicate inserts. Missing suggested QIDs remain missing until separately evidenced.
3. Verify source and Arabic morphological rules once in a versioned policy document, then apply each candidate with explicit per-row proof/collision checks. Default on any uncertainty: `PENDING`/`REVIEW_ONLY`; never silently approve.
4. Set `review_decision=APPROVED` and real `evidence_reference` *only for rows passing all checks* in authoritative queue. Preserve approval decisions on queue regeneration. If the importer expects some other status, adapt to the actual tested importer contract; do not bypass gating.
5. Run the **existing** importer (adapt if required only after inspecting CLI):
   `py -X utf8 -m finaira_generalization.cli import-handoff`
6. Verify approved rows arrive as reviewed production nationality aliases, not as source-verified original Wikidata P1549 aliases. Preserve provenance: `WIKIDATA_P1549_BASE + REVIEWED_ARABIC_INFLECTION` (or repo equivalent). Exact original values remain local-only; geographic candidates only if the country's Natural Earth join and bilingual labels are present.
7. Assert byte-for-byte idempotent mapping counts after two imports, no duplicate canonical aliases, no broken FKs, no disabled alias leaking into production, no accidental changes to COUNTRY or other types. Check collisions against existing runtime aliases and across QIDs.
8. Run targeted and whole-suite tests, including `get_candidates('NATIONALITY','الفلسطينيين',output_language='ar')`, `السوريين`, `اللبناني`, `المصريين`, `العراقيون`, `الامريكى`, `السورية`, malformed `اللبنانيي`, `لجيكيين`, and an unchanged English baseline. Test default `include_review_candidates=False` and explicit review mode. Verify nonexistent input retains safe fallback.
9. Re-run the coverage audit by split, reporting *unique strings* and *spans* without double counting; split verified, review-only, malformed/invalid, generic fallback, and unresolved. Original whole-corpus audit may contain held-out test rows: if so, don't claim new test numbers as untouched generalization. Preserve original audit reports.
10. Deliver actual file-by-file changes, approved/rejected/pending counts with reasons, before/after unique and span coverage, 10 representative resolved mappings with evidence, 10 unresolved cases if any, SQL queries verifying rows and source IDs, test commands/output, and Git commit hash if committed. Do not push unless normal repo workflow authorizes it. Flag missing internet/source access rather than fabricating evidence.

## Explicit expected outcomes

**Potential only (NOT promised):** If all 55 routine forms pass review and they are truly all new unmatched values, we would go from 41 to 96 distinct matches of 115 (83.48%) and from 337 to 578 of 607 spans (95.22%). This is not guaranteed. The remainder of 29 spans across 19 forms require additional orthographic/context/source/annotation work. A higher coverage number is NOT a license to add unverifiable aliases.

Do not alter `BANK`, `COUNTRY`, `CORPORATION`, `GOVERNMENT_ENTITY`, `JOB_TITLE`, `OCCUPATION`, `AGE`, `DATE`, `ORGANIZATION`, `UNIVERSITY`, JEV, or pseudonymization code, except read-only checks of shared references and necessary minimally-scoped normalization/regression tests. No runtime fuzzy matching. No invented country mappings.

## Final instructions

You are authorized to **perform verification, make defensible approval decisions when evidenced, edit the existing review queue, import into the existing SQLite DB, test, and document**. Do not stop with a proposal. If you cannot verify an individual mapping, leave it disabled and explain why.

"""Read-only, deterministic candidate lookup across all supported domains."""

from __future__ import annotations

import calendar
import re
from datetime import date
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .age_date import parse_age
from .db import (
    Bank, BankAlias, BankAuditClassification, BankCandidate, BankRelationship, CandidateMetadata, DataSource,
    BankIdentityModel, BankModelAlias, BankGeneralizationCohort, BankGeneralizationForm, BankDoNotMerge,
    GeneralizationCandidate, GeneralizationLevel, GovernmentAlias,
    GovernmentCandidateReview, GovernmentEntity, IndustryQIDMapping,
    NationalityAlias, NationalityAliasV2, NationalityGeoJoin,
    NationalityCountry, NaturalEarthCountry, NaturalEarthCountryAlias, Organization, OrganizationAlias,
    OrganizationExclusion, OrganizationIndustry, OccupationAlias, make_engine,
)
from .layers import stable_id
from .normalization import normalize

AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

BANK_MODEL_FORM_LABELS = {
    "CONVENTIONAL": ("Conventional bank", "\u0628\u0646\u0643 \u062a\u0642\u0644\u064a\u062f\u064a"),
    "MIXED": ("Bank offering conventional and Islamic banking services", "\u0628\u0646\u0643 \u064a\u0642\u062f\u0645 \u062e\u062f\u0645\u0627\u062a \u0645\u0635\u0631\u0641\u064a\u0629 \u062a\u0642\u0644\u064a\u062f\u064a\u0629 \u0648\u0625\u0633\u0644\u0627\u0645\u064a\u0629"),
    "ISLAMIC": ("Islamic bank", "\u0628\u0646\u0643 \u0625\u0633\u0644\u0627\u0645\u064a"),
    "ISLAMIC_WINDOW": ("Bank with an Islamic window", "\u0628\u0646\u0643 \u0630\u0648 \u0646\u0627\u0641\u0630\u0629 \u0625\u0633\u0644\u0627\u0645\u064a\u0629"),
    "SPECIALIZED": ("Specialized or development bank", "\u0628\u0646\u0643 \u0645\u062a\u062e\u0635\u0635 \u0623\u0648 \u062a\u0646\u0645\u0648\u064a"),
    "UNKNOWN": ("Unknown banking model", "\u0646\u0645\u0648\u0630\u062c \u0645\u0635\u0631\u0641\u064a \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641"),
    "HISTORICAL": ("Historical or undetermined banking model", "\u0646\u0645\u0648\u0630\u062c \u0645\u0635\u0631\u0641\u064a \u062a\u0627\u0631\u064a\u062e\u064a \u0623\u0648 \u063a\u064a\u0631 \u0645\u062d\u062f\u062f"),
    "HISTORICAL_UNDETERMINED": ("Historical or undetermined banking model", "\u0646\u0645\u0648\u0630\u062c \u0645\u0635\u0631\u0641\u064a \u062a\u0627\u0631\u064a\u062e\u064a \u0623\u0648 \u063a\u064a\u0631 \u0645\u062d\u062f\u062f"),
    "NOT_APPLICABLE": ("Not a bank", "\u0644\u064a\u0633 \u0628\u0646\u0643\u064b\u0627"),
    "NOT_A_BANK": ("Not a bank", "\u0644\u064a\u0633 \u0628\u0646\u0643\u064b\u0627"),
}


@dataclass
class Candidate:
    candidate_id: str
    level_code: str
    specificity_rank: int
    representation: str | None
    language: str
    taxonomy: str | None
    taxonomy_code: str | None
    source: str | None
    verification_status: str
    metadata: dict
    available: bool = True
    missing_reason: str | None = None

    def to_dict(self):
        value = asdict(self)
        meta = value["metadata"]
        value.update({"label_en": meta.get("label_en"), "label_ar": meta.get("label_ar"), "dimension": meta.get("dimension"), "is_exact": meta.get("is_exact", False), "is_local_only": meta.get("is_local_only", False), "is_suppression": meta.get("is_suppression", False), "provenance": meta.get("provenance")})
        return value


def _candidate_dict(*, candidate_id, level_code, rank, label_en, label_ar, language, taxonomy, taxonomy_code, source, verification_status, is_exact=False, is_local_only=False, is_suppression=False, dimension=None, provenance=None, extra=None):
    metadata = dict(extra or {})
    metadata.update({"label_en": label_en, "label_ar": label_ar, "dimension": dimension, "is_exact": is_exact, "is_local_only": is_local_only, "is_suppression": is_suppression, "provenance": provenance})
    representation = label_ar if language == "ar" else label_en
    return Candidate(candidate_id, level_code, rank, representation, language, taxonomy, taxonomy_code, source, verification_status, metadata, representation is not None, None if representation is not None else "MISSING_VERIFIED_TRANSLATION").to_dict()


class GeneralizationDB:
    def __init__(self, path="data/processed/finaira_generalization.db"):
        self.engine = make_engine(path)

    def get_candidates(self, entity_type, value, output_language="en", context=None, include_review_candidates=False, input_language=None):
        et = entity_type.upper()
        lang = output_language.lower()
        query_lang = (input_language or lang).lower()
        context = context or {}
        # The public taxonomy has one organization-like runtime type.  Keep
        # accepting legacy/source labels for compatibility, but resolve them
        # through CORPORATION so universities and generic organizations do
        # not become a separate generalization domain.
        if et in {"ORGANIZATION", "UNIVERSITY"}:
            et = "CORPORATION"
        if et == "OCCUPATION":
            et = "JOB_TITLE"
        if et == "AGE":
            return self._age(value, lang)
        if et == "DATE":
            return self._date(value, lang, context)
        with Session(self.engine) as session:
            if et == "JOB_TITLE":
                return self._occupation(session, value, lang)
            if et == "COUNTRY":
                return self._country(session, value, lang, query_lang)
            if et == "NATIONALITY":
                return self._nationality(session, value, lang, query_lang)
            if et == "BANK":
                return self._bank(session, value, lang, include_review_candidates, query_lang)
            if et == "CORPORATION":
                return self._organization(session, et, value, lang, include_review_candidates, query_lang)
            if et == "GOVERNMENT_ENTITY":
                return self._government(session, value, lang, include_review_candidates, query_lang)
        return self._result(et, "UNSUPPORTED_ENTITY_TYPE", None, [], "UNSUPPORTED_ENTITY_TYPE")

    def _result(self, entity_type, status, canonical_id, candidates, reason=None):
        return {"entity_type": entity_type, "resolution_status": status, "reason_code": reason, "canonical_id": canonical_id, "selected_candidate": None, "candidates": candidates}

    @staticmethod
    def _occupation_phrase_key(value, lang):
        normalized = normalize(value, lang)
        return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))

    @staticmethod
    def _occupation_alias_variants(alias_text):
        """Return slash-separated ESCO alternatives as independent aliases."""
        return [part.strip() for part in re.split(r"\s*/\s*", alias_text) if part.strip()]

    @staticmethod
    def _occupation_query_languages(value, output_language):
        """Prefer the language signalled by the query, not the output label language."""
        primary = "ar" if re.search(r"[\u0600-\u06ff]", value or "") else "en"
        languages = [primary]
        if output_language in {"ar", "en"} and output_language not in languages:
            languages.append(output_language)
        for language in ("ar", "en"):
            if language not in languages:
                languages.append(language)
        return languages

    def _occupation_lookup(self, session, value, query_language):
        rows = session.scalars(select(OccupationAlias).where(OccupationAlias.language == query_language)).all()
        exact_index = {}
        variant_exact_index = {}
        phrase_index = {}
        for row in rows:
            if row.review_status not in {"OFFICIAL", "REVIEWED"}:
                continue
            exact_index.setdefault(row.normalized_alias, set()).add(row.occupation_id)
            for variant in self._occupation_alias_variants(row.alias_text):
                variant_key = normalize(variant, query_language)
                variant_exact_index.setdefault(variant_key, set()).add(row.occupation_id)
                phrase_key = self._occupation_phrase_key(variant, query_language)
                if phrase_key:
                    phrase_index.setdefault(phrase_key, set()).add(row.occupation_id)

        normalized = normalize(value, query_language)
        ids = exact_index.get(normalized, set())
        matched_phrase = value
        match_method = "EXACT_ALIAS"
        original_phrase_key = self._occupation_phrase_key(value, query_language)
        if not ids:
            ids = variant_exact_index.get(normalized, set())
            if ids:
                match_method = "ALIAS_VARIANT"
        if not ids and original_phrase_key:
            ids = phrase_index.get(original_phrase_key, set())
            if ids:
                matched_phrase = original_phrase_key
                match_method = "NORMALIZED_FULL_PHRASE"

        if not ids:
            tokens = original_phrase_key.split()
            found = []
            for size in range(len(tokens) - 1, 0, -1):
                for start in range(0, len(tokens) - size + 1):
                    phrase = " ".join(tokens[start:start + size])
                    candidate_ids = phrase_index.get(phrase, set())
                    if candidate_ids:
                        found.append((phrase, candidate_ids))
                if found:
                    break
            if found:
                matched_phrase = found[0][0] if len(found) == 1 else " | ".join(item[0] for item in found)
                ids = set().union(*(item[1] for item in found))
                match_method = "LONGEST_PHRASE_MATCH"
        return ids, match_method, matched_phrase

    def _occupation(self, session, value, lang):
        """Resolve both legacy occupation labels through JOB_TITLE/ESCO/ISCO.

        The full value is attempted first. If it is not an alias, contiguous
        phrases are tried from longest to shortest. A shortened match is
        explicitly recorded as such and never treated as an exact match to the
        original input.
        """
        scheme = "JOB_TITLE_ISCO08"
        for query_language in self._occupation_query_languages(value, lang):
            ids, match_method, matched_phrase = self._occupation_lookup(session, value, query_language)
            if not ids:
                continue
            if len(ids) > 1:
                return self._occupation_result(session, scheme, None, lang, "AMBIGUOUS", "ALIAS_COLLISION", match_method, matched_phrase, query_language)
            reason = None if match_method in {"EXACT_ALIAS", "ALIAS_VARIANT", "NORMALIZED_FULL_PHRASE"} else "LONGEST_PHRASE_MATCH"
            return self._occupation_result(session, scheme, next(iter(ids)), lang, "VERIFIED", reason, match_method, matched_phrase, query_language)
        return self._job_title_fallback(lang, "UNRECOGNIZED_JOB_TITLE_GENERIC_FALLBACK")

    def _occupation_result(self, session, scheme, canonical, lang, status, reason, match_method, matched_phrase, query_language):
        result = self._static_result(session, "JOB_TITLE", scheme, canonical, lang, status, reason)
        for candidate in result["candidates"]:
            provenance = dict(candidate.get("provenance") or {})
            provenance.update({"canonical_entity_type": "JOB_TITLE", "match_method": match_method, "matched_phrase": matched_phrase, "query_language": query_language, "output_language": lang})
            candidate["provenance"] = provenance
        return result

    def _job_title_fallback(self, lang, reason):
        labels = [
            ("JOB_TITLE_1", "Job title 1", "المسمى الوظيفي 1"),
            ("JOB_TITLE_2", "Job title 2", "المسمى الوظيفي 2"),
        ]
        candidates = [_candidate_dict(candidate_id=stable_id("JOB_TITLE_FALLBACK", code), level_code=code, rank=index, label_en=en, label_ar=ar, language=lang, taxonomy="FINAIR_JOB_TITLE", taxonomy_code=None, source="Finaira safe generic fallback", verification_status="CONFIGURED", provenance={"canonical_entity_type": "JOB_TITLE", "fallback_kind": "UNMATCHED_JOB_TITLE"}) for index, (code, en, ar) in enumerate(labels)]
        candidates.append(_candidate_dict(candidate_id=stable_id("JOB_TITLE_FALLBACK", "SUPPRESSED"), level_code="SUPPRESSED", rank=2, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_JOB_TITLE", taxonomy_code=None, source="Finaira safe generic fallback", verification_status="CONFIGURED", is_suppression=True, provenance={"canonical_entity_type": "JOB_TITLE", "fallback_kind": "UNMATCHED_JOB_TITLE"}))
        return self._result("JOB_TITLE", "NOT_FOUND", None, candidates, reason)

    def _country(self, session, value, lang, query_lang=None):
        """Resolve country names directly against Natural Earth Admin 0.

        COUNTRY is deliberately separate from NATIONALITY.  A country name
        is not treated as a demonym, and Natural Earth region labels are only
        exposed when the requested output language has a verified label.
        """
        query_lang = query_lang or lang
        normalized = normalize(value, query_lang)
        matches = []
        match_methods = {}
        match_verification = {}
        aliases = [row for row in session.scalars(select(NaturalEarthCountryAlias).where(NaturalEarthCountryAlias.enabled_for_lookup.is_(True))).all() if normalize(row.alias_text, row.language) == normalize(value, row.language)]
        alias_ids = {row.natural_earth_id for row in aliases}
        for alias in aliases:
            current = match_verification.get(alias.natural_earth_id)
            if current != "REVIEWED" or alias.verification_status == "REVIEWED":
                match_verification[alias.natural_earth_id] = alias.verification_status
        if alias_ids:
            rows = [session.get(NaturalEarthCountry, natural_earth_id) for natural_earth_id in sorted(alias_ids)]
        else:
            rows = session.scalars(select(NaturalEarthCountry)).all()
        for row in rows:
            if row is None:
                continue
            method = None
            if alias_ids and row.natural_earth_id in alias_ids:
                method = "WIKIDATA_COUNTRY_ALIAS"
            elif row.name_ar and query_lang == "ar" and normalize(row.name_ar, "ar") == normalized:
                method = "NATURAL_EARTH_NAME_AR"
            elif row.name_en and query_lang == "en" and normalize(row.name_en, "en") == normalized:
                method = "NATURAL_EARTH_NAME_EN"
            elif row.iso_a2 and row.iso_a2 != "-99" and row.iso_a2.casefold() == normalized:
                method = "NATURAL_EARTH_ISO_A2"
            if method:
                matches.append(row)
                match_methods[row.natural_earth_id] = method
        if len(matches) > 1:
            return self._country_result(session, None, lang, "AMBIGUOUS", "ALIAS_COLLISION", matches, match_methods, match_verification)
        if not matches:
            return self._country_result(session, None, lang, "NOT_FOUND", "UNRECOGNIZED_COUNTRY", [], {}, match_verification)
        return self._country_result(session, matches[0], lang, "MATCHED", None, matches, match_methods, match_verification)

    def _country_result(self, session, country, lang, status, reason, matches, match_methods, match_verification=None):
        candidates = []
        source = self._source(session, country.source_id) if country else None
        if country and status == "MATCHED":
            match_verification = match_verification or {}
            alias_verification = match_verification.get(country.natural_earth_id, "SOURCE_VERIFIED")
            provenance = {
                "source": source,
                "natural_earth_id": country.natural_earth_id,
                "natural_earth_version": country.source_version,
                "match_method": match_methods.get(country.natural_earth_id),
                "wikidata_qid": country.wikidata_qid,
                "iso_a2": country.iso_a2,
                "alias_verification_status": alias_verification,
            }
            exact_id = stable_id("COUNTRY_NATURAL_EARTH", "EXACT", country.natural_earth_id)
            candidates.append(_candidate_dict(candidate_id=exact_id, level_code="EXACT", rank=0, label_en=country.name_en, label_ar=country.name_ar, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.iso_a2, source=source, verification_status=alias_verification, is_exact=True, is_local_only=True, provenance=provenance, extra={"country_qid": country.wikidata_qid}))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUBREGION", country.subregion), level_code="SUBREGION", rank=1, label_en=country.subregion, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.subregion, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "REGION_UN", country.region_un), level_code="REGION_UN", rank=2, label_en=country.region_un, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.region_un, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "CONTINENT", country.continent), level_code="CONTINENT", rank=3, label_en=country.continent, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.continent, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=4, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        else:
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=0, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        return self._result("COUNTRY", status, country.iso_a2 if country else None, candidates, reason)

    def _nationality(self, session, value, lang, query_lang=None):
        query_lang = query_lang or lang
        # The presence of v2 rows is the runtime switch away from legacy M49.
        if session.scalar(select(NationalityAliasV2.alias_key).limit(1)) is None:
            rows = session.scalars(select(NationalityAlias).where(NationalityAlias.normalized_alias == normalize(value, query_lang), NationalityAlias.language == query_lang)).all()
            ids = {row.country_iso2 for row in rows if row.review_status in {"OFFICIAL", "REVIEWED"}}
            if len(ids) > 1:
                return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", None, lang, "AMBIGUOUS", "ALIAS_COLLISION")
            if not ids:
                return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", None, lang, "NOT_FOUND", "UNRECOGNIZED_NATIONALITY")
            return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", next(iter(ids)), lang, "VERIFIED")
        rows = session.scalars(select(NationalityAliasV2).where(NationalityAliasV2.normalized_alias == normalize(value, query_lang), NationalityAliasV2.language == query_lang)).all()
        qids = {row.country_qid for row in rows}
        if len(qids) > 1:
            return self._natural_earth_result(session, None, lang, "AMBIGUOUS", "ALIAS_COLLISION")
        if not qids:
            return self._natural_earth_result(session, None, lang, "NOT_FOUND", "UNRECOGNIZED_NATIONALITY")
        qid = next(iter(qids))
        join = session.get(NationalityGeoJoin, qid)
        if not join or join.join_status not in {"MATCHED_QID", "MATCHED_ISO"}:
            return self._natural_earth_result(session, qid, lang, "REVIEW_ONLY", "NATURAL_EARTH_JOIN_UNRESOLVED")
        return self._natural_earth_result(session, qid, lang, "MATCHED", None)

    def _natural_earth_result(self, session, qid, lang, status, reason):
        candidates = []
        join = session.get(NationalityGeoJoin, qid) if qid else None
        country = session.get(NationalityCountry, qid) if qid else None
        ne = session.get(NaturalEarthCountry, join.natural_earth_id) if join and join.natural_earth_id else None
        aliases = session.scalars(select(NationalityAliasV2).where(NationalityAliasV2.country_qid == qid).order_by(NationalityAliasV2.alias_key)).all() if qid else []
        alias = next((item for item in aliases if item.language == lang), aliases[0] if aliases else None)
        alias_en = next((item.alias_text for item in aliases if item.language == "en"), None)
        alias_ar = next((item.alias_text for item in aliases if item.language == "ar"), None)
        source = self._source(session, alias.source_id if alias else (join.source_id if join else None))
        if status == "MATCHED" and alias and ne:
            provenance = {"source": source, "join_status": join.join_status, "match_method": join.match_method, "natural_earth_id": ne.natural_earth_id, "natural_earth_version": "5.1.1"}
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "EXACT", qid), level_code="EXACT", rank=0, label_en=alias_en, label_ar=alias_ar, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.iso_a2, source=source, verification_status=alias.verification_status, is_exact=True, is_local_only=True, provenance=provenance, extra={"join_status": join.join_status, "country_qid": country.country_qid if country else qid}))
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "SUBREGION", ne.subregion), level_code="SUBREGION", rank=1, label_en=ne.subregion, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.subregion, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "CONTINENT", ne.continent), level_code="CONTINENT", rank=2, label_en=ne.continent, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.continent, source=source, verification_status="SOURCE_VERIFIED", provenance={**provenance, "region_un": ne.region_un}))
        candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=3, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        return self._result("NATIONALITY", status, qid, candidates, reason)

    def _bank(self, session, value, lang, include_review, query_lang=None):
        query_lang = query_lang or lang
        norm = normalize(value, query_lang)
        model_aliases = session.scalars(select(BankModelAlias).where(BankModelAlias.normalized_alias == norm, BankModelAlias.language == query_lang)).all()
        if model_aliases:
            enabled_aliases = [row for row in model_aliases if row.enabled_for_lookup]
            enabled_keys = {row.safe_generalization_key for row in enabled_aliases if row.safe_generalization_key}
            blocked_keys = {row.safe_generalization_key for row in model_aliases if not row.enabled_for_lookup and row.safe_generalization_key}
            # A reviewed or historical operation with the same spelling but a
            # different model-safe key makes the alias unsafe to auto-resolve.
            # Do not let a verified conventional alias hide a reviewed mixed,
            # Islamic, historical, or otherwise conflicting operation.
            if enabled_aliases and blocked_keys - enabled_keys and not include_review:
                return self._bank_fallback("REVIEW_ONLY", "BANK_MODEL_REVIEW_REQUIRED", lang)
            aliases = model_aliases if include_review else enabled_aliases
            if aliases:
                records = [session.get(BankIdentityModel, row.record_id) for row in aliases]
                records = [row for row in records if row is not None]
                return self._bank_model_result(session, records, lang)
            return self._bank_fallback("REVIEW_ONLY", "BANK_MODEL_REVIEW_REQUIRED", lang)
        all_aliases = session.scalars(select(BankAlias).where(BankAlias.normalized_alias == norm, BankAlias.language == query_lang)).all()
        enabled_aliases = [row for row in all_aliases if row.enabled_for_lookup]
        all_ids = {row.bank_id for row in all_aliases}
        if not include_review and len(all_ids) > 1 and enabled_aliases:
            return self._bank_fallback("AMBIGUOUS", "ALIAS_COLLISION", lang)
        aliases = all_aliases if include_review else enabled_aliases
        ids = {row.bank_id for row in aliases}
        if not ids:
            ids = {row.bank_id for row in session.scalars(select(Bank)).all() if normalize(row.name_en, "en") == norm or (row.name_ar and normalize(row.name_ar, "ar") == norm)}
        if len(ids) > 1:
            return self._bank_fallback("AMBIGUOUS", "ALIAS_COLLISION", lang)
        if not ids:
            return self._bank_fallback("NOT_FOUND", "UNRECOGNIZED_BANK", lang)
        model_records = session.scalars(select(BankIdentityModel).where(BankIdentityModel.canonical_bank_id.in_(ids))).all()
        if model_records:
            return self._bank_model_result(session, model_records, lang)
        bank_id = next(iter(ids))
        rows = session.scalars(select(BankCandidate).where(BankCandidate.bank_id == bank_id).order_by(BankCandidate.specificity_rank)).all()
        return self._result("BANK", "MATCHED", bank_id, [self._bank_row(session, row, lang) for row in rows])

    @staticmethod
    def _bank_record_key(record):
        return record.safe_generalization_key or record.proposed_model_aware_key

    def _bank_model_result(self, session, records, lang):
        """Resolve source aliases to a verified model-aware cohort.

        Country operations remain separate source records. They collapse only
        when the supplied safe key agrees and no explicit do-not-merge pair
        blocks the collapse. Review-required or unknown-model rows remain
        review-only and are never selected by the privacy pipeline.
        """
        records = sorted({row.record_id: row for row in records}.values(), key=lambda row: row.record_id)
        keys = {self._bank_record_key(row) for row in records if self._bank_record_key(row)}
        if len(keys) != 1:
            return self._bank_fallback("AMBIGUOUS", "ALIAS_COLLISION", lang)
        key = next(iter(keys))
        record_ids = {row.record_id for row in records}
        blocked = session.scalars(select(BankDoNotMerge)).all()
        if any({row.record_a, row.record_b}.issubset(record_ids) for row in blocked):
            return self._bank_fallback("AMBIGUOUS", "EXPLICIT_DO_NOT_MERGE", lang)
        cohort = session.get(BankGeneralizationCohort, key)
        eligible = bool(cohort and cohort.eligible_for_lookup)
        representative = records[0]
        form = session.scalar(select(BankGeneralizationForm).where(
            BankGeneralizationForm.source_record_id.in_(record_ids),
            BankGeneralizationForm.safe_generalization_key == key,
            BankGeneralizationForm.level_code == "MODEL_SAFE_GROUP",
        ).order_by(BankGeneralizationForm.form_id))
        finance_form = session.scalar(select(BankGeneralizationForm).where(
            BankGeneralizationForm.source_record_id.in_(record_ids),
            BankGeneralizationForm.safe_generalization_key == key,
            BankGeneralizationForm.level_code == "FINANCE_MODEL",
        ).order_by(BankGeneralizationForm.form_id))
        canonical_id = representative.bank_identity_id or representative.canonical_bank_id
        exact_row = session.scalar(select(BankCandidate).where(BankCandidate.bank_id == representative.canonical_bank_id, BankCandidate.is_exact.is_(True)))
        candidates = []
        if exact_row is not None:
            exact = self._bank_row(session, exact_row, lang)
            exact_label_en = representative.canonical_name_2026 or representative.source_name_en or exact.get("label_en")
            approved_ar_alias = session.scalar(select(BankAlias).where(
                BankAlias.bank_id == representative.canonical_bank_id,
                BankAlias.language == "ar",
                BankAlias.enabled_for_lookup.is_(True),
            ).order_by(BankAlias.alias_id))
            exact_label_ar = representative.source_name_ar or exact.get("label_ar") or (approved_ar_alias.alias_text if approved_ar_alias else None)
            exact["label_en"] = exact_label_en
            exact["label_ar"] = exact_label_ar
            exact["representation"] = exact_label_ar if lang == "ar" else exact_label_en
            exact["provenance"] = {
                **(exact.get("provenance") or {}),
                "canonical_entity_record_id": representative.record_id,
                "bank_identity_id": representative.bank_identity_id,
                "family_id": representative.family_id,
                "family_display_name": representative.family_display_name,
                "safe_generalization_key": key,
                "banking_model_effective": representative.banking_model_effective,
                "review_required": representative.review_required,
                "automatic_grouping": representative.automatic_grouping,
            }
            candidates.append(exact)
        bank = session.get(Bank, representative.canonical_bank_id)
        banking_model = (bank.finance_model if bank else None) or representative.banking_model_effective or "UNKNOWN"
        model_label_en, model_label_ar = BANK_MODEL_FORM_LABELS.get(banking_model, BANK_MODEL_FORM_LABELS["UNKNOWN"])
        model_enabled = bool(finance_form and finance_form.enabled_for_lookup)
        finance_provenance = {
            "source": self._source(session, finance_form.source_id) if finance_form else self._source(session, cohort.source_id) if cohort else None,
            "generalization_form_id": finance_form.form_id if finance_form else None,
            "generalization_form_level": "FINANCE_MODEL",
            "shared_form_key": f"BANK_FINANCE_MODEL__{banking_model}",
            "banking_model": banking_model,
            "safe_generalization_key": key,
            "family_id": cohort.family_id if cohort else representative.family_id,
            "source_record_ids": sorted(record_ids),
            "review_required": any(row.review_required for row in records),
            "eligible_for_lookup": model_enabled,
            "disclosure_approved": model_enabled,
        }
        candidates.append(_candidate_dict(
            candidate_id=f"BANK_FINANCE_MODEL__{banking_model}",
            level_code="FINANCE_MODEL",
            rank=2,
            label_en=model_label_en,
            label_ar=model_label_ar,
            language=lang,
            taxonomy="FINAIR_BANK",
            taxonomy_code=banking_model,
            source=self._source(session, finance_form.source_id) if finance_form else self._source(session, cohort.source_id) if cohort else None,
            verification_status="SOURCE_VERIFIED" if model_enabled else "REVIEW_ONLY",
            provenance=finance_provenance,
            extra={
                "finance_model": banking_model,
                "shared_form_key": f"BANK_FINANCE_MODEL__{banking_model}",
                "review_only": not model_enabled,
                "disclosure_approved": model_enabled,
            },
        ))
        provenance = {
            "source": self._source(session, cohort.source_id) if cohort else None,
            "safe_generalization_key": key,
            "family_id": cohort.family_id if cohort else representative.family_id,
            "family_display_name": representative.family_display_name,
            "model": cohort.model if cohort else representative.banking_model_effective,
            "source_record_ids": sorted(record_ids),
            "bank_identity_ids": sorted({row.bank_identity_id for row in records if row.bank_identity_id}),
            "automatic_grouping": cohort.automatic_grouping if cohort else False,
            "eligible_for_lookup": eligible,
            "eligibility_reason": cohort.eligibility_reason if cohort else "MISSING_COHORT",
            "review_required": any(row.review_required for row in records),
            "generalization_form_id": form.form_id if form else None,
            "generalization_form_level": form.level_code if form else "MODEL_SAFE_GROUP",
            "finance_model_form_id": finance_form.form_id if finance_form else None,
            "finance_model_form_key": f"BANK_FINANCE_MODEL__{banking_model}",
        }
        candidates.append(_candidate_dict(
            candidate_id=f"BANK_SAFE__{key}",
            level_code="MODEL_SAFE_GROUP",
            rank=1,
            label_en=key,
            label_ar=key,
            language=lang,
            taxonomy="FINAIR_BANK_MODEL_SAFE",
            taxonomy_code=key,
            source=self._source(session, cohort.source_id) if cohort else None,
            verification_status="SOURCE_VERIFIED" if eligible else "REVIEW_ONLY",
            provenance=provenance,
            extra={"safe_generalization_key": key, "review_only": not eligible, "disclosure_approved": eligible},
        ))
        generic_rows = session.scalars(select(BankCandidate).where(
            BankCandidate.bank_id == representative.canonical_bank_id,
            BankCandidate.level_code.in_(("BANKING_INSTITUTION", "FINANCIAL_INSTITUTION")),
        ).order_by(BankCandidate.specificity_rank)).all()
        for generic_row in generic_rows:
            generic_candidate = self._bank_row(session, generic_row, lang)
            generic_candidate["provenance"] = {
                **(generic_candidate.get("provenance") or {}),
                "safe_generalization_key": key,
                "finance_model_form_id": finance_form.form_id if finance_form else None,
                "shared_form_key": f"BANK_FINANCE_MODEL__{banking_model}",
                "review_required": any(row.review_required for row in records),
            }
            candidates.append(generic_candidate)
        candidates.append(_candidate_dict(
            candidate_id=f"BANK_SAFE__{key}__SUPPRESSED",
            level_code="SUPPRESSED",
            rank=99,
            label_en=None,
            label_ar=None,
            language=lang,
            taxonomy="FINAIR_BANK_MODEL_SAFE",
            taxonomy_code=None,
            source=self._source(session, cohort.source_id) if cohort else None,
            verification_status="CONFIGURED",
            is_suppression=True,
            provenance=provenance,
        ))
        return self._result("BANK", "MATCHED" if eligible else "REVIEW_ONLY", canonical_id, candidates, None if eligible else "BANK_MODEL_REVIEW_REQUIRED")

    def _bank_row(self, session, row, lang):
        source = self._source(session, row.source_id)
        audits = session.scalars(select(BankAuditClassification).where(BankAuditClassification.bank_id == row.bank_id).order_by(BankAuditClassification.source_record_id)).all()
        relationships = session.scalars(select(BankRelationship).where((BankRelationship.child_bank_id == row.bank_id) | (BankRelationship.parent_bank_id == row.bank_id)).order_by(BankRelationship.relationship_id)).all()
        audit_payload = [{
            "source_record_id": item.source_record_id,
            "country_code": item.country_code,
            "banking_model": item.banking_model,
            "banking_model_source": item.banking_model_source,
            "business_scope": item.business_scope,
            "entity_kind": item.entity_kind,
            "operational_status": item.operational_status,
            "license_status": item.license_status,
            "licensed_count_eligible": item.licensed_count_eligible,
            "license_confirmation": item.license_confirmation,
            "confidence": item.confidence,
            "review_action": item.review_action,
            "source_url": item.source_url,
            "evidence_url": item.evidence_url,
            "classification_evidence": item.classification_evidence,
            "review_note": item.review_note,
        } for item in audits]
        relationship_payload = [{
            "relationship_type": item.relationship_type,
            "child_bank_id": item.child_bank_id,
            "parent_bank_id": item.parent_bank_id,
            "verification_status": item.verification_status,
            "evidence_note": item.evidence_note,
        } for item in relationships]
        primary = audits[0] if audits else None
        provenance = {"source": source, "evidence_status": row.evidence_status, "disclosure_approved": row.disclosure_approved}
        if primary:
            provenance.update({"audit_source_record_id": primary.source_record_id, "audit_review_action": primary.review_action, "audit_license_status": primary.license_status})
        return _candidate_dict(candidate_id=row.candidate_id, level_code=row.level_code, rank=row.specificity_rank, label_en=row.label_en, label_ar=row.label_ar, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=row.finance_model, source=source, verification_status=row.verification_status, is_exact=row.is_exact, is_local_only=row.is_local_only, is_suppression=row.is_suppression, provenance=provenance, extra={"category_population_count": row.category_population_count, "finance_model": row.finance_model, "disclosure_approved": row.disclosure_approved, "audit_classifications": audit_payload, "relationships": relationship_payload})

    def _bank_fallback(self, status, reason, lang):
        labels = [("BANKING_INSTITUTION", "Banking institution", "مؤسسة مصرفية"), ("FINANCIAL_INSTITUTION", "Financial institution", "مؤسسة مالية")]
        candidates = [_candidate_dict(candidate_id=stable_id("BANK_FALLBACK", code), level_code=code, rank=index, label_en=en, label_ar=ar, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED") for index, (code, en, ar) in enumerate(labels)]
        candidates.append(_candidate_dict(candidate_id=stable_id("BANK_FALLBACK", "SUPPRESSED"), level_code="SUPPRESSED", rank=2, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True))
        return self._result("BANK", status, None, candidates, reason)

    def _organization(self, session, entity_type, value, lang, include_review, query_lang=None):
        query_lang = query_lang or lang
        rows = session.scalars(select(OrganizationAlias).where(OrganizationAlias.normalized_alias == normalize(value, query_lang), OrganizationAlias.language == query_lang, OrganizationAlias.enabled_for_lookup.is_(True))).all()
        ids = {row.organization_qid for row in rows}
        if len(ids) > 1:
            return self._organization_fallback(entity_type, lang, "AMBIGUOUS", "ALIAS_COLLISION")
        if not ids:
            return self._organization_fallback(entity_type, lang, "NOT_FOUND", "UNRECOGNIZED_ORGANIZATION")
        qid = next(iter(ids))
        org = session.get(Organization, qid)
        if session.scalar(select(OrganizationExclusion.exclusion_id).where(OrganizationExclusion.organization_qid == qid)):
            return self._organization_fallback(entity_type, lang, "EXCLUDED", "EXCLUDED_ORGANIZATION")
        # Source rows may retain their original semantic kind in review_flags,
        # but the runtime taxonomy is deliberately CORPORATION for every
        # organization-like record.
        kind = "CORPORATION"
        label_en = org.name_en or "Company"
        label_ar = org.name_ar
        source = self._source(session, org.source_id)
        verified_identity = org.identity_verification_status in {"VERIFIED", "APPROVED", "OFFICIAL"} and org.import_decision in {"VERIFIED", "APPROVED"}
        status = "MATCHED" if verified_identity else "REVIEW_ONLY"
        candidates = [_candidate_dict(candidate_id=stable_id("ORG", qid, "EXACT"), level_code="EXACT", rank=0, label_en=label_en, label_ar=label_ar, language=lang, taxonomy="WIKIDATA_ORGANIZATION", taxonomy_code=qid, source=source, verification_status=org.identity_verification_status, is_exact=True, is_local_only=True, provenance={"source": source, "import_decision": org.import_decision, "review_flags": org.review_flags, "canonical_entity_type": "CORPORATION", "source_semantic_kind": org.semantic_kind})]
        generic = ("ORGANIZATION_GENERIC", "Company", "شركة")
        candidates.append(_candidate_dict(candidate_id=stable_id("ORG", kind, "GENERIC"), level_code=generic[0], rank=1, label_en=generic[1], label_ar=generic[2], language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"))
        for link in session.scalars(select(OrganizationIndustry).where(OrganizationIndustry.organization_qid == qid)).all():
            mapping = session.get(IndustryQIDMapping, link.mapping_id) if link.mapping_id else None
            industry_verified = verified_identity and link.verification_status in {"VERIFIED", "APPROVED"} and mapping is not None and mapping.review_status in {"VERIFIED", "APPROVED"}
            if mapping is not None and (industry_verified or include_review):
                candidates.append(_candidate_dict(candidate_id=stable_id("ORG", qid, link.link_id), level_code=link.subcategory_code or link.sector_code or "INDUSTRY", rank=2, label_en=mapping.subcategory_label_en, label_ar=mapping.subcategory_label_ar, language=lang, taxonomy="FINAIR_INDUSTRY", taxonomy_code=link.subcategory_code or link.sector_code, source=self._source(session, mapping.source_id), verification_status="VERIFIED" if industry_verified else "REVIEW_ONLY", dimension="INDUSTRY", provenance={"source": self._source(session, mapping.source_id), "organization_industry_status": link.verification_status, "mapping_status": mapping.review_status}, extra={"review_only": not industry_verified}))
        candidates.append(_candidate_dict(candidate_id=stable_id("ORG", qid, "SUPPRESSED"), level_code="SUPPRESSED", rank=99, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True))
        return self._result(entity_type, status, qid, sorted(candidates, key=lambda row: (row["specificity_rank"], row["candidate_id"])))

    def _organization_fallback(self, entity_type, lang, status, reason):
        code, en, ar = "ORGANIZATION_GENERIC", "Company", "شركة"
        candidates = [_candidate_dict(candidate_id=stable_id("ORG_FALLBACK", code), level_code=code, rank=0, label_en=en, label_ar=ar, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"), _candidate_dict(candidate_id=stable_id("ORG_FALLBACK", "SUPPRESSED"), level_code="SUPPRESSED", rank=1, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True)]
        return self._result("CORPORATION", status, None, candidates, reason)

    def _government(self, session, value, lang, include_review, query_lang=None):
        query_lang = query_lang or lang
        aliases = session.scalars(select(GovernmentAlias).where(GovernmentAlias.normalized_alias == normalize(value, query_lang), GovernmentAlias.language == query_lang)).all()
        enabled = [row for row in aliases if row.enabled_for_lookup]
        aliases = enabled if enabled or not include_review else aliases
        ids = {row.entity_id for row in aliases}
        if len(ids) > 1:
            return self._government_fallback(lang, "AMBIGUOUS", "ALIAS_COLLISION")
        if not ids:
            return self._government_fallback(lang, "NOT_FOUND", "UNRECOGNIZED_GOVERNMENT_ENTITY")
        entity_id = next(iter(ids))
        entity = session.get(GovernmentEntity, entity_id)
        alias = sorted(aliases, key=lambda row: row.alias_id)[0]
        source = self._source(session, entity.source_id)
        candidates = [_candidate_dict(candidate_id=f"{entity_id}__EXACT", level_code="EXACT", rank=0, label_en=entity.name_en_provisional, label_ar=entity.name_ar, language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=entity_id, source=source, verification_status=entity.identity_verification_status, is_exact=True, is_local_only=True, provenance={"source": source, "alias_verification_status": alias.verification_status, "identity_verification_status": entity.identity_verification_status})]
        candidates.append(_candidate_dict(candidate_id="GOVERNMENT_ENTITY__GENERIC", level_code="GOVERNMENT_ENTITY_GENERIC", rank=1, label_en="Government entity", label_ar="جهة حكومية", language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"))
        if include_review:
            for row in session.scalars(select(GovernmentCandidateReview).where(GovernmentCandidateReview.entity_id == entity_id).order_by(GovernmentCandidateReview.specificity_rank_branch_local, GovernmentCandidateReview.candidate_id)).all():
                if row.level_code == "EXACT":
                    continue
                candidates.append(_candidate_dict(candidate_id=row.candidate_id, level_code=row.level_code, rank=10 + row.specificity_rank_branch_local, label_en=row.label_en, label_ar=row.label_ar, language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=row.level_code, source=row.source_url or "government_candidate_catalog_REVIEW.csv", verification_status=row.verification_status, is_local_only=row.is_local_only, is_suppression=row.is_suppression, dimension=row.dimension, provenance={"source": row.source_url, "requires_policy_approval": row.requires_policy_approval, "default_visible": row.default_visible}, extra={"review_only": True, "branch": row.dimension}))
        candidates.append(_candidate_dict(candidate_id=f"{entity_id}__SUPPRESSED", level_code="SUPPRESSED", rank=99, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True))
        return self._result("GOVERNMENT_ENTITY", "REVIEW_ONLY", entity_id, candidates)

    def _government_fallback(self, lang, status, reason):
        candidates = [_candidate_dict(candidate_id="GOVERNMENT_ENTITY__GENERIC", level_code="GOVERNMENT_ENTITY_GENERIC", rank=0, label_en="Government entity", label_ar="جهة حكومية", language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"), _candidate_dict(candidate_id="GOVERNMENT_ENTITY__SUPPRESSED", level_code="SUPPRESSED", rank=1, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_GOVERNMENT", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True)]
        return self._result("GOVERNMENT_ENTITY", status, None, candidates, reason)

    def _source(self, session, source_id):
        source = session.get(DataSource, source_id) if source_id else None
        return {"name": source.name, "version": source.version, "checksum": source.checksum, "url": source.source_url} if source else None

    def _static_result(self, session, entity_type, scheme, canonical, lang, status, reason=None):
        all_candidates = session.scalars(select(GeneralizationCandidate).where(GeneralizationCandidate.scheme_id == scheme)).all()
        allowed = []
        if canonical:
            by_id = {row.candidate_id: row for row in all_candidates}
            current = by_id.get(stable_id(scheme, "EXACT", canonical))
            while current:
                allowed.append(current)
                current = by_id.get(current.parent_candidate_id)
        suppressed = next((row for row in all_candidates if row.candidate_id == stable_id(scheme, "SUPPRESSED")), None)
        if suppressed and suppressed not in allowed:
            allowed.append(suppressed)
        return self._result(entity_type, status, canonical, self._rows(session, scheme, allowed, lang), reason)

    def _rows(self, session, scheme, items, lang):
        levels = {row.level_id: row for row in session.scalars(select(GeneralizationLevel).where(GeneralizationLevel.scheme_id == scheme)).all()}
        output = []
        for candidate in sorted(items, key=lambda row: levels[row.level_id].specificity_rank):
            level = levels[candidate.level_id]
            metadata = session.get(CandidateMetadata, candidate.candidate_id)
            source = self._source(session, candidate.source_id)
            output.append(_candidate_dict(candidate_id=candidate.candidate_id, level_code=level.level_code, rank=level.specificity_rank, label_en=candidate.label_en, label_ar=candidate.label_ar, language=lang, taxonomy="ISCO-08" if scheme.endswith("ISCO08") else "UN_M49" if scheme.endswith("M49") else None, taxonomy_code=candidate.taxonomy_code, source=source, verification_status=candidate.review_status, is_exact=metadata.is_exact, is_local_only=metadata.is_local_only, is_suppression=metadata.is_suppression, provenance={"source": source, "derivation_method": candidate.derivation_method}, extra={"taxonomy_depth": metadata.taxonomy_depth, "underlying_category_count": metadata.underlying_category_count}))
        return output

    def _age(self, value, lang):
        try:
            n = parse_age(value)
        except ValueError:
            return self._result("AGE", "INVALID_INPUT", None, [], "INVALID_INPUT")
        narrow = [(0, 17, "أقل من 18 سنة", "Under 18"), (18, 24, "18–24 سنة", "18–24 years"), (25, 29, "25–29 سنة", "25–29 years"), (30, 44, "30–44 سنة", "30–44 years"), (45, 64, "45–64 سنة", "45–64 years"), (65, 120, "65 سنة فأكثر", "65 years and over")]
        wide = [(0, 17, "أقل من 18 سنة", "Under 18"), (18, 24, "18–24 سنة", "18–24 years"), (25, 34, "25–34 سنة", "25–34 years"), (35, 44, "35–44 سنة", "35–44 years"), (45, 54, "45–54 سنة", "45–54 years"), (55, 64, "55–64 سنة", "55–64 years"), (65, 120, "65 سنة فأكثر", "65 years and over")]
        narrow_row = next(row for row in narrow if row[0] <= n <= row[1])
        wide_row = next(row for row in wide if row[0] <= n <= row[1])
        broad = ("قاصر", "Minor") if n < 18 else ("بالغ", "Adult")
        values = [("EXACT", f"{n} سنة", f"{n} years", n, n, True), ("NARROW_BAND", narrow_row[2], narrow_row[3], narrow_row[0], narrow_row[1], False), ("WIDE_BAND", wide_row[2], wide_row[3], wide_row[0], wide_row[1], False), ("BROAD_CATEGORY", broad[0], broad[1], None, None, False), ("SUPPRESSED", "العمر غير محدد", "Age unspecified", None, None, False)]
        candidates = [_candidate_dict(candidate_id=stable_id("AGE_STANDARD", code, n), level_code=code, rank=index, label_en=en, label_ar=ar, language=lang, taxonomy="Finaira policy", taxonomy_code=None, source="Finaira policy", verification_status="CONFIGURED", is_exact=exact, is_local_only=exact, is_suppression=code == "SUPPRESSED", extra={"interval_start": lo, "interval_end": hi, "interval_width": hi - lo + 1 if lo is not None and hi is not None else None}) for index, (code, ar, en, lo, hi, exact) in enumerate(values)]
        return self._result("AGE", "VERIFIED", None, candidates)

    def _date(self, value, lang, context):
        from .date_detector import date_interval, date_levels, detect_date
        detected = detect_date(value, context)
        if detected.status != "VERIFIED":
            return self._result("DATE", detected.status, None, [], detected.reason_code)
        levels = date_levels(detected)
        key = detected.date_iso or f"{detected.calendar}:{detected.year}:{detected.month}:{detected.day}:{detected.raw}"
        candidates = []
        for row in levels:
            code = row["code"]
            interval_start, interval_end = date_interval(detected, code)
            candidates.append(_candidate_dict(
                candidate_id=stable_id("DATE_DETECTOR", detected.calendar, code, key),
                level_code=code,
                rank=row["rank"],
                label_en=row["label_en"],
                label_ar=row["label_ar"],
                language=lang,
                taxonomy=detected.calendar,
                taxonomy_code=None,
                source="Finaira rule-based date detector",
                verification_status="CONFIGURED",
                is_exact=row["is_exact"],
                is_local_only=row["is_exact"],
                is_suppression=row["suppression"],
                provenance={"raw": detected.raw, "calendar": detected.calendar, "precision": detected.precision, "format_family": detected.format_family, "confidence": detected.confidence, "detector_status": detected.status},
                extra={
                    "temporal_precision": code.lower(),
                    "calendar": detected.calendar,
                    "date_iso": detected.date_iso,
                    "timezone": detected.metadata.get("timezone"),
                    "interval_start": interval_start.isoformat() if interval_start else None,
                    "interval_end": interval_end.isoformat() if interval_end else None,
                },
            ))
        return self._result("DATE", "VERIFIED", None, candidates)

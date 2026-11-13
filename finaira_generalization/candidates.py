"""Read-only, deterministic candidate lookup across all supported domains."""

from __future__ import annotations

import calendar
from datetime import date
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .age_date import parse_age
from .db import (
    Bank, BankAlias, BankCandidate, CandidateMetadata, DataSource,
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

    def get_candidates(self, entity_type, value, output_language="en", context=None, include_review_candidates=False):
        et = entity_type.upper()
        lang = output_language.lower()
        context = context or {}
        if et == "AGE":
            return self._age(value, lang)
        if et == "DATE":
            return self._date(value, lang, context)
        with Session(self.engine) as session:
            if et in {"OCCUPATION", "JOB_TITLE"}:
                return self._occupation(session, et, value, lang)
            if et == "COUNTRY":
                return self._country(session, value, lang)
            if et == "NATIONALITY":
                return self._nationality(session, value, lang)
            if et == "BANK":
                return self._bank(session, value, lang, include_review_candidates)
            if et in {"CORPORATION", "ORGANIZATION", "UNIVERSITY"}:
                return self._organization(session, et, value, lang, include_review_candidates)
            if et == "GOVERNMENT_ENTITY":
                return self._government(session, value, lang, include_review_candidates)
        return self._result(et, "UNSUPPORTED_ENTITY_TYPE", None, [], "UNSUPPORTED_ENTITY_TYPE")

    def _result(self, entity_type, status, canonical_id, candidates, reason=None):
        return {"entity_type": entity_type, "resolution_status": status, "reason_code": reason, "canonical_id": canonical_id, "selected_candidate": None, "candidates": candidates}

    def _occupation(self, session, entity_type, value, lang):
        rows = session.scalars(select(OccupationAlias).where(OccupationAlias.normalized_alias == normalize(value, lang), OccupationAlias.language == lang)).all()
        ids = {row.occupation_id for row in rows if row.review_status in {"OFFICIAL", "REVIEWED"}}
        scheme = "OCCUPATION_ISCO08" if entity_type == "OCCUPATION" else "JOB_TITLE_ISCO08"
        if len(ids) > 1:
            return self._static_result(session, entity_type, scheme, None, lang, "AMBIGUOUS", "ALIAS_COLLISION")
        if not ids:
            return self._static_result(session, entity_type, scheme, None, lang, "NOT_FOUND", "UNRECOGNIZED_OCCUPATION")
        return self._static_result(session, entity_type, scheme, next(iter(ids)), lang, "VERIFIED")

    def _country(self, session, value, lang):
        """Resolve country names directly against Natural Earth Admin 0.

        COUNTRY is deliberately separate from NATIONALITY.  A country name
        is not treated as a demonym, and Natural Earth region labels are only
        exposed when the requested output language has a verified label.
        """
        normalized = normalize(value, lang)
        matches = []
        match_methods = {}
        aliases = [row for row in session.scalars(select(NaturalEarthCountryAlias).where(NaturalEarthCountryAlias.enabled_for_lookup.is_(True))).all() if normalize(row.alias_text, row.language) == normalize(value, row.language)]
        alias_ids = {row.natural_earth_id for row in aliases}
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
            elif row.name_ar and normalize(row.name_ar, "ar") == normalized:
                method = "NATURAL_EARTH_NAME_AR"
            elif row.name_en and normalize(row.name_en, "en") == normalized:
                method = "NATURAL_EARTH_NAME_EN"
            elif row.iso_a2 and row.iso_a2 != "-99" and row.iso_a2.casefold() == normalized:
                method = "NATURAL_EARTH_ISO_A2"
            if method:
                matches.append(row)
                match_methods[row.natural_earth_id] = method
        if len(matches) > 1:
            return self._country_result(session, None, lang, "AMBIGUOUS", "ALIAS_COLLISION", matches, match_methods)
        if not matches:
            return self._country_result(session, None, lang, "NOT_FOUND", "UNRECOGNIZED_COUNTRY", [], {})
        return self._country_result(session, matches[0], lang, "MATCHED", None, matches, match_methods)

    def _country_result(self, session, country, lang, status, reason, matches, match_methods):
        candidates = []
        source = self._source(session, country.source_id) if country else None
        if country and status == "MATCHED":
            provenance = {
                "source": source,
                "natural_earth_id": country.natural_earth_id,
                "natural_earth_version": country.source_version,
                "match_method": match_methods.get(country.natural_earth_id),
                "wikidata_qid": country.wikidata_qid,
                "iso_a2": country.iso_a2,
            }
            exact_id = stable_id("COUNTRY_NATURAL_EARTH", "EXACT", country.natural_earth_id)
            candidates.append(_candidate_dict(candidate_id=exact_id, level_code="EXACT", rank=0, label_en=country.name_en, label_ar=country.name_ar, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.iso_a2, source=source, verification_status="SOURCE_VERIFIED", is_exact=True, is_local_only=True, provenance=provenance, extra={"country_qid": country.wikidata_qid}))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUBREGION", country.subregion), level_code="SUBREGION", rank=1, label_en=country.subregion, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.subregion, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "REGION_UN", country.region_un), level_code="REGION_UN", rank=2, label_en=country.region_un, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.region_un, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "CONTINENT", country.continent), level_code="CONTINENT", rank=3, label_en=country.continent, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=country.continent, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=4, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        else:
            candidates.append(_candidate_dict(candidate_id=stable_id("COUNTRY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=0, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        return self._result("COUNTRY", status, country.iso_a2 if country else None, candidates, reason)

    def _nationality(self, session, value, lang):
        # The presence of v2 rows is the runtime switch away from legacy M49.
        if session.scalar(select(NationalityAliasV2.alias_key).limit(1)) is None:
            rows = session.scalars(select(NationalityAlias).where(NationalityAlias.normalized_alias == normalize(value, lang), NationalityAlias.language == lang)).all()
            ids = {row.country_iso2 for row in rows if row.review_status in {"OFFICIAL", "REVIEWED"}}
            if len(ids) > 1:
                return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", None, lang, "AMBIGUOUS", "ALIAS_COLLISION")
            if not ids:
                return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", None, lang, "NOT_FOUND", "UNRECOGNIZED_NATIONALITY")
            return self._static_result(session, "NATIONALITY", "NATIONALITY_M49", next(iter(ids)), lang, "VERIFIED")
        rows = session.scalars(select(NationalityAliasV2).where(NationalityAliasV2.normalized_alias == normalize(value, lang), NationalityAliasV2.language == lang)).all()
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
        alias = session.scalar(select(NationalityAliasV2).where(NationalityAliasV2.country_qid == qid, NationalityAliasV2.language == lang).order_by(NationalityAliasV2.alias_key)) if qid else None
        source = self._source(session, alias.source_id if alias else (join.source_id if join else None))
        if status == "MATCHED" and alias and ne:
            provenance = {"source": source, "join_status": join.join_status, "match_method": join.match_method, "natural_earth_id": ne.natural_earth_id, "natural_earth_version": "5.1.1"}
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "EXACT", qid), level_code="EXACT", rank=0, label_en=alias.alias_text if lang == "en" else None, label_ar=alias.alias_text if lang == "ar" else None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.iso_a2, source=source, verification_status="SOURCE_VERIFIED", is_exact=True, is_local_only=True, provenance=provenance, extra={"join_status": join.join_status, "country_qid": country.country_qid if country else qid}))
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "SUBREGION", ne.subregion), level_code="SUBREGION", rank=1, label_en=ne.subregion, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.subregion, source=source, verification_status="SOURCE_VERIFIED", provenance=provenance))
            candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "CONTINENT", ne.continent), level_code="CONTINENT", rank=2, label_en=ne.continent, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=ne.continent, source=source, verification_status="SOURCE_VERIFIED", provenance={**provenance, "region_un": ne.region_un}))
        candidates.append(_candidate_dict(candidate_id=stable_id("NATIONALITY_NATURAL_EARTH", "SUPPRESSED"), level_code="SUPPRESSED", rank=3, label_en=None, label_ar=None, language=lang, taxonomy="NATURAL_EARTH", taxonomy_code=None, source=source, verification_status="CONFIGURED", is_suppression=True))
        return self._result("NATIONALITY", status, qid, candidates, reason)

    def _bank(self, session, value, lang, include_review):
        norm = normalize(value, lang)
        aliases = session.scalars(select(BankAlias).where(BankAlias.normalized_alias == norm, BankAlias.language == lang, BankAlias.enabled_for_lookup.is_(True))).all()
        if include_review and not aliases:
            aliases = session.scalars(select(BankAlias).where(BankAlias.normalized_alias == norm, BankAlias.language == lang)).all()
        ids = {row.bank_id for row in aliases}
        if not ids:
            ids = {row.bank_id for row in session.scalars(select(Bank)).all() if normalize(row.name_en, "en") == norm or (row.name_ar and normalize(row.name_ar, "ar") == norm)}
        if len(ids) > 1:
            return self._bank_fallback("AMBIGUOUS", "ALIAS_COLLISION", lang)
        if not ids:
            return self._bank_fallback("NOT_FOUND", "UNRECOGNIZED_BANK", lang)
        bank_id = next(iter(ids))
        rows = session.scalars(select(BankCandidate).where(BankCandidate.bank_id == bank_id).order_by(BankCandidate.specificity_rank)).all()
        return self._result("BANK", "MATCHED", bank_id, [self._bank_row(session, row, lang) for row in rows])

    def _bank_row(self, session, row, lang):
        source = self._source(session, row.source_id)
        return _candidate_dict(candidate_id=row.candidate_id, level_code=row.level_code, rank=row.specificity_rank, label_en=row.label_en, label_ar=row.label_ar, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=row.finance_model, source=source, verification_status=row.verification_status, is_exact=row.is_exact, is_local_only=row.is_local_only, is_suppression=row.is_suppression, provenance={"source": source, "evidence_status": row.evidence_status, "disclosure_approved": row.disclosure_approved}, extra={"category_population_count": row.category_population_count, "finance_model": row.finance_model, "disclosure_approved": row.disclosure_approved})

    def _bank_fallback(self, status, reason, lang):
        labels = [("BANKING_INSTITUTION", "Banking institution", "مؤسسة مصرفية"), ("FINANCIAL_INSTITUTION", "Financial institution", "مؤسسة مالية")]
        candidates = [_candidate_dict(candidate_id=stable_id("BANK_FALLBACK", code), level_code=code, rank=index, label_en=en, label_ar=ar, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED") for index, (code, en, ar) in enumerate(labels)]
        candidates.append(_candidate_dict(candidate_id=stable_id("BANK_FALLBACK", "SUPPRESSED"), level_code="SUPPRESSED", rank=2, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_BANK", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True))
        return self._result("BANK", status, None, candidates, reason)

    def _organization(self, session, entity_type, value, lang, include_review):
        rows = session.scalars(select(OrganizationAlias).where(OrganizationAlias.normalized_alias == normalize(value, lang), OrganizationAlias.language == lang, OrganizationAlias.enabled_for_lookup.is_(True))).all()
        ids = {row.organization_qid for row in rows}
        if len(ids) > 1:
            return self._organization_fallback(entity_type, lang, "AMBIGUOUS", "ALIAS_COLLISION")
        if not ids:
            return self._organization_fallback(entity_type, lang, "NOT_FOUND", "UNRECOGNIZED_ORGANIZATION")
        qid = next(iter(ids))
        org = session.get(Organization, qid)
        if session.scalar(select(OrganizationExclusion.exclusion_id).where(OrganizationExclusion.organization_qid == qid)):
            return self._organization_fallback(entity_type, lang, "EXCLUDED", "EXCLUDED_ORGANIZATION")
        if entity_type in {"CORPORATION", "UNIVERSITY"} and org.semantic_kind != entity_type:
            return self._organization_fallback(entity_type, lang, "NOT_FOUND", "ENTITY_KIND_MISMATCH")
        kind = org.semantic_kind if entity_type == "ORGANIZATION" else entity_type
        label_en = org.name_en or ("University" if kind == "UNIVERSITY" else "Company" if kind == "CORPORATION" else "Organization")
        label_ar = org.name_ar
        source = self._source(session, org.source_id)
        verified_identity = org.identity_verification_status in {"VERIFIED", "APPROVED", "OFFICIAL"} and org.import_decision in {"VERIFIED", "APPROVED"}
        status = "MATCHED" if verified_identity else "REVIEW_ONLY"
        candidates = [_candidate_dict(candidate_id=stable_id("ORG", qid, "EXACT"), level_code="EXACT", rank=0, label_en=label_en, label_ar=label_ar, language=lang, taxonomy="WIKIDATA_ORGANIZATION", taxonomy_code=qid, source=source, verification_status=org.identity_verification_status, is_exact=True, is_local_only=True, provenance={"source": source, "import_decision": org.import_decision, "review_flags": org.review_flags})]
        generic = {"UNIVERSITY": ("ORGANIZATION_GENERIC", "University", "جامعة"), "CORPORATION": ("ORGANIZATION_GENERIC", "Company", "شركة"), "ORGANIZATION": ("ORGANIZATION_GENERIC", "Organization", "منظمة")}[kind]
        candidates.append(_candidate_dict(candidate_id=stable_id("ORG", kind, "GENERIC"), level_code=generic[0], rank=1, label_en=generic[1], label_ar=generic[2], language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"))
        for link in session.scalars(select(OrganizationIndustry).where(OrganizationIndustry.organization_qid == qid)).all():
            mapping = session.get(IndustryQIDMapping, link.mapping_id) if link.mapping_id else None
            industry_verified = verified_identity and link.verification_status in {"VERIFIED", "APPROVED"} and mapping is not None and mapping.review_status in {"VERIFIED", "APPROVED"}
            if mapping is not None and (industry_verified or include_review):
                candidates.append(_candidate_dict(candidate_id=stable_id("ORG", qid, link.link_id), level_code=link.subcategory_code or link.sector_code or "INDUSTRY", rank=2, label_en=mapping.subcategory_label_en, label_ar=mapping.subcategory_label_ar, language=lang, taxonomy="FINAIR_INDUSTRY", taxonomy_code=link.subcategory_code or link.sector_code, source=self._source(session, mapping.source_id), verification_status="VERIFIED" if industry_verified else "REVIEW_ONLY", dimension="INDUSTRY", provenance={"source": self._source(session, mapping.source_id), "organization_industry_status": link.verification_status, "mapping_status": mapping.review_status}, extra={"review_only": not industry_verified}))
        candidates.append(_candidate_dict(candidate_id=stable_id("ORG", qid, "SUPPRESSED"), level_code="SUPPRESSED", rank=99, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True))
        return self._result(entity_type, status, qid, sorted(candidates, key=lambda row: (row["specificity_rank"], row["candidate_id"])))

    def _organization_fallback(self, entity_type, lang, status, reason):
        kind = entity_type if entity_type in {"CORPORATION", "UNIVERSITY"} else "ORGANIZATION"
        code, en, ar = ("ORGANIZATION_GENERIC", "University", "جامعة") if kind == "UNIVERSITY" else ("ORGANIZATION_GENERIC", "Company", "شركة") if kind == "CORPORATION" else ("ORGANIZATION_GENERIC", "Organization", "منظمة")
        candidates = [_candidate_dict(candidate_id=stable_id("ORG_FALLBACK", code), level_code=code, rank=0, label_en=en, label_ar=ar, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED"), _candidate_dict(candidate_id=stable_id("ORG_FALLBACK", "SUPPRESSED"), level_code="SUPPRESSED", rank=1, label_en=None, label_ar=None, language=lang, taxonomy="FINAIR_ORGANIZATION", taxonomy_code=None, source="Finaira taxonomy", verification_status="CONFIGURED", is_suppression=True)]
        return self._result(entity_type, status, None, candidates, reason)

    def _government(self, session, value, lang, include_review):
        aliases = session.scalars(select(GovernmentAlias).where(GovernmentAlias.normalized_alias == normalize(value, lang), GovernmentAlias.language == lang)).all()
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
        from .age_date import parse_date
        try:
            d = parse_date(value, context.get("date_format"))
        except ValueError as exc:
            return self._result("DATE", str(exc), None, [], str(exc))
        quarter = (d.month - 1) // 3 + 1
        month_start = d.replace(day=1)
        month_end = d.replace(day=calendar.monthrange(d.year, d.month)[1])
        quarter_start = date(d.year, 3 * (quarter - 1) + 1, 1)
        quarter_end = date(d.year, 3 * quarter, calendar.monthrange(d.year, 3 * quarter)[1])
        year_start, year_end = date(d.year, 1, 1), date(d.year, 12, 31)
        values = [("EXACT", f"{d.day} {EN_MONTHS[d.month - 1]} {d.year}", f"{d.day} {AR_MONTHS[d.month - 1]} {d.year}", d, d, "date"), ("MONTH", f"{EN_MONTHS[d.month - 1]} {d.year}", f"{AR_MONTHS[d.month - 1]} {d.year}", month_start, month_end, "month"), ("QUARTER", f"Q{quarter} {d.year}", f"الربع {quarter} من {d.year}", quarter_start, quarter_end, "quarter"), ("YEAR", str(d.year), str(d.year), year_start, year_end, "year"), ("SUPPRESSED", "Date unspecified", "التاريخ غير محدد", None, None, "suppression")]
        candidates = [_candidate_dict(candidate_id=stable_id("DATE_GREGORIAN", code, d.isoformat()), level_code=code, rank=index, label_en=en, label_ar=ar, language=lang, taxonomy="Gregorian", taxonomy_code=None, source="Finaira policy", verification_status="CONFIGURED", is_exact=code == "EXACT", is_local_only=code == "EXACT", is_suppression=code == "SUPPRESSED", extra={"interval_start": lo.isoformat() if lo else None, "interval_end": hi.isoformat() if hi else None, "interval_width": (hi - lo).days + 1 if lo and hi else None, "temporal_precision": precision}) for index, (code, en, ar, lo, hi, precision) in enumerate(values)]
        return self._result("DATE", "VERIFIED", None, candidates)

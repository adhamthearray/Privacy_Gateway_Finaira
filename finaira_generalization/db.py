from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, inspect, UniqueConstraint, Index, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase): pass

class DataSource(Base):
    __tablename__ = "data_sources"
    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    version: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(500))
    retrieved_at: Mapped[str] = mapped_column(String(40), default=lambda: datetime.now(timezone.utc).isoformat())
    license: Mapped[str | None] = mapped_column(String(300))
    checksum: Mapped[str | None] = mapped_column(String(64))

class Occupation(Base):
    __tablename__ = "occupations"
    occupation_id: Mapped[str] = mapped_column(String(300), primary_key=True)
    label_ar: Mapped[str | None] = mapped_column(Text)
    label_en: Mapped[str | None] = mapped_column(Text)
    isco_code: Mapped[str | None] = mapped_column(String(4), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    review_status: Mapped[str] = mapped_column(String(30), default="OFFICIAL")

class OccupationAlias(Base):
    __tablename__ = "occupation_aliases"
    alias_id: Mapped[int] = mapped_column(primary_key=True)
    occupation_id: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_id"), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    review_status: Mapped[str] = mapped_column(String(30), default="OFFICIAL")

class IscoGroup(Base):
    __tablename__ = "isco_groups"
    isco_code: Mapped[str] = mapped_column(String(4), primary_key=True)
    parent_code: Mapped[str | None] = mapped_column(String(4), index=True)
    level: Mapped[int] = mapped_column(Integer)
    label_ar: Mapped[str | None] = mapped_column(Text)
    label_en: Mapped[str | None] = mapped_column(Text)
    arabic_label_status: Mapped[str] = mapped_column(String(30), default="MISSING")

class NationalityAlias(Base):
    __tablename__ = "nationality_aliases"
    alias_id: Mapped[int] = mapped_column(primary_key=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    country_iso2: Mapped[str] = mapped_column(String(2), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    review_status: Mapped[str] = mapped_column(String(30), default="OFFICIAL")

class Country(Base):
    __tablename__ = "countries"
    iso2: Mapped[str] = mapped_column(String(2), primary_key=True)
    country_ar: Mapped[str | None] = mapped_column(Text)
    country_en: Mapped[str | None] = mapped_column(Text)
    m49_code: Mapped[str | None] = mapped_column(String(3))
    subregion_code: Mapped[str | None] = mapped_column(String(3))
    subregion_ar: Mapped[str | None] = mapped_column(Text)
    subregion_en: Mapped[str | None] = mapped_column(Text)
    region_code: Mapped[str | None] = mapped_column(String(3))
    region_ar: Mapped[str | None] = mapped_column(Text)
    region_en: Mapped[str | None] = mapped_column(Text)

class AgeBand(Base):
    __tablename__ = "age_bands"
    band_id: Mapped[int] = mapped_column(primary_key=True)
    scheme: Mapped[str] = mapped_column(String(50))
    min_age: Mapped[int] = mapped_column(Integer)
    max_age: Mapped[int | None] = mapped_column(Integer)
    label_ar: Mapped[str] = mapped_column(Text)
    label_en: Mapped[str] = mapped_column(Text)

class DateRule(Base):
    __tablename__ = "date_rules"
    rule_id: Mapped[int] = mapped_column(primary_key=True)
    precision: Mapped[str] = mapped_column(String(20))
    calendar: Mapped[str] = mapped_column(String(30))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class AgeSchemeRule(Base):
    __tablename__ = "age_scheme_rules"
    scheme_id: Mapped[str] = mapped_column(ForeignKey("generalization_schemes.scheme_id"), primary_key=True)
    band_id: Mapped[int] = mapped_column(ForeignKey("age_bands.band_id"), primary_key=True)

class DateSchemeRule(Base):
    __tablename__ = "date_scheme_rules"
    scheme_id: Mapped[str] = mapped_column(ForeignKey("generalization_schemes.scheme_id"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("date_rules.rule_id"), primary_key=True)

class GeneralizationScheme(Base):
    __tablename__ = "generalization_schemes"
    scheme_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), index=True)
    scheme_name: Mapped[str] = mapped_column(String(120))
    taxonomy_name: Mapped[str] = mapped_column(String(80))
    taxonomy_version: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.source_id"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class GeneralizationLevel(Base):
    __tablename__ = "generalization_levels"
    level_id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("generalization_schemes.scheme_id"), index=True)
    level_code: Mapped[str] = mapped_column(String(40))
    specificity_rank: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    representation_kind: Mapped[str] = mapped_column(String(40))
    is_exact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suppression: Mapped[bool] = mapped_column(Boolean, default=False)
    default_local_only: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("scheme_id", "level_code", name="uq_level_scheme_code"), UniqueConstraint("scheme_id", "specificity_rank", name="uq_level_scheme_rank"))

class GeneralizationCandidate(Base):
    __tablename__ = "generalization_candidates"
    candidate_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("generalization_schemes.scheme_id"), index=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("generalization_levels.level_id"), index=True)
    canonical_entity_id: Mapped[str | None] = mapped_column(String(300), index=True)
    taxonomy_code: Mapped[str | None] = mapped_column(String(20), index=True)
    parent_candidate_id: Mapped[str | None] = mapped_column(ForeignKey("generalization_candidates.candidate_id"), index=True)
    label_ar: Mapped[str | None] = mapped_column(Text)
    label_en: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.source_id"))
    review_status: Mapped[str] = mapped_column(String(30), default="OFFICIAL")
    derivation_method: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[str] = mapped_column(String(40), default=lambda: datetime.now(timezone.utc).isoformat())

class CandidateMetadata(Base):
    __tablename__ = "candidate_metadata"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("generalization_candidates.candidate_id"), primary_key=True)
    specificity_rank: Mapped[int] = mapped_column(Integer)
    taxonomy_depth: Mapped[int | None] = mapped_column(Integer)
    underlying_category_count: Mapped[int | None] = mapped_column(Integer)
    is_exact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suppression: Mapped[bool] = mapped_column(Boolean, default=False)
    is_local_only: Mapped[bool] = mapped_column(Boolean, default=False)
    preserves_exact_value: Mapped[bool] = mapped_column(Boolean, default=False)
    preserves_category: Mapped[bool] = mapped_column(Boolean, default=False)
    preserves_entity_identity: Mapped[bool] = mapped_column(Boolean, default=False)
    preserves_numeric_precision: Mapped[bool] = mapped_column(Boolean, default=False)
    representation_kind: Mapped[str] = mapped_column(String(40))
    verification_status: Mapped[str] = mapped_column(String(30))
    interval_start: Mapped[str | None] = mapped_column(String(40))
    interval_end: Mapped[str | None] = mapped_column(String(40))
    interval_width: Mapped[int | None] = mapped_column(Integer)

class CandidateProvenance(Base):
    __tablename__ = "candidate_provenance"
    provenance_id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("generalization_candidates.candidate_id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.source_id"))
    source_version: Mapped[str | None] = mapped_column(String(100))
    source_checksum: Mapped[str | None] = mapped_column(String(64))
    derivation_method: Mapped[str] = mapped_column(String(80))
    validation_status: Mapped[str] = mapped_column(String(30))
    review_status: Mapped[str] = mapped_column(String(30))
    review_date: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

class OccupationCandidateRef(Base):
    __tablename__ = "occupation_candidate_refs"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("generalization_candidates.candidate_id"), primary_key=True)
    occupation_id: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_id"), index=True)

class NationalityCandidateRef(Base):
    __tablename__ = "nationality_candidate_refs"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("generalization_candidates.candidate_id"), primary_key=True)
    iso2: Mapped[str] = mapped_column(ForeignKey("countries.iso2"), index=True)

class OccupationIscoRef(Base):
    __tablename__ = "occupation_isco_refs"
    occupation_id: Mapped[str] = mapped_column(ForeignKey("occupations.occupation_id"), primary_key=True)
    isco_code: Mapped[str] = mapped_column(ForeignKey("isco_groups.isco_code"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.source_id"))

class NationalityAliasCountryRef(Base):
    __tablename__ = "nationality_alias_country_refs"
    alias_id: Mapped[int] = mapped_column(ForeignKey("nationality_aliases.alias_id"), primary_key=True)
    iso2: Mapped[str] = mapped_column(ForeignKey("countries.iso2"), index=True)

class M49Region(Base):
    __tablename__ = "m49_regions"
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    parent_code: Mapped[str | None] = mapped_column(ForeignKey("m49_regions.code"), index=True)
    level: Mapped[int] = mapped_column(Integer)
    label_ar: Mapped[str | None] = mapped_column(Text)
    label_en: Mapped[str | None] = mapped_column(Text)

class CountryM49Link(Base):
    __tablename__ = "country_m49_links"
    iso2: Mapped[str] = mapped_column(ForeignKey("countries.iso2"), primary_key=True)
    subregion_code: Mapped[str | None] = mapped_column(ForeignKey("m49_regions.code"))
    region_code: Mapped[str | None] = mapped_column(ForeignKey("m49_regions.code"))


# Handoff v2 tables are additive.  The legacy ESCO/ISCO and M49 tables above
# remain available for historical compatibility; runtime nationality lookup
# uses the Natural Earth tables below.
class ImportBatch(Base):
    __tablename__ = "import_batches"
    batch_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    started_at: Mapped[str] = mapped_column(String(40))
    completed_at: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    manifest_path: Mapped[str | None] = mapped_column(Text)
    counts_json: Mapped[str | None] = mapped_column(Text)
    error_text: Mapped[str | None] = mapped_column(Text)


class NaturalEarthCountry(Base):
    __tablename__ = "natural_earth_countries"
    natural_earth_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    wikidata_qid: Mapped[str | None] = mapped_column(String(20), index=True)
    iso_a2: Mapped[str | None] = mapped_column(String(2), index=True)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    subregion: Mapped[str | None] = mapped_column(Text)
    region_un: Mapped[str | None] = mapped_column(Text)
    continent: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    source_version: Mapped[str] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("wikidata_qid", name="uq_ne_country_wikidata_qid"),)


class NaturalEarthCountryAlias(Base):
    __tablename__ = "natural_earth_country_aliases"
    alias_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    natural_earth_id: Mapped[str] = mapped_column(ForeignKey("natural_earth_countries.natural_earth_id"), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    alias_kind: Mapped[str] = mapped_column(String(30))
    source_property: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    verification_status: Mapped[str] = mapped_column(String(40), default="SOURCE_VERIFIED")
    enabled_for_lookup: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("natural_earth_id", "normalized_alias", "language", name="uq_ne_country_alias"),)


class NationalityCountry(Base):
    __tablename__ = "nationality_countries"
    country_qid: Mapped[str] = mapped_column(String(20), primary_key=True)
    iso2: Mapped[str] = mapped_column(String(2), index=True)
    country_label: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    verification_status: Mapped[str] = mapped_column(String(40), default="SOURCE_VERIFIED")


class NationalityAliasV2(Base):
    __tablename__ = "nationality_aliases_v2"
    alias_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    country_qid: Mapped[str] = mapped_column(ForeignKey("nationality_countries.country_qid"), index=True)
    iso2: Mapped[str] = mapped_column(String(2), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    verification_status: Mapped[str] = mapped_column(String(40), default="SOURCE_VERIFIED")


class NationalityGeoJoin(Base):
    __tablename__ = "nationality_geo_joins"
    country_qid: Mapped[str] = mapped_column(ForeignKey("nationality_countries.country_qid"), primary_key=True)
    iso2: Mapped[str] = mapped_column(String(2), index=True)
    natural_earth_id: Mapped[str | None] = mapped_column(ForeignKey("natural_earth_countries.natural_earth_id"), index=True)
    join_status: Mapped[str] = mapped_column(String(30), index=True)
    match_method: Mapped[str | None] = mapped_column(String(20))
    audit_note: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class Bank(Base):
    __tablename__ = "banks"
    bank_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    cbe_list_number: Mapped[str | None] = mapped_column(String(20))
    name_en: Mapped[str] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    finance_model: Mapped[str] = mapped_column(String(20), index=True)
    finance_model_label_en: Mapped[str] = mapped_column(Text)
    finance_model_label_ar: Mapped[str] = mapped_column(Text)
    classification_rule: Mapped[str] = mapped_column(String(80))
    evidence_status: Mapped[str] = mapped_column(String(80))
    evidence_confidence: Mapped[str | None] = mapped_column(String(30))
    as_of_date: Mapped[str | None] = mapped_column(String(20))
    evidence_review_status: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class BankAlias(Base):
    __tablename__ = "bank_aliases"
    alias_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.bank_id"), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    alias_kind: Mapped[str | None] = mapped_column(String(50))
    review_status: Mapped[str] = mapped_column(String(50))
    enabled_for_lookup: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    __table_args__ = (UniqueConstraint("normalized_alias", "language", "bank_id", name="uq_bank_alias"),)


class BankEvidence(Base):
    __tablename__ = "bank_evidence"
    evidence_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.bank_id"), index=True)
    finance_model: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(Text)
    evidence_summary_en: Mapped[str | None] = mapped_column(Text)
    source_publication_or_update: Mapped[str | None] = mapped_column(Text)
    checked_on: Mapped[str | None] = mapped_column(String(20))
    source_strength: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class BankCandidate(Base):
    __tablename__ = "bank_candidates"
    candidate_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("banks.bank_id"), index=True)
    level_code: Mapped[str] = mapped_column(String(40), index=True)
    specificity_rank: Mapped[int] = mapped_column(Integer)
    label_en: Mapped[str | None] = mapped_column(Text)
    label_ar: Mapped[str | None] = mapped_column(Text)
    finance_model: Mapped[str | None] = mapped_column(String(20))
    category_population_count: Mapped[int | None] = mapped_column(Integer)
    is_exact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_local_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suppression: Mapped[bool] = mapped_column(Boolean, default=False)
    disclosure_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_status: Mapped[str] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    derivation_method: Mapped[str] = mapped_column(String(80))
    __table_args__ = (UniqueConstraint("bank_id", "level_code", name="uq_bank_candidate_level"),)


class Organization(Base):
    __tablename__ = "organizations"
    organization_qid: Mapped[str] = mapped_column(String(20), primary_key=True)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    semantic_kind: Mapped[str] = mapped_column(String(30), index=True)
    identity_verification_status: Mapped[str] = mapped_column(String(50), index=True)
    import_decision: Mapped[str] = mapped_column(String(70), index=True)
    import_status: Mapped[str | None] = mapped_column(String(70))
    review_flags: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class OrganizationAlias(Base):
    __tablename__ = "organization_aliases"
    alias_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_qid: Mapped[str] = mapped_column(ForeignKey("organizations.organization_qid"), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    enabled_for_lookup: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_status: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    __table_args__ = (UniqueConstraint("normalized_alias", "language", "organization_qid", name="uq_org_alias"),)


class IndustryCategory(Base):
    __tablename__ = "industry_categories"
    category_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    parent_code: Mapped[str | None] = mapped_column(ForeignKey("industry_categories.category_code"), index=True)
    label_en: Mapped[str] = mapped_column(Text)
    label_ar: Mapped[str] = mapped_column(Text)
    category_kind: Mapped[str] = mapped_column(String(30))
    license: Mapped[str | None] = mapped_column(String(100))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class IndustryQIDMapping(Base):
    __tablename__ = "industry_qid_mappings"
    mapping_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    industry_qid: Mapped[str] = mapped_column(String(40), index=True)
    source_industry_label_en: Mapped[str | None] = mapped_column(Text)
    sector_code: Mapped[str | None] = mapped_column(String(50), index=True)
    subcategory_code: Mapped[str | None] = mapped_column(String(50), index=True)
    subcategory_label_en: Mapped[str | None] = mapped_column(Text)
    subcategory_label_ar: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(50), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class OrganizationIndustry(Base):
    __tablename__ = "organization_industries"
    link_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_qid: Mapped[str] = mapped_column(ForeignKey("organizations.organization_qid"), index=True)
    mapping_id: Mapped[str | None] = mapped_column(ForeignKey("industry_qid_mappings.mapping_id"), index=True)
    industry_qid: Mapped[str] = mapped_column(String(40), index=True)
    sector_code: Mapped[str | None] = mapped_column(String(50))
    subcategory_code: Mapped[str | None] = mapped_column(String(50))
    mapping_status: Mapped[str | None] = mapped_column(String(50))
    import_decision: Mapped[str] = mapped_column(String(70))
    verification_status: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class OrganizationExclusion(Base):
    __tablename__ = "organization_exclusions"
    exclusion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_qid: Mapped[str | None] = mapped_column(String(20), index=True)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_ar: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    import_decision: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class OrganizationReviewQueue(Base):
    __tablename__ = "organization_review_queue"
    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_qid: Mapped[str | None] = mapped_column(String(20), index=True)
    import_status: Mapped[str | None] = mapped_column(String(50))
    review_flags: Mapped[str | None] = mapped_column(Text)
    import_decision: Mapped[str | None] = mapped_column(String(70))
    review_reason: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentEntity(Base):
    __tablename__ = "government_entities"
    entity_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    name_ar: Mapped[str] = mapped_column(Text)
    name_en_provisional: Mapped[str | None] = mapped_column(Text)
    country_iso: Mapped[str] = mapped_column(String(2), index=True)
    organization_form_code: Mapped[str | None] = mapped_column(String(50))
    function_code: Mapped[str | None] = mapped_column(String(50))
    wikidata_qid: Mapped[str | None] = mapped_column(String(20))
    official_source_url: Mapped[str | None] = mapped_column(Text)
    identity_verification_status: Mapped[str] = mapped_column(String(50), index=True)
    function_verification_status: Mapped[str] = mapped_column(String(50))
    english_name_verification_status: Mapped[str] = mapped_column(String(50))
    enabled_for_specific_mapping: Mapped[bool] = mapped_column(Boolean, default=False)
    dataset_status: Mapped[str | None] = mapped_column(String(50))
    review_notes: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentAlias(Base):
    __tablename__ = "government_aliases"
    alias_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("government_entities.entity_id"), index=True)
    language: Mapped[str] = mapped_column(String(2), index=True)
    alias_text: Mapped[str] = mapped_column(Text)
    normalized_alias: Mapped[str] = mapped_column(Text, index=True)
    verification_status: Mapped[str] = mapped_column(String(50))
    enabled_for_lookup: Mapped[bool] = mapped_column(Boolean, default=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentCategory(Base):
    __tablename__ = "government_categories"
    category_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    label_ar: Mapped[str] = mapped_column(Text)
    label_en: Mapped[str] = mapped_column(Text)
    parent_category_code: Mapped[str | None] = mapped_column(ForeignKey("government_categories.category_code"), index=True)
    reidentification_risk_hint: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentCandidateReview(Base):
    __tablename__ = "government_candidate_reviews"
    candidate_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("government_entities.entity_id"), index=True)
    level_code: Mapped[str] = mapped_column(String(50))
    dimension: Mapped[str] = mapped_column(String(30), index=True)
    specificity_rank_branch_local: Mapped[int] = mapped_column(Integer)
    label_ar: Mapped[str | None] = mapped_column(Text)
    label_en: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(50))
    requires_policy_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    is_local_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suppression: Mapped[bool] = mapped_column(Boolean, default=False)
    default_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentEntityCategory(Base):
    __tablename__ = "government_entity_categories"
    link_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("government_entities.entity_id"), index=True)
    category_code: Mapped[str] = mapped_column(ForeignKey("government_categories.category_code"), index=True)
    dimension: Mapped[str] = mapped_column(String(30))
    verification_status: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))


class GovernmentReviewQueue(Base):
    __tablename__ = "government_review_queue"
    review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("government_entities.entity_id"), index=True)
    review_identity: Mapped[str | None] = mapped_column(String(30))
    review_current_status: Mapped[str | None] = mapped_column(String(30))
    review_function_category: Mapped[str | None] = mapped_column(String(30))
    review_english_name: Mapped[str | None] = mapped_column(String(30))
    review_wikidata_qid: Mapped[str | None] = mapped_column(String(30))
    specific_mapping_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))

def make_engine(path: str | Path):
    engine = create_engine(f"sqlite:///{Path(path)}", future=True)
    return engine


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def init_db(path: str | Path):
    engine = make_engine(path)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS build_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return engine

def schema_tables(path: str | Path):
    return inspect(make_engine(path)).get_table_names()

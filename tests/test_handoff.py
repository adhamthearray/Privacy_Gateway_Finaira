from pathlib import Path
import csv

from sqlalchemy import text

from finaira_generalization import GeneralizationDB, import_handoff
from finaira_generalization.db import make_engine


DB = Path("data/processed/finaira_generalization.db")


def scalar(sql):
    with make_engine(DB).connect() as connection:
        return connection.execute(text(sql)).scalar()


def test_natural_earth_join_and_runtime_source():
    assert scalar("select count(*) from nationality_aliases_v2 where verification_status='SOURCE_VERIFIED'") == 857
    assert scalar("select count(*) from nationality_aliases_v2 where verification_status='REVIEWED'") == 59
    assert scalar("select count(*) from nationality_countries") == 239
    assert scalar("select count(*) from natural_earth_countries") == 258
    assert scalar("select count(*) from natural_earth_country_aliases where verification_status='REVIEWED'") == 30
    assert scalar("select count(*) from nationality_geo_joins where join_status='MATCHED_QID'") == 230
    result = GeneralizationDB(DB).get_candidates("NATIONALITY", "Egyptian", "en")
    assert result["resolution_status"] == "MATCHED"
    assert all(candidate["taxonomy"] == "NATURAL_EARTH" for candidate in result["candidates"])
    assert result["candidates"][1]["representation"] == "Northern Africa"


def test_nationality_variant_review_queue_is_gated():
    queue = Path("reports/nationality_improvement/nationality_variant_review_queue.csv")
    with queue.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len({row["corpus_value"] for row in rows if row["review_decision"] == "APPROVED"}) == 59
    assert sum(row["review_decision"] == "PENDING" for row in rows) == 15
    assert sum(row["review_decision"] == "REJECTED" for row in rows) == 1
    assert scalar("select count(*) from nationality_aliases_v2") == 916
    assert scalar("select count(*) from nationality_aliases_v2 where verification_status='REVIEWED'") == 59
    assert scalar("select count(*) from nationality_alias_review_provenance") == 67


def test_reviewed_nationalities_and_pending_gates():
    for value in ("الفلسطينيون", "السوريين", "اللبناني", "المصريين", "العراقيون", "الامريكى"):
        result = GeneralizationDB(DB).get_candidates("NATIONALITY", value, "ar")
        assert result["resolution_status"] == "MATCHED", value
    assert GeneralizationDB(DB).get_candidates("NATIONALITY", "الفلسطينيون", "ar")["canonical_id"] == "Q23792"
    assert GeneralizationDB(DB).get_candidates("NATIONALITY", "Egyptian", "en")["resolution_status"] == "MATCHED"
    pending = GeneralizationDB(DB).get_candidates("NATIONALITY", "اللبنانيي", "ar")
    pending_review = GeneralizationDB(DB).get_candidates("NATIONALITY", "اللبنانيي", "ar", include_review_candidates=True)
    assert pending["resolution_status"] == "NOT_FOUND"
    assert pending_review["resolution_status"] == "NOT_FOUND"
    assert [candidate["level_code"] for candidate in pending["candidates"]] == ["SUPPRESSED"]
    assert scalar("select count(*) from nationality_geo_joins where join_status='UNMATCHED'") == 7


def test_country_resolves_directly_from_natural_earth():
    result = GeneralizationDB(DB).get_candidates("COUNTRY", "Egypt", "en")
    assert result["resolution_status"] == "MATCHED"
    assert result["canonical_id"] == "EG"
    assert [candidate["level_code"] for candidate in result["candidates"]] == ["EXACT", "SUBREGION", "REGION_UN", "CONTINENT", "SUPPRESSED"]
    assert result["candidates"][0]["is_local_only"] is True
    assert result["candidates"][1]["representation"] == "Northern Africa"
    unknown = GeneralizationDB(DB).get_candidates("COUNTRY", "not-a-country", "en")
    assert unknown["resolution_status"] == "NOT_FOUND"
    assert [candidate["level_code"] for candidate in unknown["candidates"]] == ["SUPPRESSED"]


def test_country_wikidata_alias_layer_is_source_verified():
    assert scalar("select count(*) from natural_earth_country_aliases") > 0
    alias = scalar("select alias_text from natural_earth_country_aliases where language='en' order by alias_id limit 1")
    result = GeneralizationDB(DB).get_candidates("COUNTRY", alias, "en")
    assert result["resolution_status"] == "MATCHED"
    assert result["candidates"][0]["verification_status"] == "SOURCE_VERIFIED"
    assert result["candidates"][0]["provenance"]["match_method"] == "WIKIDATA_COUNTRY_ALIAS"


def test_reviewed_current_country_variants_and_exclusions():
    for value, language in (("UK", "en"), ("USA", "en"), ("دولة فلسطين", "ar"), ("موزامبيق", "ar"), ("أرتيريا", "ar"), ("نيوزلندا", "ar")):
        result = GeneralizationDB(DB).get_candidates("COUNTRY", value, language)
        assert result["resolution_status"] == "MATCHED", value
        assert result["candidates"][0]["verification_status"] == "REVIEWED", value
    for value, language in (("KSA", "en"), ("الاتحاد السوفيتي", "ar"), ("نابلس", "ar")):
        result = GeneralizationDB(DB).get_candidates("COUNTRY", value, language)
        assert result["resolution_status"] == "NOT_FOUND", value
        assert [candidate["level_code"] for candidate in result["candidates"]] == ["SUPPRESSED"]
    queue = Path("reports/ner_v1_generalization/country_review_queue.csv")
    with queue.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 86
    assert sum(row["review_decision"] == "APPROVED" for row in rows) == 31
    assert sum(row["review_decision"] == "PENDING" for row in rows) == 25
    assert sum(row["review_decision"] == "REJECTED" for row in rows) == 30


def test_bank_authority_and_evidence_flags():
    assert scalar("select count(*) from banks") == 37
    assert scalar("select count(*) from bank_candidates") == 185
    assert scalar("select count(*) from bank_evidence") == 24
    assert scalar("select count(*) from banks where finance_model='CONVENTIONAL'") == 24
    assert scalar("select count(*) from banks where finance_model='MIXED'") == 9
    assert scalar("select count(*) from banks where finance_model='ISLAMIC'") == 4
    result = GeneralizationDB(DB).get_candidates("BANK", "Banque Misr", "en")
    assert result["resolution_status"] == "MATCHED"
    assert [candidate["level_code"] for candidate in result["candidates"]] == ["EXACT", "FINANCE_MODEL", "BANKING_INSTITUTION", "FINANCIAL_INSTITUTION", "SUPPRESSED"]
    assert result["candidates"][0]["is_local_only"] is True
    assert all(candidate["metadata"].get("disclosure_approved", False) is False for candidate in result["candidates"])
    assert scalar("select count(*) from banks where name_ar is null") == 37
    assert scalar("select count(*) from bank_aliases where review_status='APPROVED_BY_USER'") == 47
    assert scalar("select count(*) from bank_aliases where enabled_for_lookup=1") == 86


def test_organization_pending_identity_gates_specific_industry():
    assert scalar("select count(*) from organizations") == 312
    assert scalar("select count(*) from organizations where semantic_kind='CORPORATION'") == 312
    assert scalar("select count(*) from organizations where semantic_kind='UNIVERSITY'") == 0
    assert scalar("select count(*) from industry_categories where category_code <> 'ORGANIZATION'") == 63
    result = GeneralizationDB(DB).get_candidates("UNIVERSITY", "New Cairo Technological University", "en")
    assert result["resolution_status"] == "REVIEW_ONLY"
    assert result["entity_type"] == "CORPORATION"
    assert result["candidates"][0]["provenance"]["canonical_entity_type"] == "CORPORATION"
    assert all(candidate["level_code"] not in {"MFG_FOOD", "ICT_SOFTWARE"} for candidate in result["candidates"])
    organization = GeneralizationDB(DB).get_candidates("ORGANIZATION", "New Cairo Technological University", "en")
    assert organization["entity_type"] == "CORPORATION"
    assert organization["candidates"][1]["representation"] == "Company"
    company = GeneralizationDB(DB).get_candidates("CORPORATION", "Edita Food Industries S.A.E.", "en")
    assert all(candidate["level_code"] not in {"MFG_FOOD", "MFG"} for candidate in company["candidates"])
    review = GeneralizationDB(DB).get_candidates("CORPORATION", "Edita Food Industries S.A.E.", "en", include_review_candidates=True)
    assert any(candidate["verification_status"] == "REVIEW_ONLY" for candidate in review["candidates"] if candidate["level_code"] not in {"EXACT", "COMPANY", "SUPPRESSED"})
    unknown = GeneralizationDB(DB).get_candidates("CORPORATION", "not a real company", "en")
    assert unknown["resolution_status"] == "NOT_FOUND"
    assert [candidate["level_code"] for candidate in unknown["candidates"]] == ["ORGANIZATION_GENERIC", "SUPPRESSED"]


def test_government_review_default_and_optional_branches():
    assert scalar("select count(*) from government_entities") == 12
    assert scalar("select count(*) from government_aliases where verification_status='APPROVED_BY_USER'") == 24
    assert scalar("select count(*) from government_aliases where enabled_for_lookup=1") == 24
    assert scalar("select count(*) from government_categories") == 17
    result = GeneralizationDB(DB).get_candidates("GOVERNMENT_ENTITY", "وزارة المالية", "ar")
    assert result["resolution_status"] == "REVIEW_ONLY"
    assert [candidate["level_code"] for candidate in result["candidates"]] == ["EXACT", "GOVERNMENT_ENTITY_GENERIC", "SUPPRESSED"]
    assert all(candidate["level_code"] not in {"PUBLIC_FINANCE", "PUBLIC_MINISTRY"} for candidate in result["candidates"])
    review = GeneralizationDB(DB).get_candidates("GOVERNMENT_ENTITY", "وزارة المالية", "ar", include_review_candidates=True)
    assert any(candidate["dimension"] == "FUNCTION" for candidate in review["candidates"])
    unknown = GeneralizationDB(DB).get_candidates("GOVERNMENT_ENTITY", "unknown", "en")
    assert unknown["resolution_status"] == "NOT_FOUND"
    assert unknown["candidates"][0]["representation"] == "Government entity"


def test_fk_integrity_and_idempotent_handoff_import():
    before = {table: scalar(f"select count(*) from {table}") for table in ("banks", "bank_candidates", "organizations", "government_entities", "natural_earth_country_aliases", "nationality_aliases_v2", "nationality_alias_review_provenance")}
    import_handoff(DB, report_dir="reports", backup=False)
    after_first = {table: scalar(f"select count(*) from {table}") for table in before}
    import_handoff(DB, report_dir="reports", backup=False)
    after_second = {table: scalar(f"select count(*) from {table}") for table in before}
    assert after_first == before
    assert after_second == before
    with make_engine(DB).connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert connection.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []

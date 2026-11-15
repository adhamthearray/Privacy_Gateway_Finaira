import shutil
import sqlite3
from pathlib import Path

from finaira import Entity, PipelineRequest, PrivacyPipeline
from finaira_generalization import GeneralizationDB
from scripts.import_bank_identity_model import import_bank_identity_model


DB = Path("data/processed/finaira_generalization.db")
SOURCE = Path("data/sources/bank/model_safe_2026")


def safe_key(result):
    return next(candidate["representation"] for candidate in result["candidates"] if candidate["level_code"] == "MODEL_SAFE_GROUP")


def test_model_safe_tables_and_source_counts_are_integrated():
    with sqlite3.connect(DB) as connection:
        assert connection.execute("select count(*) from bank_identity_model_records").fetchone()[0] == 303
        assert connection.execute("select count(*) from bank_model_aliases").fetchone()[0] == 1524
        assert connection.execute("select count(*) from bank_generalization_cohorts").fetchone()[0] == 227
        assert connection.execute("select count(*) from bank_generalization_forms").fetchone()[0] == 606
        assert connection.execute("select count(*) from bank_generalization_forms where level_code='FINANCE_MODEL'").fetchone()[0] == 303
        assert connection.execute("select count(*) from bank_generalization_forms where level_code='MODEL_SAFE_GROUP'").fetchone()[0] == 303
        assert connection.execute("select count(*) from bank_model_relationship_evidence").fetchone()[0] == 21
        assert connection.execute("select count(*) from bank_model_do_not_merge").fetchone()[0] == 12
        assert connection.execute("select count(*) from bank_model_research_corrections").fetchone()[0] == 30
        assert connection.execute("select count(*) from bank_model_evidence_notes").fetchone()[0] == 14
        assert connection.execute("select count(*) from banks").fetchone()[0] == 302


def test_model_safe_import_is_idempotent_and_preserves_legacy_bank_rows(tmp_path):
    temp_db = tmp_path / "finaira_generalization.db"
    shutil.copy2(DB, temp_db)
    first = import_bank_identity_model(temp_db, SOURCE, tmp_path / "report", backup=False)
    second = import_bank_identity_model(temp_db, SOURCE, tmp_path / "report", backup=False)
    assert first["input_records"] == second["input_records"] == 303
    assert first["duplicate_source_records_mapped"] == second["duplicate_source_records_mapped"] == 1
    assert second["aliases_enabled_for_lookup"] == 525
    with sqlite3.connect(temp_db) as connection:
        assert connection.execute("select count(*) from banks").fetchone()[0] == 302
        assert connection.execute("select count(*) from bank_identity_model_records").fetchone()[0] == 303
        assert connection.execute("select count(*) from bank_model_aliases").fetchone()[0] == 1524
        assert connection.execute("select count(*) from bank_generalization_cohorts").fetchone()[0] == 227
        assert connection.execute("select count(*) from bank_generalization_forms").fetchone()[0] == 606


def test_bank_safe_candidate_is_linked_to_persisted_generalization_form():
    result = GeneralizationDB(DB).get_candidates("BANK", "Emirates NBD Bank", "en")
    candidate = next(item for item in result["candidates"] if item["level_code"] == "MODEL_SAFE_GROUP")
    form_id = candidate["provenance"]["generalization_form_id"]
    with sqlite3.connect(DB) as connection:
        row = connection.execute(
            "select safe_generalization_key, level_code, enabled_for_lookup from bank_generalization_forms where form_id = ?",
            (form_id,),
        ).fetchone()
    assert row == ("GEN_EMIRATES_NBD_CONVENTIONAL", "MODEL_SAFE_GROUP", 1)


def test_bank_model_forms_are_shared_across_banks_and_bilingual():
    db = GeneralizationDB(DB)
    conventional_a = db.get_candidates("BANK", "Emirates NBD Bank", "en")
    conventional_b = db.get_candidates("BANK", "First Abu Dhabi Bank", "en")
    islamic = db.get_candidates("BANK", "مصرف الراجحي", "ar")
    a = next(item for item in conventional_a["candidates"] if item["level_code"] == "FINANCE_MODEL")
    b = next(item for item in conventional_b["candidates"] if item["level_code"] == "FINANCE_MODEL")
    i = next(item for item in islamic["candidates"] if item["level_code"] == "FINANCE_MODEL")
    assert (a["candidate_id"], a["representation"]) == ("BANK_FINANCE_MODEL__CONVENTIONAL", "Conventional bank")
    assert (b["candidate_id"], b["representation"]) == ("BANK_FINANCE_MODEL__CONVENTIONAL", "Conventional bank")
    assert (i["candidate_id"], i["representation"]) == ("BANK_FINANCE_MODEL__ISLAMIC", "بنك إسلامي")
    assert a["provenance"]["generalization_form_id"]
    assert a["metadata"]["disclosure_approved"] is True


def test_verified_cross_country_and_model_aware_keys():
    db = GeneralizationDB(DB)
    assert safe_key(db.get_candidates("BANK", "National Bank of Egypt", "en")) == safe_key(db.get_candidates("BANK", "البنك الأهلي المصري", "ar"))
    assert safe_key(db.get_candidates("BANK", "Al Rajhi Bank", "en")) == "GEN_AL_RAJHI_BANK_ISLAMIC"
    assert safe_key(db.get_candidates("BANK", "First Abu Dhabi Bank", "en")) == "GEN_FAB_CONVENTIONAL"

    enbd = db.get_candidates("BANK", "Emirates NBD Bank", "en")
    islamic = db.get_candidates("BANK", "Emirates Islamic Bank", "en")
    assert safe_key(enbd) == "GEN_EMIRATES_NBD_CONVENTIONAL"
    assert safe_key(islamic) == "GEN_EMIRATES_NBD_ISLAMIC"
    assert enbd["candidates"][1]["provenance"]["family_id"] == islamic["candidates"][1]["provenance"]["family_id"] == "GRP_EMIRATES_NBD"

    assert safe_key(db.get_candidates("BANK", "Boubyan Bank", "en")) == "GEN_NBK_ISLAMIC"
    assert safe_key(db.get_candidates("BANK", "National Bank of Kuwait", "en")) == "GEN_NBK_CONVENTIONAL"
    assert db.get_candidates("BANK", "National Bank of Kuwait - Egypt (NBK)", "en")["resolution_status"] == "REVIEW_ONLY"


def test_explicit_collisions_and_review_required_models_do_not_auto_group():
    db = GeneralizationDB(DB)
    for value in ("Ahlibank", "Banque Misr", "BOK International Bank", "Saudi Hollandi Bank"):
        result = db.get_candidates("BANK", value, "en")
        assert result["resolution_status"] in {"REVIEW_ONLY", "AMBIGUOUS"}
        assert result["selected_candidate"] is None

    for value in ("EG_BANK_001", "EG_BANK_024"):
        with sqlite3.connect(DB) as connection:
            row = connection.execute(
                "select review_required, automatic_grouping from bank_identity_model_records where record_id = ?",
                (value,),
            ).fetchone()
        assert row == (1, 1)


def test_bank_pipeline_uses_safe_key_and_pseudonym_fallback():
    first = "Emirates NBD Bank"
    document = f"{first} worked with {first}."
    entities = [
        Entity("BANK", first, 0, len(first), "bank-1", "en"),
        Entity("BANK", first, document.rindex(first), document.rindex(first) + len(first), "bank-1", "en"),
    ]
    result = PrivacyPipeline().run(PipelineRequest(document, entities))
    assert result.status == "PASS"
    assert result.protected_document == "GEN_EMIRATES_NBD_CONVENTIONAL worked with GEN_EMIRATES_NBD_CONVENTIONAL."

    unknown = "Unresolved Bank Identity"
    fallback = PrivacyPipeline().run(PipelineRequest(unknown, [Entity("BANK", unknown, 0, len(unknown), "unknown-bank", "en")]))
    assert fallback.status == "PASS"
    assert fallback.protected_document == "__FN_BANK_0001__"

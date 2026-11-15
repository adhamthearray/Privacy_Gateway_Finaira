import shutil
import sqlite3
from pathlib import Path

from finaira_generalization import GeneralizationDB
from finaira_generalization.db import make_engine
from scripts.import_gcc_bank_audit import import_gcc_audit
from sqlalchemy import text


DB = Path("data/processed/finaira_generalization.db")
SOURCE = Path("data/sources/bank/gcc_2026")


def scalar(query, *args):
    with sqlite3.connect(DB) as connection:
        return connection.execute(query, args).fetchone()[0]


def test_gcc_audit_counts_and_source_provenance_are_integrated():
    assert scalar("select count(*) from banks") == 302
    assert scalar("select count(*) from bank_audit_classifications") == 266
    assert scalar("select count(*) from bank_relationships") == 5
    assert scalar("select count(*) from bank_aliases") == 1569
    assert scalar("select count(*) from banks where bank_id='EG_BANK_001'") == 1
    assert scalar("select count(*) from bank_audit_classifications where license_status='CONFIRMED'") == 94
    assert scalar("select count(*) from bank_audit_classifications where licensed_count_eligible=1") == 94
    assert scalar("select count(*) from bank_audit_classifications where license_status='UNVERIFIED'") == 75


def test_gcc_model_scope_status_and_relationships_are_not_collapsed():
    with sqlite3.connect(DB) as connection:
        stc = connection.execute("select banking_model, business_scope, entity_kind, license_status from bank_audit_classifications where source_record_id='SA-012'").fetchone()
        window = connection.execute("select banking_model, license_status from bank_audit_classifications where source_record_id='OM-151'").fetchone()
        alizz = connection.execute("select banking_model, license_status from bank_audit_classifications where source_record_id='OM-148'").fetchone()
        baraka_group = connection.execute("select banking_model, entity_kind, license_status, licensed_count_eligible from bank_audit_classifications where source_record_id='BH-180'").fetchone()
        parent = connection.execute("select child_bank_id, parent_bank_id, relationship_type from bank_relationships where source_record_id='OM-151'").fetchone()
        duplicate = connection.execute("select bank_id from bank_audit_classifications where source_record_id='BH-241'").fetchone()
    assert stc == ("UNKNOWN", "Digital", "Digital licensed bank", "UNVERIFIED")
    assert window == ("ISLAMIC_WINDOW", "LINKED_WINDOW")
    assert alizz == ("ISLAMIC", "RECHECK_REQUIRED")
    assert baraka_group == ("NOT_APPLICABLE", "Investment firm / holding group (not bank licence)", "NOT_APPLICABLE", 0)
    assert parent == ("OM-151", "OM-140", "ISLAMIC_WINDOW_OF")
    assert duplicate == ("BH-197",)


def test_runtime_bank_lookup_exposes_audit_and_blocks_ambiguous_aliases():
    db = GeneralizationDB(DB)
    meethaq = db.get_candidates("BANK", "Meethaq Islamic Banking", "en", include_review_candidates=True)
    assert meethaq["resolution_status"] == "REVIEW_ONLY"
    assert meethaq["canonical_id"] == "BANK_WINDOW_OM_151"
    assert meethaq["candidates"][0]["verification_status"] == "REVIEW_ONLY"
    assert meethaq["candidates"][0]["provenance"]["audit_license_status"] == "LINKED_WINDOW"
    assert meethaq["candidates"][0]["metadata"]["relationships"][0]["parent_bank_id"] == "OM-140"

    unknown_model = db.get_candidates("BANK", "STC Bank", "en", include_review_candidates=True)
    assert unknown_model["resolution_status"] == "REVIEW_ONLY"
    assert unknown_model["candidates"][0]["metadata"]["audit_classifications"][0]["banking_model"] == "UNKNOWN"

    ambiguous = db.get_candidates("BANK", "BOK International Bank", "en", include_review_candidates=True)
    assert ambiguous["resolution_status"] == "AMBIGUOUS"
    assert ambiguous["reason_code"] == "ALIAS_COLLISION"

    historical = db.get_candidates("BANK", "Saudi Hollandi Bank", "en", include_review_candidates=True)
    assert historical["resolution_status"] == "AMBIGUOUS"
    assert historical["reason_code"] == "ALIAS_COLLISION"


def test_gcc_import_is_idempotent_and_preserves_existing_data(tmp_path):
    temp_db = tmp_path / "finaira_generalization.db"
    shutil.copy2(DB, temp_db)
    first = import_gcc_audit(temp_db, SOURCE, tmp_path / "report", backup=False)
    second = import_gcc_audit(temp_db, SOURCE, tmp_path / "report", backup=False)
    assert first["new_records_created"] == 0
    assert first["new_aliases_imported"] == 0
    assert second["new_records_created"] == 0
    assert second["new_aliases_imported"] == 0
    assert second["aliases_preserved_before"] == second["aliases_preserved_after"] == 1569
    engine = make_engine(temp_db)
    with engine.connect() as connection:
        assert connection.execute(text("select count(*) from banks")).scalar() == 302
        assert connection.execute(text("select count(*) from bank_audit_classifications")).scalar() == 266
        assert connection.execute(text("select count(*) from bank_relationships")).scalar() == 5


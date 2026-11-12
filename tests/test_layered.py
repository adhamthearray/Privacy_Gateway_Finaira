from pathlib import Path
from finaira_generalization import GeneralizationDB
from finaira_generalization.layers import generate_levels
from finaira_generalization.db import make_engine
from sqlalchemy import text

DB=Path("data/processed/finaira_generalization.db")

def test_occupation_returns_ordered_verified_chain():
    r=GeneralizationDB(DB).get_candidates("OCCUPATION","technical director","en")
    assert r["resolution_status"]=="VERIFIED"
    assert [x["level_code"] for x in r["candidates"]]==["EXACT","ISCO_UNIT","ISCO_MINOR","ISCO_SUB_MAJOR","ISCO_MAJOR","SUPPRESSED"]
    assert all(x["verification_status"]=="OFFICIAL" for x in r["candidates"])

def test_nationality_arabic_chain_and_natural_earth_english_labels():
    ar=GeneralizationDB(DB).get_candidates("NATIONALITY","مصرية","ar")
    assert [x["level_code"] for x in ar["candidates"]]==["EXACT","SUBREGION","CONTINENT","SUPPRESSED"]
    assert ar["candidates"][0]["taxonomy"]=="NATURAL_EARTH"
    assert ar["candidates"][1]["available"] is False
    en=GeneralizationDB(DB).get_candidates("NATIONALITY","Egyptian","en")
    assert en["resolution_status"]=="MATCHED"
    assert en["candidates"][1]["available"] is True
    assert en["candidates"][1]["taxonomy"]=="NATURAL_EARTH"

def test_dynamic_age_and_date_layers_have_nested_intervals():
    age=GeneralizationDB(DB).get_candidates("AGE","27","en")["candidates"]
    assert [x["level_code"] for x in age]==["EXACT","NARROW_BAND","WIDE_BAND","BROAD_CATEGORY","SUPPRESSED"]
    assert age[1]["metadata"]["interval_start"]<=age[0]["metadata"]["interval_start"]
    assert age[1]["metadata"]["interval_end"]>=age[0]["metadata"]["interval_end"]
    date=GeneralizationDB(DB).get_candidates("DATE","2026-03-14","en")["candidates"]
    assert date[2]["representation"]=="Q1 2026"
    assert date[2]["metadata"]["interval_start"]=="2026-01-01"

def test_ids_stable_and_base_tables_preserved():
    e=make_engine(DB)
    with e.connect() as c:
        before=c.execute(text("select count(*) from occupations")).scalar()
    first=GeneralizationDB(DB).get_candidates("OCCUPATION","technical director","en")["candidates"]
    generate_levels(DB)
    second=GeneralizationDB(DB).get_candidates("OCCUPATION","technical director","en")["candidates"]
    assert [x["candidate_id"] for x in first]==[x["candidate_id"] for x in second]
    with e.connect() as c:
        assert c.execute(text("select count(*) from occupations")).scalar()==before

def test_unknown_returns_safe_suppression_only():
    r=GeneralizationDB(DB).get_candidates("OCCUPATION","not a real occupation","en")
    assert r["resolution_status"]=="NOT_FOUND"
    assert [x["level_code"] for x in r["candidates"]]==["SUPPRESSED"]

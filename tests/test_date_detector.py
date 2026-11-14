from datetime import date

import pytest

from finaira_generalization import GeneralizationDB
from finaira_generalization.age_date import date_generalize, parse_date
from finaira_generalization.date_detector import detect_date, date_levels


def test_iso_numeric_and_named_gregorian_formats():
    cases = {
        "2026-11-14": "2026-11-14",
        "2026/11/14": "2026-11-14",
        "14/11/2026": "2026-11-14",
        "14 11 2026": "2026-11-14",
        "14 November 2026": "2026-11-14",
        "November 14, 2026": "2026-11-14",
        "١٤/١١/٢٠٢٦": "2026-11-14",
        "۱۴/۱۱/۲۰۲۶": "2026-11-14",
        "14 نوفمبر 2026": "2026-11-14",
    }
    for raw, expected in cases.items():
        detected = detect_date(raw)
        assert detected.status == "VERIFIED", raw
        assert detected.date_iso == expected, raw
        assert detected.calendar == "GREGORIAN", raw


def test_ambiguous_and_explicit_numeric_orders():
    ambiguous = detect_date("03/04/2026")
    assert ambiguous.status == "AMBIGUOUS"
    assert ambiguous.reason_code == "AMBIGUOUS_DATE"
    assert parse_date("03/04/2026", "%d/%m/%Y") == date(2026, 4, 3)
    assert detect_date("03/04/2026", {"date_order": "MDY"}).date_iso == "2026-03-04"
    with pytest.raises(ValueError, match="AMBIGUOUS_DATE"):
        parse_date("03/04/2026")


def test_iso_week_ordinal_timestamp_and_compact_formats():
    assert detect_date("2026-W46-6").date_iso == "2026-11-14"
    assert detect_date("2026318").date_iso == "2026-11-14"
    timestamp = detect_date("2026-11-14T21:00:00+02:00")
    assert timestamp.format_family == "ISO_8601_TIMESTAMP"
    assert timestamp.time_text == "21:00:00"
    assert timestamp.timezone_text == "+02:00"
    assert detect_date("20261114").date_iso == "2026-11-14"


def test_partial_dates_and_generalization_levels():
    month = detect_date("2026-11")
    assert month.precision == "month"
    assert [row["code"] for row in date_levels(month)] == ["MONTH", "QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]
    day_month = detect_date("14 Nov")
    assert day_month.precision == "day_month"
    assert date_generalize("2026-11-14", "quarter") == "Q4 2026"
    assert date_generalize("2026-11-14", "year", language="ar") == "2026"


def test_non_gregorian_values_are_preserved_without_conversion():
    hijri = detect_date("١٤ رمضان ١٤٤٨ هـ")
    assert hijri.status == "VERIFIED"
    assert hijri.calendar == "HIJRI"
    assert hijri.date_iso is None
    assert hijri.metadata["conversion"] == "not_performed"
    assert date_generalize("١٤ رمضان ١٤٤٨ هـ", "YEAR") == "Hijri 1448"

    solar = detect_date("1405/08/23", {"calendar": "SOLAR_HIJRI"})
    assert solar.status == "VERIFIED"
    assert solar.calendar == "SOLAR_HIJRI"
    assert solar.date_iso is None
    assert detect_date("1448 AH").calendar == "HIJRI"


def test_relative_invalid_and_ambiguous_inputs_are_explicit():
    assert detect_date("tomorrow").status == "NEEDS_CONTEXT"
    relative = detect_date("tomorrow", {"anchor_date": "2026-11-14"})
    assert relative.date_iso == "2026-11-15"
    assert relative.is_relative is True
    assert detect_date("31/02/2026").status == "INVALID_INPUT"
    assert detect_date("2026").reason_code == "AMBIGUOUS_YEAR_OR_IDENTIFIER"
    assert detect_date("2026", {"date_hint": "year"}).precision == "year"


def test_date_candidates_expose_detector_provenance_and_intervals():
    result = GeneralizationDB("data/processed/finaira_generalization.db").get_candidates("DATE", "2026-03-14", "en")
    assert result["resolution_status"] == "VERIFIED"
    assert [row["level_code"] for row in result["candidates"]] == ["EXACT", "MONTH", "QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]
    quarter = result["candidates"][2]
    assert quarter["source"] == "Finaira rule-based date detector"
    assert quarter["provenance"]["calendar"] == "GREGORIAN"
    assert quarter["metadata"]["interval_start"] == "2026-01-01"
    assert quarter["metadata"]["interval_end"] == "2026-03-31"


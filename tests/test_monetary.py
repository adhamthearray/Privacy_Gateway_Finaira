from decimal import Decimal

from finaira_generalization.monetary import generalize_threshold, interpret_and_generalize_money


def interpretation(value, **kwargs):
    return interpret_and_generalize_money(value, kwargs or None)["interpretation"]


def test_number_only_formats_normalize_without_currency():
    values = (
        "12500",
        "12,500",
        "١٢٬٥٠٠",
        "۱۲٬۵۰۰",
        "12.5k",
        "١٢٫٥ ألف",
        "twelve thousand five hundred",
        "اثنا عشر ألفًا وخمسمائة",
    )
    for value in values:
        result = interpret_and_generalize_money(value)
        assert result["interpretation"]["status"] == "SUCCESS", value
        assert result["interpretation"]["normalized_amount"] == "12500", value
        assert result["interpretation"]["currency"] is None
        assert result["representations"]["range_based"]["status"] == "AVAILABLE"
        assert result["representations"]["order_of_magnitude"]["status"] == "AVAILABLE"
        if value == "12500":
            assert result["representations"]["order_of_magnitude"]["en"] == "Tens of thousands"
        assert result["representations"]["task_aware_threshold"]["status"] == "REQUIRES_THRESHOLD"


def test_currency_is_optional_but_preserved_when_present():
    for value in ("12500 SAR", "SAR 12500", "12.5k SAR", "١٢٫٥ ألف ريال سعودي"):
        result = interpret_and_generalize_money(value)
        assert result["interpretation"]["status"] == "SUCCESS", value
        assert result["interpretation"]["normalized_amount"] == "12500", value
        assert result["interpretation"]["currency"] == "SAR", value
        assert result["representations"]["range_based"]["en"] == "10,000–25,000 SAR"
        assert "ريال سعودي" in result["representations"]["range_based"]["ar"]
        assert "ريال سعودي" in result["representations"]["order_of_magnitude"]["ar"]


def test_plain_locale_decimal_and_grouping_forms():
    assert interpretation("12,500.75")["normalized_amount"] == "12500.75"
    assert interpretation("12.500,75", locale="de-DE")["normalized_amount"] == "12500.75"
    assert interpretation("12 500,75", locale="fr-FR")["normalized_amount"] == "12500.75"
    assert interpretation("12'500.75")["normalized_amount"] == "12500.75"
    assert interpretation(".75")["normalized_amount"] == "0.75"
    assert interpretation("0.5")["normalized_amount"] == "0.5"
    assert interpretation("1,234")["status"] == "AMBIGUOUS_NUMBER"
    assert interpretation("1,234", locale="en-US")["normalized_amount"] == "1234"


def test_written_scales_fractions_and_scientific_values():
    cases = {
        "five hundred": "500",
        "one thousand": "1000",
        "one and a half million": "1500000",
        "مليون ونصف": "1500000",
        "ثلاثة ملايين": "3000000",
        "مليار ومئتا مليون": "1200000000",
        "½": "0.5",
        "2½": "2.5",
        "half a million": "500000",
        "1.2e6": "1200000",
        "3 × 10^6": "3000000",
        "10^9": "1000000000",
    }
    for value, expected in cases.items():
        assert interpretation(value)["normalized_amount"] == expected, value


def test_signed_approximate_range_and_constraint_inputs_are_not_exact():
    assert interpretation("-500")["normalized_amount"] == "-500"
    assert interpretation("500-")["normalized_amount"] == "-500"
    assert interpretation("(500)")["normalized_amount"] == "-500"
    assert interpretation("about 5000")["qualifier"] == "APPROXIMATE"
    ranged = interpret_and_generalize_money("1000-5000")
    assert ranged["interpretation"]["normalized_lower"] == "1000"
    assert ranged["interpretation"]["normalized_upper"] == "5000"
    assert ranged["interpretation"]["is_exact"] is False
    assert ranged["representations"]["range_based"]["status"] == "INDETERMINATE"
    constrained = interpret_and_generalize_money("at least 10000")
    assert constrained["interpretation"]["qualifier"] == "CONSTRAINT"
    assert constrained["representations"]["order_of_magnitude"]["status"] == "INDETERMINATE"


def test_threshold_representation_is_conditional_and_exact():
    no_threshold = interpret_and_generalize_money("12500")
    assert no_threshold["representations"]["task_aware_threshold"] == {"status": "REQUIRES_THRESHOLD", "en": None, "ar": None}
    result = interpret_and_generalize_money("12500", threshold_spec={"operator": ">", "threshold": "10000"})
    threshold = result["representations"]["task_aware_threshold"]
    assert threshold["status"] == "TRUE"
    assert threshold["value"] is True
    assert threshold["en"] == "Amount exceeds 10,000"
    assert threshold["ar"] == "المبلغ يتجاوز ١٠٬٠٠٠"
    assert interpret_and_generalize_money("1000-5000", threshold_spec={"operator": ">", "threshold": "10000"})["representations"]["task_aware_threshold"]["status"] == "FALSE"
    assert interpret_and_generalize_money("about 5000", threshold_spec={"operator": ">", "threshold": "1000"})["representations"]["task_aware_threshold"]["status"] == "INDETERMINATE"


def test_threshold_operators_units_and_boundaries():
    assert generalize_threshold(Decimal("100"), ">", Decimal("100"))["status"] == "FALSE"
    assert generalize_threshold(Decimal("100"), ">=", Decimal("100"))["status"] == "TRUE"
    assert generalize_threshold(Decimal("100"), "BETWEEN", ["100", "200"])["value"] is True
    assert generalize_threshold(Decimal("300"), "OUTSIDE_RANGE", ["100", "200"])["value"] is True
    assert generalize_threshold(Decimal("100"), ">", Decimal("50"), currency="SAR", threshold_currency="EGP")["status"] == "CURRENCY_MISMATCH"
    assert generalize_threshold(Decimal("100"), ">", Decimal("50"), currency="SAR")["status"] == "CURRENCY_CONTEXT_REQUIRED"
    assert generalize_threshold(Decimal("100"), ">", Decimal("50"), currency="SAR", same_unit_context=True)["status"] == "TRUE"


def test_currency_conflicts_unknown_currency_offsets_and_metadata():
    assert interpretation("12500 XYZ")["status"] == "UNKNOWN_CURRENCY"
    assert interpret_and_generalize_money("12500 SAR", {"currency": "EGP"})["interpretation"]["status"] == "CURRENCY_CONFLICT"
    result = interpret_and_generalize_money("١٢٥٠٠", {"start": 4, "end": 9, "metadata": {"source": "ner"}})
    assert result["offsets"] == {"start": 4, "end": 9}
    assert result["metadata"] == {"source": "ner"}
    assert interpret_and_generalize_money("12500", {"entity_type": "PERSON_NAME"})["interpretation"]["status"] == "INVALID_ENTITY_TYPE"


def test_currency_specific_minor_units_are_exact_only_when_currency_is_known():
    cases = {
        "12 riyals and 50 halalas": ("12.5", "SAR"),
        "3 dinars and 125 fils": ("3.125", "KWD"),
        "٥ جنيهات و٢٥ قرشًا": ("5.25", "EGP"),
    }
    for value, (amount, currency) in cases.items():
        result = interpret_and_generalize_money(value)
        assert result["interpretation"]["normalized_amount"] == amount, value
        assert result["interpretation"]["currency"] == currency, value
        assert result["interpretation"]["pattern"] == "MINOR_UNITS", value


def test_trusted_external_scale_is_optional_and_deterministic():
    result = interpret_and_generalize_money("12.5", {"scale": "thousand"})
    assert result["interpretation"]["normalized_amount"] == "12500"
    assert result["interpretation"]["pattern"] == "SCALED_NUMBER"

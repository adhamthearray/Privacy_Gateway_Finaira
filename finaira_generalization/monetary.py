"""Deterministic interpretation and generalization of known monetary entities.

This module deliberately does not detect entities in documents and does not
choose a representation.  It accepts one already-classified monetary value,
normalizes it with :class:`~decimal.Decimal`, and returns all three candidate
representations for a later policy/JEV layer.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


DEFAULT_BUCKETS = (
    (Decimal("0"), Decimal("1000")),
    (Decimal("1000"), Decimal("5000")),
    (Decimal("5000"), Decimal("10000")),
    (Decimal("10000"), Decimal("25000")),
    (Decimal("25000"), Decimal("50000")),
    (Decimal("50000"), Decimal("100000")),
    (Decimal("100000"), Decimal("500000")),
    (Decimal("500000"), Decimal("1000000")),
)

_DIGIT_MAP = {
    **{chr(0x660 + i): str(i) for i in range(10)},
    **{chr(0x6F0 + i): str(i) for i in range(10)},
    **{chr(0x966 + i): str(i) for i in range(10)},
    **{chr(0xBE6 + i): str(i) for i in range(10)},
    **{chr(0xE50 + i): str(i) for i in range(10)},
    **{chr(0x17E0 + i): str(i) for i in range(10)},
    **{chr(0x1040 + i): str(i) for i in range(10)},
}
_DIGITS = str.maketrans(_DIGIT_MAP)
_MINUS = str.maketrans({"−": "-", "﹣": "-", "－": "-"})
_AR_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_SPACE = re.compile(r"\s+")

_CURRENCY_ALIASES = {
    "SAR": ("sar", "riyal", "riyals", "ريال سعودي", "ريال", "ر.س", "ر س", "sr"),
    "AED": ("aed", "درهم إماراتي", "درهم اماراتي", "درهم", "د.إ", "دإ"),
    "KWD": ("kwd", "dinar", "dinars", "دينار كويتي", "دينار كويت", "د.ك", "دك"),
    "BHD": ("bhd", "دينار بحريني", "د.ب", "دب"),
    "QAR": ("qar", "ريال قطري", "ر.ق", "رق"),
    "OMR": ("omr", "ريال عماني", "ريال عُماني", "ر.ع", "رع", "baisa", "بيسة"),
    "EGP": ("egp", "جنيه مصري", "جنيه", "جنيهات", "ج.م", "ج م", "le", "l.e."),
    "USD": ("usd", "us dollar", "us dollars", "dollar", "dollars", "دولار", "دولار أمريكي", "دولار امريكي", "$"),
    "EUR": ("eur", "euro", "euros", "يورو", "€"),
    "GBP": ("gbp", "pound", "pounds", "sterling", "جنيه إسترليني", "جنيه استرليني", "£"),
    "JPY": ("jpy", "yen", "ين", "¥"),
    "CHF": ("chf", "swiss franc", "فرنك سويسري"),
    "CAD": ("cad", "canadian dollar", "دولار كندي"),
    "AUD": ("aud", "australian dollar", "دولار أسترالي", "دولار استرالي"),
    "INR": ("inr", "rupee", "rupees", "روبية", "روبيه", "₹"),
    "TRY": ("try", "lira", "ليرة", "₺"),
    "CNY": ("cny", "yuan", "renminbi", "يوان", "¥"),
}
_CURRENCY_LABEL_AR = {
    "EGP": "جنيه مصري", "SAR": "ريال سعودي", "AED": "درهم إماراتي",
    "KWD": "دينار كويتي", "BHD": "دينار بحريني", "QAR": "ريال قطري",
    "OMR": "ريال عماني", "USD": "دولار أمريكي", "EUR": "يورو",
    "GBP": "جنيه إسترليني", "JPY": "ين ياباني", "CHF": "فرنك سويسري",
    "CAD": "دولار كندي", "AUD": "دولار أسترالي", "INR": "روبية هندية",
    "TRY": "ليرة تركية", "CNY": "يوان صيني",
}
_CURRENCY_LOOKUP: dict[str, str] = {}
for _code, _aliases in _CURRENCY_ALIASES.items():
    for _alias in _aliases:
        _CURRENCY_LOOKUP[_alias.casefold()] = _code

_EN_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
_EN_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_EN_SCALES = {"thousand": Decimal("1000"), "million": Decimal("1000000"), "billion": Decimal("1000000000"), "trillion": Decimal("1000000000000"), "lakh": Decimal("100000"), "lakhs": Decimal("100000"), "crore": Decimal("10000000"), "crores": Decimal("10000000")}
_AR_ONES = {
    "صفر": 0, "واحد": 1, "واحدة": 1, "اثنان": 2, "اثنين": 2, "اثنا": 2, "اثني": 2,
    "اثنتان": 2, "اثنتين": 2, "اثنتا": 2, "اثنتي": 2, "ثلاث": 3, "ثلاثة": 3,
    "أربع": 4, "اربعة": 4, "أربعة": 4, "خمس": 5, "خمسة": 5, "ست": 6, "ستة": 6,
    "سبع": 7, "سبعة": 7, "ثمان": 8, "ثمانية": 8, "تسع": 9, "تسعة": 9,
    "عشر": 10, "عشرة": 10,
}
_AR_TENS = {"عشرون": 20, "عشرين": 20, "ثلاثون": 30, "ثلاثين": 30, "أربعون": 40, "أربعين": 40, "خمسون": 50, "خمسين": 50, "ستون": 60, "ستين": 60, "سبعون": 70, "سبعين": 70, "ثمانون": 80, "ثمانين": 80, "تسعون": 90, "تسعين": 90}
_AR_HUNDREDS = {
    "مائة": 100, "مئة": 100, "مائه": 100, "مئتان": 200, "مئتا": 200, "مائتان": 200,
    "ثلاثمائة": 300, "ثلاثمئة": 300, "أربعمائة": 400, "أربعمئة": 400,
    "خمسمائة": 500, "خمسمئة": 500, "ستمائة": 600, "ستمئة": 600,
    "سبعمائة": 700, "سبعمئة": 700, "ثمانمائة": 800, "ثمانمئة": 800,
    "تسعمائة": 900, "تسعمئة": 900,
}
_AR_SCALES = {
    "ألف": Decimal("1000"), "الف": Decimal("1000"), "آلاف": Decimal("1000"), "ألفًا": Decimal("1000"), "ألفا": Decimal("1000"), "الفًا": Decimal("1000"), "الفا": Decimal("1000"),
    "مليون": Decimal("1000000"), "ملايين": Decimal("1000000"),
    "مليار": Decimal("1000000000"), "مليارات": Decimal("1000000000"),
    "تريليون": Decimal("1000000000000"), "تريليونات": Decimal("1000000000000"),
}
_EXTERNAL_SCALES = {
    "thousand": Decimal("1000"), "k": Decimal("1000"), "ألف": Decimal("1000"), "الف": Decimal("1000"),
    "million": Decimal("1000000"), "m": Decimal("1000000"), "مليون": Decimal("1000000"),
    "billion": Decimal("1000000000"), "bn": Decimal("1000000000"), "مليار": Decimal("1000000000"),
    "trillion": Decimal("1000000000000"), "t": Decimal("1000000000000"), "تريليون": Decimal("1000000000000"),
}

_APPROXIMATE_RE = re.compile(r"(?i)^(?:~|≈|about\b|approximately\b|roughly\b|around\b|حوالي\b|تقريبًا\b|تقريبا\b|قرابة\b|نحو\b)\s*")
_CONSTRAINT_RE = re.compile(r"(?i)^(>=|<=|≥|≤|>|<|=|!=|≠)\s*(.+)$")
_WRITTEN_CONSTRAINTS = (
    (re.compile(r"(?i)^at\s+least\s+(.+)$"), ">="),
    (re.compile(r"(?i)^at\s+most\s+(.+)$"), "<="),
    (re.compile(r"(?i)^no\s+more\s+than\s+(.+)$"), "<="),
    (re.compile(r"(?i)^more\s+than\s+(.+)$"), ">"),
    (re.compile(r"(?i)^less\s+than\s+(.+)$"), "<"),
    (re.compile(r"^أكثر\s+من\s+(.+)$"), ">"),
    (re.compile(r"^أقل\s+من\s+(.+)$"), "<"),
    (re.compile(r"^على\s+الأقل\s+(.+)$"), ">="),
    (re.compile(r"^لا\s+يتجاوز\s+(.+)$"), "<="),
)


def _clean(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text)).translate(_DIGITS).translate(_MINUS)
    value = _AR_DIACRITICS.sub("", value).replace("ـ", "").replace("٫", ".").replace("٬", ",")
    return _SPACE.sub(" ", value).strip()


def _arabic_clean(text: str) -> str:
    value = _clean(text).casefold().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    value = re.sub(r"[ًٌٍَُِّْـ]", "", value)
    return _SPACE.sub(" ", value).strip()


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("INVALID_NUMBER") from exc
    if not result.is_finite():
        raise ValueError("INVALID_NUMBER")
    return result


def _external_scale(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal(1)
    if isinstance(value, (int, float, Decimal)):
        return _decimal(value)
    key = _clean(str(value)).casefold()
    if key in _EXTERNAL_SCALES:
        return _EXTERNAL_SCALES[key]
    if key in _AR_SCALES:
        return _AR_SCALES[key]
    return _decimal(value)


def _currency(value: Any) -> str | None:
    if value is None or value == "":
        return None
    key = _clean(str(value)).casefold().strip(" .")
    if key in _CURRENCY_LOOKUP:
        return _CURRENCY_LOOKUP[key]
    upper = key.upper()
    if upper in _CURRENCY_ALIASES:
        return upper
    raise ValueError("UNKNOWN_CURRENCY")


def _currency_tokens(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    lowered = _clean(text).casefold()
    for alias, code in sorted(_CURRENCY_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in {"$", "€", "£", "¥", "₹", "₺"}:
            present = alias in lowered
        elif re.search(r"[a-z]", alias):
            present = bool(re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", lowered))
        else:
            present = bool(re.search(rf"(?<![\u0600-\u06ff]){re.escape(alias)}(?![\u0600-\u06ff])", lowered))
        if present:
            found.append((alias, code))
    return found


def _extract_currency(text: str, context: dict) -> tuple[str | None, str, str | None]:
    explicit = _currency_tokens(text)
    codes = {code for _, code in explicit}
    if len(codes) > 1:
        raise ValueError("CURRENCY_CONFLICT")
    text_currency = next(iter(codes), None)
    context_currency = _currency(context.get("currency")) if context.get("currency") is not None else None
    if text_currency and context_currency and text_currency != context_currency:
        raise ValueError("CURRENCY_CONFLICT")
    currency = text_currency or context_currency
    cleaned = text
    for alias, _code in explicit:
        if alias in {"$", "€", "£", "¥", "₹", "₺"}:
            cleaned = cleaned.replace(alias, " ")
        elif re.search(r"[a-z]", alias):
            cleaned = re.sub(rf"(?i)(?<![a-z]){re.escape(alias)}(?![a-z])", " ", cleaned)
        else:
            cleaned = re.sub(rf"(?<![\u0600-\u06ff]){re.escape(alias)}(?![\u0600-\u06ff])", " ", cleaned)
    # Preserve unknown ISO-like currency tokens as unresolved rather than
    # guessing a currency from the number.
    unknown = None
    for token in re.findall(r"(?<![A-Za-z])[A-Za-z]{3}(?![A-Za-z])", cleaned):
        # Lower-case three-letter words can be part of written numbers
        # (``one and a half million``). An uppercase token such as XYZ is a
        # useful explicit signal that an unknown currency was supplied.
        if token.isupper() and token.upper() not in _CURRENCY_ALIASES:
            unknown = token.upper()
            cleaned = re.sub(rf"(?i)(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", " ", cleaned)
            break
    return currency, _SPACE.sub(" ", cleaned).strip(), unknown


def _parse_numeric(text: str, locale: str | None) -> Decimal:
    value = _clean(text).replace("'", "").replace("’", "")
    if not value:
        raise ValueError("INVALID_NUMBER")
    value = value.replace(" ", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:[.,]\d+)*|[.,]\d+)", value):
        raise ValueError("UNSUPPORTED_PATTERN")
    sign = ""
    if value[:1] in "+-":
        sign, value = value[0], value[1:]
    locale_key = (locale or "").casefold()
    comma_decimal = bool(re.search(r"(?:^|[-_])(?:de|fr|es|it|pt|tr)(?:[-_]|$)", locale_key))
    comma_decimal = comma_decimal or locale_key.startswith(("de", "fr", "es", "it", "pt", "tr"))
    locale_known = bool(locale_key)
    dot_decimal = locale_key.startswith(("en", "ar", "hi", "bn", "th", "km", "my"))
    if "," in value and "." in value:
        decimal_sep = "," if value.rfind(",") > value.rfind(".") else "."
        grouping_sep = "." if decimal_sep == "," else ","
        integer, fraction = value.rsplit(decimal_sep, 1)
        integer = integer.replace(grouping_sep, "")
        normalized = f"{integer}.{fraction}"
    elif "," in value or "." in value:
        sep = "," if "," in value else "."
        chunks = value.split(sep)
        if len(chunks) > 2:
            if not all(len(chunk) == 3 for chunk in chunks[1:]):
                raise ValueError("AMBIGUOUS_NUMBER")
            normalized = "".join(chunks)
        else:
            left, right = chunks
            if len(right) == 3:
                if comma_decimal and sep == ",":
                    normalized = f"{left}.{right}"
                elif dot_decimal and sep == ".":
                    normalized = f"{left}.{right}"
                elif locale_known:
                    normalized = f"{left}{right}"
                elif len(left) == 1:
                    raise ValueError("AMBIGUOUS_NUMBER")
                else:
                    normalized = f"{left}{right}"
            else:
                normalized = f"{left}.{right}" if sep == "," or sep == "." else value
    else:
        normalized = value
    try:
        return _decimal(f"{sign}{normalized}")
    except ValueError as exc:
        raise ValueError("INVALID_NUMBER") from exc


def _parse_under_1000(tokens: list[str], language: str) -> Decimal:
    if language == "en":
        total = 0
        current = 0
        for token in tokens:
            if token in {"and", "of", "the"}:
                continue
            if token in _EN_ONES:
                current += _EN_ONES[token]
            elif token in _EN_TENS:
                current += _EN_TENS[token]
            elif token == "hundred":
                current = (current or 1) * 100
            else:
                raise ValueError("UNSUPPORTED_WRITTEN_NUMBER")
        return Decimal(total + current)
    total = 0
    for token in tokens:
        token = token.lstrip("و") if token.startswith("و") and len(token) > 1 else token
        if token in {"و", "من", "عام", "سنه", "سنة", "مبلغ"}:
            continue
        if token in _AR_ONES:
            total += _AR_ONES[token]
        elif token in _AR_TENS:
            total += _AR_TENS[token]
        elif token in _AR_HUNDREDS:
            total += _AR_HUNDREDS[token]
        else:
            raise ValueError("UNSUPPORTED_WRITTEN_NUMBER")
    return Decimal(total)


def _parse_words(text: str) -> Decimal:
    arabic = any("\u0600" <= char <= "\u06ff" for char in text)
    language = "ar" if arabic else "en"
    if language == "en":
        normalized = re.sub(r"[-,]", " ", text.casefold())
        if re.fullmatch(r"one\s+and\s+a\s+half\s+(?:million|billion|trillion|thousand|lakh|crore)", normalized):
            scale = normalized.split()[-1]
            return _EN_SCALES[scale] * Decimal("1.5")
        tokens = normalized.split()
        if not any(token in _EN_ONES or token in _EN_TENS or token in _EN_SCALES or token == "hundred" for token in tokens):
            raise ValueError("UNSUPPORTED_WRITTEN_NUMBER")
        total = Decimal(0)
        current: list[str] = []
        for token in tokens:
            if token in _EN_SCALES:
                base = _parse_under_1000(current, "en") if current else Decimal(1)
                total += base * _EN_SCALES[token]
                current = []
            else:
                current.append(token)
        return total + (_parse_under_1000(current, "en") if current else Decimal(0))
    normalized = _arabic_clean(text)
    if normalized.endswith(" ونصف") or normalized.endswith(" ونصفا"):
        base_text = normalized.rsplit(" ونصف", 1)[0]
        tokens = base_text.split()
        scale = next((token for token in reversed(tokens) if token in _AR_SCALES), None)
        if scale:
            return _parse_words(base_text) + _AR_SCALES[scale] / 2
    tokens = normalized.replace("،", " ").replace("-", " ").split()
    if not any(token.lstrip("و") in _AR_ONES or token.lstrip("و") in _AR_TENS or token.lstrip("و") in _AR_HUNDREDS or token.lstrip("و") in _AR_SCALES for token in tokens):
        raise ValueError("UNSUPPORTED_WRITTEN_NUMBER")
    total = Decimal(0)
    current: list[str] = []
    for token in tokens:
        key = token.lstrip("و") if token.startswith("و") and len(token) > 1 else token
        if key in _AR_SCALES:
            base = _parse_under_1000(current, "ar") if current else Decimal(1)
            total += base * _AR_SCALES[key]
            current = []
        else:
            current.append(key)
    return total + (_parse_under_1000(current, "ar") if current else Decimal(0))


def _parse_fraction(text: str) -> Decimal | None:
    glyphs = {"½": Decimal("0.5"), "¼": Decimal("0.25"), "¾": Decimal("0.75"), "⅓": Decimal(1) / 3, "⅔": Decimal(2) / 3}
    if text in glyphs:
        return glyphs[text]
    # NFKC turns ``2½`` into ``21⁄2``. Recover that mixed-number form after
    # normalization while keeping ordinary slash fractions exact.
    normalized_mixed = re.fullmatch(r"(\d+)(\d)⁄(\d)", text)
    if normalized_mixed:
        denominator = int(normalized_mixed.group(3))
        return Decimal(normalized_mixed.group(1)) + Decimal(normalized_mixed.group(2)) / Decimal(denominator)
    slash_fraction = re.fullmatch(r"(\d+)\s*[⁄/]\s*(\d+)", text)
    if slash_fraction:
        denominator = int(slash_fraction.group(2))
        if denominator == 0:
            return None
        return Decimal(slash_fraction.group(1)) / Decimal(denominator)
    match = re.fullmatch(r"(\d+)\s*([½¼¾])", text)
    if match:
        return Decimal(match.group(1)) + glyphs[match.group(2)]
    if re.fullmatch(r"(?i)half\s+a\s+million", text):
        return Decimal("500000")
    if re.fullmatch(r"(?i)quarter\s+of\s+a\s+million", text):
        return Decimal("250000")
    if text in {"نصف مليون", "نصف مليون"}:
        return Decimal("500000")
    if text in {"ربع مليون"}:
        return Decimal("250000")
    return None


def _parse_core(text: str, locale: str | None) -> tuple[Decimal, str]:
    value = _clean(text).strip()
    if not value:
        raise ValueError("INVALID_NUMBER")
    sign = Decimal(1)
    if value.startswith("(") and value.endswith(")"):
        value = value[1:-1].strip()
        sign = Decimal(-1)
    elif value.endswith("-") and not value.startswith("-"):
        value = value[:-1].strip()
        sign = Decimal(-1)
    if value[:1] in "+-":
        if value[0] == "-": sign *= -1
        value = value[1:].strip()
    fraction = _parse_fraction(value)
    if fraction is not None:
        return sign * fraction, "FRACTION"
    power_of_ten = re.fullmatch(r"10\s*\^\s*(\d+)", value)
    if power_of_ten:
        exponent = int(power_of_ten.group(1))
        if exponent > 1000:
            raise ValueError("EXPONENT_TOO_LARGE")
        return sign * (Decimal(10) ** exponent), "SCIENTIFIC"
    scientific = re.fullmatch(r"(?i)(\d+(?:\.\d+)?)\s*[×x*]\s*10\s*\^\s*(\d+)|([+-]?\d+(?:\.\d+)?)[eE]([+-]?\d+)", value)
    if scientific:
        if scientific.group(1):
            base, exponent = Decimal(scientific.group(1)), int(scientific.group(2))
        else:
            base, exponent = Decimal(scientific.group(3)), int(scientific.group(4))
        if abs(exponent) > 1000:
            raise ValueError("EXPONENT_TOO_LARGE")
        with localcontext() as context:
            context.prec = 80
            return sign * base * (Decimal(10) ** exponent), "SCIENTIFIC"
    abbreviated = re.fullmatch(r"(.+?)\s*(k|K|m|M|mn|bn|b|t|million|billion|trillion|lakh|crore|ألف|الف|آلاف|ألفا|الفا|مليون|ملايين|مليار|مليارات|تريليون|تريليونات)$", value, re.I)
    if abbreviated:
        number, suffix = abbreviated.groups()
        suffix_key = suffix.casefold()
        scale = {"k": Decimal("1000"), "m": Decimal("1000000"), "mn": Decimal("1000000"), "b": Decimal("1000000000"), "bn": Decimal("1000000000"), "t": Decimal("1000000000000")}.get(suffix_key, _EN_SCALES.get(suffix_key) or _AR_SCALES.get(suffix))
        if scale is None:
            raise ValueError("UNSUPPORTED_SCALE")
        try:
            base = _parse_numeric(number, locale)
        except ValueError:
            # Phrases such as ``مليار ومئتا مليون`` and ``one million``
            # contain a scale word but are written numbers, not numeric
            # abbreviations.
            return sign * _parse_words(value), "WRITTEN_NUMBER"
        return sign * base * scale, "ABBREVIATED_NUMBER"
    try:
        return sign * _parse_numeric(value, locale), "PLAIN_NUMERIC"
    except ValueError as numeric_error:
        if str(numeric_error) == "AMBIGUOUS_NUMBER":
            raise
        return sign * _parse_words(value), "WRITTEN_NUMBER"


def _parse_piece(text: str, locale: str | None) -> tuple[Decimal, str]:
    return _parse_core(text.strip(), locale)


def _parse_minor_units(text: str, currency: str | None, locale: str | None) -> tuple[Decimal, str] | None:
    """Parse explicit major/minor-unit wording when the currency is known."""
    cleaned = _clean(text)
    patterns = {
        "SAR": r"^(.+?)\s*(?:riyal|riyals|ريال(?:\s+سعودي)?|ر\.س|ر س)\s+(?:and|و)\s*(\d+)\s*(?:halala|halalas|هللة|هللات)$",
        "AED": r"^(.+?)\s*(?:dirham|dirhams|درهم(?:\s+إماراتي)?|د\.إ|دإ)\s+(?:and|و)\s*(\d+)\s*(?:fils|فلس)$",
        "KWD": r"^(.+?)\s*(?:dinar|dinars|دينار(?:\s+كويتي)?|د\.ك|دك)\s+(?:and|و)\s*(\d+)\s*(?:fils|فلس)$",
        "BHD": r"^(.+?)\s*(?:dinar|dinars|دينار(?:\s+بحريني)?|د\.ب|دب)\s+(?:and|و)\s*(\d+)\s*(?:fils|فلس)$",
        "EGP": r"^(.+?)\s*(?:pound|pounds|جنيه(?:ات)?|ج\.م|ج م)\s+(?:and|و)\s*(\d+)\s*(?:piastre|piaster|قرش|قروش|قرشا)$",
    }
    if currency not in patterns:
        return None
    match = re.fullmatch(patterns[currency], cleaned, re.I)
    if not match:
        return None
    major, minor = _parse_numeric(match.group(1), locale), int(match.group(2))
    scale = Decimal("1000") if currency in {"KWD", "BHD"} else Decimal("100")
    return major + Decimal(minor) / scale, "MINOR_UNITS"


def _parse_structured(text: str, locale: str | None) -> dict:
    value = _clean(text)
    approximate = bool(_APPROXIMATE_RE.match(value))
    if approximate:
        value = _APPROXIMATE_RE.sub("", value, count=1).strip()
    for pattern, operator in _WRITTEN_CONSTRAINTS:
        match = pattern.match(value)
        if match:
            amount, kind = _parse_piece(match.group(1), locale)
            return {"kind": "CONSTRAINT", "operator": operator, "amount": amount, "pattern": "CONSTRAINED_AMOUNT", "qualifier": "CONSTRAINT"}
    constraint = _CONSTRAINT_RE.match(value)
    if constraint:
        amount, kind = _parse_piece(constraint.group(2), locale)
        return {"kind": "CONSTRAINT", "operator": constraint.group(1), "amount": amount, "pattern": "CONSTRAINED_AMOUNT", "qualifier": "CONSTRAINT"}
    range_match = re.match(r"(?i)^(?:between|from|بين|من)\s+(.+?)\s+(?:and|to|و|إلى|الى)\s+(.+)$", value)
    if range_match:
        lower, lower_kind = _parse_piece(range_match.group(1), locale)
        upper, upper_kind = _parse_piece(range_match.group(2), locale)
        if lower > upper:
            lower, upper = upper, lower
        return {"kind": "RANGE", "lower": lower, "upper": upper, "pattern": "MONETARY_RANGE", "qualifier": "RANGE"}
    plus_minus = re.match(r"^(.+?)\s*[±]\s*(.+)$", value)
    if plus_minus:
        center, center_kind = _parse_piece(plus_minus.group(1), locale)
        delta, delta_kind = _parse_piece(plus_minus.group(2), locale)
        delta = abs(delta)
        return {"kind": "RANGE", "lower": center - delta, "upper": center + delta, "pattern": "MONETARY_RANGE", "qualifier": "RANGE"}
    dash_range = re.match(r"^(.+?)\s*[–—]\s*(.+)$", value)
    if not dash_range:
        dash_range = re.match(r"^([\d., ]+)\s*-\s*([\d., ]+)$", value)
    if dash_range:
        lower, lower_kind = _parse_piece(dash_range.group(1), locale)
        upper, upper_kind = _parse_piece(dash_range.group(2), locale)
        if lower > upper:
            lower, upper = upper, lower
        return {"kind": "RANGE", "lower": lower, "upper": upper, "pattern": "MONETARY_RANGE", "qualifier": "RANGE"}
    amount, kind = _parse_piece(value, locale)
    return {"kind": "EXACT", "amount": amount, "pattern": kind, "qualifier": "APPROXIMATE" if approximate else "EXACT", "approximate": approximate}


def _arabic_digits(value: str) -> str:
    return value.translate(str.maketrans("0123456789,.", "٠١٢٣٤٥٦٧٨٩٬٫"))


def _format_number(value: Decimal, arabic: bool = False) -> str:
    text = _decimal_text(value)
    if "." in text:
        integer, fraction = text.split(".", 1)
    else:
        integer, fraction = text, None
    sign = ""
    if integer.startswith("-"):
        sign, integer = "-", integer[1:]
    groups = []
    while len(integer) > 3:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    groups.insert(0, integer or "0")
    result = ",".join(groups)
    if fraction is not None:
        result += "." + fraction
    result = sign + result
    return _arabic_digits(result) if arabic else result


def _currency_suffix(currency: str | None, arabic: bool) -> str:
    if not currency:
        return ""
    return f" {_CURRENCY_LABEL_AR.get(currency, currency)}" if arabic else f" {currency}"


def _range_representation(amount: Decimal, currency: str | None, buckets=DEFAULT_BUCKETS) -> dict:
    magnitude = abs(amount)
    selected = next(((lo, hi) for lo, hi in buckets if lo <= magnitude < hi), None)
    overflow = selected is None
    if overflow:
        lo, hi = buckets[-1][1], None
    else:
        lo, hi = selected
    if amount < 0:
        low, high = (-(hi if hi is not None else lo), -lo)
    else:
        low, high = lo, hi
    if high is None:
        en = f"{_format_number(low)}+{_currency_suffix(currency, False)}" if amount >= 0 else f"≤ {_format_number(high)}{_currency_suffix(currency, False)}"
        ar = f"أكثر من {_format_number(low, True)}{_currency_suffix(currency, True)}" if amount >= 0 else f"أقل من أو يساوي {_format_number(high, True)}{_currency_suffix(currency, True)}"
    else:
        en = f"{_format_number(low)}–{_format_number(high)}{_currency_suffix(currency, False)}"
        ar = f"بين {_format_number(low, True)} و{_format_number(high, True)}{_currency_suffix(currency, True)}"
    return {"status": "AVAILABLE", "en": en, "ar": ar, "metadata": {"lower": _decimal_text(low), "upper": _decimal_text(high) if high is not None else None, "half_open": True, "overflow": overflow}}


def _magnitude_representation(amount: Decimal, currency: str | None) -> dict:
    absolute = abs(amount)
    if absolute == 0:
        en, ar = "Zero", "صفر"
    elif absolute < 1:
        en, ar = "Less than one", "أقل من واحد"
    else:
        exponent = absolute.adjusted()
        if exponent == 0:
            en, ar = "Units", "آحاد"
        elif exponent == 1:
            en, ar = "Tens", "عشرات"
        elif exponent == 2:
            en, ar = "Hundreds", "مئات"
        else:
            group, remainder = divmod(exponent, 3)
            en_scales = {1: "thousands", 2: "millions", 3: "billions", 4: "trillions"}
            ar_scales = {1: "الآلاف", 2: "الملايين", 3: "المليارات", 4: "التريليونات"}
            scale_en = en_scales.get(group, f"10^{group * 3}")
            scale_ar = ar_scales.get(group, f"10^{group * 3}")
            if remainder == 0:
                en, ar = scale_en.title(), scale_ar
            elif remainder == 1:
                en, ar = f"Tens of {scale_en}", f"عشرات {scale_ar}"
            else:
                en, ar = f"Hundreds of {scale_en}", f"مئات {scale_ar}"
        if amount < 0:
            en, ar = f"Negative {en}", f"سالب {ar}"
    return {"status": "AVAILABLE", "en": f"{en}{_currency_suffix(currency, False)}", "ar": f"{ar}{_currency_suffix(currency, True)}", "metadata": {"absolute_exponent": absolute.adjusted() if absolute else None}}


def _interval_for(value: dict) -> tuple[Decimal, Decimal]:
    if value["kind"] == "EXACT":
        return value["amount"], value["amount"]
    return value["lower"], value["upper"]


def _comparison(interval: tuple[Decimal, Decimal], operator: str, threshold: Any) -> tuple[str, bool | None]:
    lower, upper = interval
    if operator in {"BETWEEN", "OUTSIDE_RANGE"}:
        if not isinstance(threshold, (list, tuple)) or len(threshold) != 2:
            raise ValueError("INVALID_THRESHOLD")
        first, second = _decimal(threshold[0]), _decimal(threshold[1])
        if first > second: first, second = second, first
        inside = lower >= first and upper <= second
        outside = upper < first or lower > second
        if operator == "BETWEEN":
            return ("TRUE", True) if inside else ("FALSE", False) if outside else ("INDETERMINATE", None)
        return ("TRUE", True) if outside else ("FALSE", False) if inside else ("INDETERMINATE", None)
    target = _decimal(threshold)
    checks = {
        ">": (lower > target, upper <= target),
        ">=": (lower >= target, upper < target),
        "<": (upper < target, lower >= target),
        "<=": (upper <= target, lower > target),
        "=": (lower == upper == target, upper < target or lower > target),
        "!=": (upper < target or lower > target, lower == upper == target),
    }
    if operator not in checks:
        raise ValueError("INVALID_OPERATOR")
    true_case, false_case = checks[operator]
    return ("TRUE", True) if true_case else ("FALSE", False) if false_case else ("INDETERMINATE", None)


def generalize_threshold(amount: Decimal | str, operator: str, threshold: Any, currency: str | None = None, threshold_currency: str | None = None, interval: tuple[Decimal, Decimal] | None = None, same_unit_context: bool = False) -> dict:
    """Compare an exact amount or interval without performing FX conversion."""
    try:
        normalized_currency = _currency(currency) if currency else None
        normalized_threshold_currency = _currency(threshold_currency) if threshold_currency else None
    except ValueError as exc:
        return {"status": str(exc), "value": None, "en": None, "ar": None}
    if normalized_currency and normalized_threshold_currency and normalized_currency != normalized_threshold_currency:
        return {"status": "CURRENCY_MISMATCH", "value": None, "en": None, "ar": None}
    if bool(normalized_currency) != bool(normalized_threshold_currency) and not same_unit_context:
        return {"status": "CURRENCY_CONTEXT_REQUIRED", "value": None, "en": None, "ar": None}
    try:
        bounds = interval or (_decimal(amount), _decimal(amount))
        op = str(operator).upper().replace("≥", ">=").replace("≤", "<=").replace("≠", "!=")
        result, boolean = _comparison(bounds, op, threshold)
    except ValueError as exc:
        return {"status": str(exc), "value": None, "en": None, "ar": None}
    currency = normalized_currency or normalized_threshold_currency
    if op in {"BETWEEN", "OUTSIDE_RANGE"}:
        first, second = sorted((_decimal(threshold[0]), _decimal(threshold[1])))
        en = f"Amount is {'between' if op == 'BETWEEN' else 'outside'} {_format_number(first)} and {_format_number(second)}{_currency_suffix(currency, False)}"
        ar = f"المبلغ {'بين' if op == 'BETWEEN' else 'خارج النطاق بين'} {_format_number(first, True)} و{_format_number(second, True)}{_currency_suffix(currency, True)}"
    else:
        target = _format_number(_decimal(threshold))
        target_ar = _format_number(_decimal(threshold), True)
        en_words = {">": "exceeds", ">=": "is at least", "<": "is less than", "<=": "does not exceed", "=": "equals", "!=": "does not equal"}
        ar_words = {">": "يتجاوز", ">=": "لا يقل عن", "<": "أقل من", "<=": "لا يتجاوز", "=": "يساوي", "!=": "لا يساوي"}
        en = f"Amount {en_words[op]} {target}{_currency_suffix(currency, False)}"
        ar = f"المبلغ {ar_words[op]} {target_ar}{_currency_suffix(currency, True)}"
    return {"status": result, "value": boolean, "en": en, "ar": ar, "metadata": {"operator": op, "currency": currency, "unit_unspecified": currency is None}}


def _unavailable(status: str = "UNAVAILABLE", reason: str | None = None) -> dict:
    result = {"status": status, "en": None, "ar": None}
    if reason:
        result["reason"] = reason
    return result


def interpret_and_generalize_money(entity_text: str, context: dict | None = None, threshold_spec: dict | None = None) -> dict:
    """Interpret one already-detected ``MONETARY_AMOUNT`` entity."""
    context = dict(context or {})
    original = str(entity_text)
    representations = {"range_based": _unavailable(), "order_of_magnitude": _unavailable(), "task_aware_threshold": _unavailable("REQUIRES_THRESHOLD")}
    offsets = {key: context[key] for key in ("start", "end") if key in context}
    if context.get("entity_type") and str(context["entity_type"]).upper() != "MONETARY_AMOUNT":
        return {"original_text": original, "offsets": offsets, "interpretation": {"status": "INVALID_ENTITY_TYPE", "normalized_amount": None, "currency": None, "pattern": None, "qualifier": None}, "representations": representations}
    try:
        currency, cleaned, unknown_currency = _extract_currency(original, context)
        minor = _parse_minor_units(original, currency, context.get("locale"))
        if minor:
            parsed = {"kind": "EXACT", "amount": minor[0], "pattern": minor[1], "qualifier": "EXACT", "approximate": False}
        else:
            parsed = _parse_structured(cleaned, context.get("locale"))
        if context.get("scale") is not None and parsed["kind"] == "EXACT" and parsed["pattern"] in {"PLAIN_NUMERIC", "WRITTEN_NUMBER", "FRACTION"}:
            parsed["amount"] *= _external_scale(context["scale"])
            parsed["pattern"] = "SCALED_NUMBER"
    except ValueError as exc:
        reason = str(exc)
        interpretation = {"status": reason, "normalized_amount": None, "currency": None, "pattern": None, "qualifier": None}
        return {"original_text": original, "offsets": offsets, "interpretation": interpretation, "representations": representations}
    if unknown_currency:
        interpretation_status = "UNKNOWN_CURRENCY"
    else:
        interpretation_status = "SUCCESS"
    interpretation = {
        "status": interpretation_status,
        "pattern": parsed["pattern"],
        "qualifier": parsed["qualifier"],
        "currency": currency,
        "currency_text": unknown_currency,
        "normalized_amount": _decimal_text(parsed["amount"]) if parsed["kind"] == "EXACT" else None,
        "normalized_lower": _decimal_text(parsed["lower"]) if parsed["kind"] == "RANGE" else None,
        "normalized_upper": _decimal_text(parsed["upper"]) if parsed["kind"] == "RANGE" else None,
        "unit_unspecified": currency is None,
        "is_exact": parsed["kind"] == "EXACT" and parsed["qualifier"] == "EXACT",
    }
    if parsed["kind"] == "EXACT" and parsed["qualifier"] == "EXACT" and interpretation_status in {"SUCCESS", "UNKNOWN_CURRENCY"}:
        representations["range_based"] = _range_representation(parsed["amount"], currency)
        representations["order_of_magnitude"] = _magnitude_representation(parsed["amount"], currency)
    elif parsed["kind"] == "EXACT":
        representations["range_based"] = _unavailable("INDETERMINATE", "APPROXIMATE_AMOUNT")
        representations["order_of_magnitude"] = _unavailable("INDETERMINATE", "APPROXIMATE_AMOUNT")
    else:
        representations["range_based"] = _unavailable("INDETERMINATE", parsed["qualifier"])
        representations["order_of_magnitude"] = _unavailable("INDETERMINATE", parsed["qualifier"])
    threshold = threshold_spec or context.get("threshold_spec")
    if threshold:
        if parsed["kind"] == "CONSTRAINT" or (parsed["kind"] == "EXACT" and parsed.get("qualifier") != "EXACT"):
            representations["task_aware_threshold"] = _unavailable("INDETERMINATE", "NON_EXACT_AMOUNT")
            threshold = None
    if threshold:
        if parsed["kind"] == "EXACT":
            interval = (parsed["amount"], parsed["amount"])
        elif parsed["kind"] == "RANGE":
            interval = (parsed["lower"], parsed["upper"])
        else:
            interval = (parsed["amount"], parsed["amount"])
        representations["task_aware_threshold"] = generalize_threshold(
            parsed.get("amount", parsed.get("lower")),
            threshold.get("operator", ""),
            threshold.get("threshold", threshold.get("bounds")),
            currency=currency,
            threshold_currency=threshold.get("threshold_currency", threshold.get("currency")),
            interval=interval,
            same_unit_context=bool(threshold.get("same_unit_context")),
        )
    result = {"original_text": original, "offsets": offsets, "interpretation": interpretation, "representations": representations}
    if context.get("metadata") is not None:
        result["metadata"] = context["metadata"]
    return result


__all__ = ["DEFAULT_BUCKETS", "generalize_threshold", "interpret_and_generalize_money"]

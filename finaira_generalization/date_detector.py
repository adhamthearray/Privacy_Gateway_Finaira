"""Deterministic international date detection and precision generalization.

The detector deliberately returns an explicit status for ambiguous, relative,
non-Gregorian, and noisy input. It never guesses DMY versus MDY and never
converts a non-Gregorian calendar without an explicitly supplied rule.
"""

from __future__ import annotations

import calendar as calendar_module
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from .normalization import normalize


_DIGIT_SCRIPTS = (
    "0123456789",
    "٠١٢٣٤٥٦٧٨٩",
    "۰۱۲۳۴۵۶۷۸۹",
    "०१२३४५६७८९",
    "০১২৩৪৫৬৭৮৯",
    "๐๑๒๓๔๕๖๗๘๙",
    "០១២៣៤៥៦៧៨៩",
    "၀၁၂၃၄၅၆၇၈၉",
)
_DIGITS = str.maketrans({ord(char): str(index) for script in _DIGIT_SCRIPTS[1:] for index, char in enumerate(script)})
_IGNORABLE = re.compile(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069\u00ad]")
_ORDINAL_SUFFIX = re.compile(r"(?i)(\d{1,2})(st|nd|rd|th)\b")

EN_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
AR_GREGORIAN_MONTHS = {
    "يناير": 1, "كانون الثاني": 1, "فبراير": 2, "شباط": 2, "مارس": 3, "آذار": 3,
    "أبريل": 4, "إبريل": 4, "ابريل": 4, "نيسان": 4, "مايو": 5, "أيار": 5,
    "يونيو": 6, "يونيه": 6, "حزيران": 6, "يوليو": 7, "يوليه": 7, "تموز": 7,
    "أغسطس": 8, "اغسطس": 8, "آب": 8, "سبتمبر": 9, "أيلول": 9,
    "أكتوبر": 10, "اكتوبر": 10, "تشرين الأول": 10, "نوفمبر": 11,
    "تشرين الثاني": 11, "ديسمبر": 12, "كانون الأول": 12,
    "جانفي": 1, "فيفري": 2, "أفريل": 4, "ماي": 5, "جوان": 6, "جويلية": 7,
    "أوت": 8, "يوليوز": 7, "غشت": 8, "أغشت": 8, "شتنبر": 9, "شتمبر": 9,
    "نونبر": 11, "دجنبر": 12, "دجمبر": 12,
}
OTHER_GREGORIAN_MONTHS = {
    # Common written forms from the atlas. The numeric parser remains the
    # deterministic fallback for languages not represented in this table.
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12, "diciembre": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12, "novembre": 11, "gennaio": 1, "febbraio": 2,
    "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "dicembre": 12, "kasım": 11, "kasim": 11,
    "ocak": 1, "şubat": 2, "subat": 2, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9,
    "eylul": 9, "ekim": 10, "aralık": 12, "aralik": 12,
}
HIJRI_MONTHS = {
    "محرم": 1, "صفر": 2, "ربيع الأول": 3, "ربيع الاول": 3,
    "ربيع الثاني": 4, "ربيع الآخر": 4, "ربيع الاخر": 4, "جمادى الأولى": 5,
    "جمادى الاولى": 5, "جمادى الآخرة": 6, "جمادى الثانية": 6, "جمادى الاخر": 6,
    "رجب": 7, "شعبان": 8, "رمضان": 9, "شوال": 10, "ذو القعدة": 11,
    "ذي القعدة": 11, "ذو الحجة": 12, "ذي الحجة": 12,
    "muharram": 1, "safar": 2, "rabi i": 3, "rabi al-awwal": 3,
    "rabi ii": 4, "rabi al-thani": 4, "jumada i": 5, "jumada al-ula": 5,
    "jumada ii": 6, "jumada al-akhira": 6, "rajab": 7, "shaban": 8,
    "sha'ban": 8, "ramadan": 9, "ramadhan": 9, "shawwal": 10,
    "dhu al-qadah": 11, "dhu al-hijjah": 12,
}
PERSIAN_MONTHS = {"farvardin": 1, "ordibehesht": 2, "khordad": 3, "tir": 4, "mordad": 5, "shahrivar": 6, "mehr": 7, "aban": 8, "azar": 9, "dey": 10, "bahman": 11, "esfand": 12}

AR_WORD_NUMBERS = {
    "صفر": 0, "واحد": 1, "واحدة": 1, "الأول": 1, "الاول": 1, "أول": 1, "اول": 1,
    "اثنان": 2, "اثنين": 2, "الثاني": 2, "الثانيه": 2, "الثانية": 2,
    "ثلاثة": 3, "ثلاث": 3, "الثالث": 3, "أربعة": 4, "اربعة": 4, "الرابع": 4,
    "خمسة": 5, "الخامس": 5, "ستة": 6, "الست": 6, "السادس": 6,
    "سبعة": 7, "السابع": 7, "ثمانية": 8, "ثمان": 8, "الثامن": 8,
    "تسعة": 9, "التاسع": 9, "عشرة": 10, "العاشر": 10,
    "عشر": 10, "أحد عشر": 11, "احد عشر": 11, "الحادي عشر": 11, "اثنا عشر": 12,
    "اثني عشر": 12, "الثاني عشر": 12, "ثلاثة عشر": 13, "الثالث عشر": 13,
    "أربعة عشر": 14, "اربعة عشر": 14, "الرابع عشر": 14, "خمسة عشر": 15,
    "الخامس عشر": 15, "ستة عشر": 16, "السادس عشر": 16, "سبعة عشر": 17,
    "السابع عشر": 17, "ثمانية عشر": 18, "الثامن عشر": 18, "تسعة عشر": 19,
    "التاسع عشر": 19, "العشرون": 20, "ثلاثون": 30, "الثلاثون": 30,
    "أربعون": 40, "أربعين": 40, "خمسون": 50, "خمسين": 50, "ستون": 60, "ستين": 60,
    "سبعون": 70, "سبعين": 70, "ثمانون": 80, "ثمانين": 80, "تسعون": 90, "تسعين": 90,
    "عشرون": 20, "عشرين": 20, "ثلاثون": 30, "ثلاثين": 30,
    "مائة": 100, "مئة": 100, "ألف": 1000, "ألفين": 2000,
}
EN_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
    "thousand": 1000, "first": 1, "second": 2, "third": 3, "fourth": 4,
    "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
    "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
    "eighteenth": 18, "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}


@dataclass
class DateDetection:
    raw: str
    status: str
    reason_code: str | None = None
    calendar: str | None = None
    precision: str | None = None
    language: str | None = None
    format_family: str | None = None
    confidence: str = "LOW"
    year: int | None = None
    month: int | None = None
    day: int | None = None
    date_value: date | None = None
    start: date | None = None
    end: date | None = None
    time_text: str | None = None
    timezone_text: str | None = None
    is_relative: bool = False
    is_ambiguous: bool = False
    candidates: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def date_iso(self) -> str | None:
        return self.date_value.isoformat() if self.date_value else None


def _clean(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).translate(_DIGITS)
    text = _IGNORABLE.sub("", text).replace("ـ", "")
    text = re.sub(r"['’](?=\d{2}\b)", "", text)
    return text.strip()


def _key(value: str) -> str:
    return normalize(value, None).replace(".", "").strip()


def _month_lookup() -> dict[str, tuple[int, str, str]]:
    out: dict[str, tuple[int, str, str]] = {}
    for name, month in OTHER_GREGORIAN_MONTHS.items(): out[_key(name)] = (month, "other", "GREGORIAN")
    for name, month in EN_MONTHS.items(): out[_key(name)] = (month, "en", "GREGORIAN")
    for name, month in AR_GREGORIAN_MONTHS.items(): out[_key(name)] = (month, "ar", "GREGORIAN")
    for name, month in HIJRI_MONTHS.items(): out[_key(name)] = (month, "ar" if any("\u0600" <= c <= "\u06ff" for c in name) else "en", "HIJRI")
    for name, month in PERSIAN_MONTHS.items(): out[_key(name)] = (month, "fa", "SOLAR_HIJRI")
    return out


MONTH_LOOKUP = _month_lookup()


def _word_number(text: str, language: str) -> int | None:
    words = _key(text).replace("-", " ").replace(",", " ").split()
    if not words:
        return None
    table = {_key(key): value for key, value in (AR_WORD_NUMBERS if language == "ar" else EN_WORD_NUMBERS).items()}
    total = 0
    current = 0
    seen = False
    for word in words:
        if word in {"و", "and", "of", "the", "من", "عام", "سنة", "شهر", "يوم"}:
            continue
        if language == "ar" and word.startswith("و") and len(word) > 1:
            word = word[1:]
        value = table.get(word)
        if value is None:
            return None
        seen = True
        if value == 1000:
            total += (current or 1) * value
            current = 0
        elif value == 100:
            current = (current or 1) * value
        elif value >= 20 and current:
            current += value
        else:
            current += value
    return total + current if seen else None


def _valid_date(year: int, month: int, day: int) -> date:
    if year < 1 or year > 9999:
        raise ValueError("INVALID_YEAR")
    return date(year, month, day)


def _two_digit_year(year: int, context: dict) -> int:
    if context.get("two_digit_year_base") is None:
        raise ValueError("AMBIGUOUS_CENTURY")
    return int(context["two_digit_year_base"]) + year


def _success(raw: str, *, year: int | None, month: int | None, day: int | None, calendar: str = "GREGORIAN", precision: str = "day", language: str | None = None, family: str = "calendar", confidence: str = "HIGH", value: date | None = None, time_text: str | None = None, timezone_text: str | None = None, metadata: dict | None = None) -> DateDetection:
    return DateDetection(raw, "VERIFIED", calendar=calendar, precision=precision, language=language, format_family=family, confidence=confidence, year=year, month=month, day=day, date_value=value, time_text=time_text, timezone_text=timezone_text, metadata=metadata or {})


def _failure(raw: str, reason: str, status: str = "AMBIGUOUS", *, candidates: list[dict] | None = None, metadata: dict | None = None) -> DateDetection:
    return DateDetection(raw, status, reason_code=reason, is_ambiguous=status == "AMBIGUOUS", candidates=candidates or [], metadata=metadata or {})


def _parse_iso(text: str, raw: str) -> DateDetection | None:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?(Z|[+-]\d{2}:?\d{2})?)?", text)
    if not match:
        return None
    year, month, day = map(int, match.group(1, 2, 3))
    try: value = _valid_date(year, month, day)
    except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
    time_text = None
    zone = match.group(8)
    if match.group(4) is not None:
        time_text = ":".join(x for x in match.group(4, 5, 6) if x is not None)
        if match.group(7): time_text += "." + match.group(7)
        try:
            datetime.strptime(f"{match.group(4)}:{match.group(5)}:{match.group(6) or '00'}", "%H:%M:%S")
        except ValueError: return _failure(raw, "INVALID_TIME", "INVALID_INPUT")
    return _success(raw, year=year, month=month, day=day, value=value, family="ISO_8601_TIMESTAMP" if time_text else "ISO_8601_CALENDAR", time_text=time_text, timezone_text=zone, metadata={"time": time_text, "timezone": zone})


def _parse_week_or_ordinal(text: str, raw: str) -> DateDetection | None:
    week = re.fullmatch(r"(\d{4})-?W(\d{2})(?:-?(\d))?", text, re.I)
    if week:
        year, week_no = int(week.group(1)), int(week.group(2)); weekday = int(week.group(3) or 1)
        try: value = date.fromisocalendar(year, week_no, weekday)
        except ValueError: return _failure(raw, "INVALID_ISO_WEEK_DATE", "INVALID_INPUT")
        return _success(raw, year=value.year, month=value.month, day=value.day, value=value, family="ISO_8601_WEEK", metadata={"iso_week": week_no, "iso_weekday": weekday})
    ordinal = re.fullmatch(r"(\d{4})-?(\d{3})", text)
    if ordinal:
        year, doy = int(ordinal.group(1)), int(ordinal.group(2))
        try: value = date(year, 1, 1) + timedelta(days=doy - 1)
        except ValueError: return _failure(raw, "INVALID_ISO_ORDINAL_DATE", "INVALID_INPUT")
        if doy < 1 or doy > (366 if calendar_module.isleap(year) else 365): return _failure(raw, "INVALID_ISO_ORDINAL_DATE", "INVALID_INPUT")
        return _success(raw, year=year, month=value.month, day=value.day, value=value, family="ISO_8601_ORDINAL")
    return None


def _parse_numeric(text: str, raw: str, context: dict) -> DateDetection | None:
    requested_calendar = str(context.get("calendar", "")).upper()
    if requested_calendar in {"HIJRI", "SOLAR_HIJRI"}:
        parts = re.fullmatch(r"(\d{1,4})\s*([/_.|\\-])\s*(\d{1,2})\s*\2\s*(\d{1,4})", text)
        if parts:
            a, b, c = parts.group(1), parts.group(3), parts.group(4)
            order = str(context.get("date_order", "")).upper()
            if len(a) == 4:
                order = order or "YMD"
            if order not in {"DMY", "MDY", "YMD"}:
                return _failure(raw, "AMBIGUOUS_DATE", candidates=[{"order": "DMY"}, {"order": "MDY"}, {"order": "YMD"}])
            values = dict(zip(order, map(int, (a, b, c))))
            if 1 <= values["M"] <= 12 and 1 <= values["D"] <= 31:
                return _success(raw, year=values["Y"], month=values["M"], day=values["D"], calendar=requested_calendar, family=f"{requested_calendar}_NUMERIC", metadata={"conversion": "not_performed", "order": order})
            return _failure(raw, "INVALID_CALENDAR_DATE", "INVALID_INPUT")
    compact = re.fullmatch(r"\d{8}", text)
    if compact:
        year, month, day = int(text[:4]), int(text[4:6]), int(text[6:])
        try: value = _valid_date(year, month, day)
        except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=day, value=value, family="COMPACT_YYYYMMDD")
    partial = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", text)
    if partial:
        year, month = map(int, partial.groups())
        if not 1 <= month <= 12: return _failure(raw, "INVALID_MONTH", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=None, precision="month", family="PARTIAL_YEAR_MONTH")
    partial_reverse = re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text)
    if partial_reverse:
        month, year = map(int, partial_reverse.groups())
        if not 1 <= month <= 12: return _failure(raw, "INVALID_MONTH", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=None, precision="month", family="PARTIAL_MONTH_YEAR")
    parts = re.fullmatch(r"(\d{1,4})\s*([/_.|\\-])\s*(\d{1,2})\s*\2\s*(\d{1,4})", text)
    a = b = c = None
    if parts:
        a, b, c = parts.group(1), parts.group(3), parts.group(4)
    if not parts:
        spaced = re.fullmatch(r"(\d{1,4})\s+(\d{1,2})\s+(\d{1,4})", text)
        if spaced:
            a, b, c = spaced.groups()
        else:
            labeled = re.fullmatch(r"(?i)D(?:ay)?\s*[:=]\s*(\d{1,2})\s+M(?:onth)?\s*[:=]\s*(\d{1,2})\s+Y(?:ear)?\s*[:=]\s*(\d{2,4})", text)
            if labeled:
                day, month, year = map(int, labeled.groups())
                if year < 100: year = _two_digit_year(year, context)
                try: value = _valid_date(year, month, day)
                except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
                return _success(raw, year=year, month=month, day=day, value=value, family="LABELED_DMY")
            return None
    nums = list(map(int, (a, b, c)))
    order = str(context.get("date_order", "")).upper()
    if len(a) == 4: order = order or "YMD"
    if len(c) == 4 and not order:
        if nums[0] > 12 and nums[1] <= 12: order = "DMY"
        elif nums[1] > 12 and nums[0] <= 12: order = "MDY"
        else: return _failure(raw, "AMBIGUOUS_DATE", candidates=[{"order": "DMY"}, {"order": "MDY"}])
    if not order or order not in {"DMY", "MDY", "YMD"}:
        return _failure(raw, "AMBIGUOUS_DATE", candidates=[{"order": "DMY"}, {"order": "MDY"}, {"order": "YMD"}])
    values = dict(zip(order, nums)); year = values["Y"]
    year_component = a if order == "YMD" else c
    if len(year_component) == 2: year = _two_digit_year(year, context)
    try: value = _valid_date(year, values["M"], values["D"])
    except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
    return _success(raw, year=year, month=values["M"], day=values["D"], value=value, family=f"NUMERIC_{order}", metadata={"order": order})


def _parse_named(text: str, raw: str, context: dict) -> DateDetection | None:
    lookup = MONTH_LOOKUP
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+|[\u0600-\u06ff]+|\d+", text)
    normalized_tokens = [_key(token) for token in tokens]
    month_index = next((i for i, token in enumerate(normalized_tokens) if token in lookup), None)
    if month_index is None:
        # Try two-token Arabic month names such as كانون الثاني or ربيع الأول.
        for i in range(len(normalized_tokens) - 1):
            pair = f"{normalized_tokens[i]} {normalized_tokens[i + 1]}"
            if pair in lookup:
                month_index = i; normalized_tokens[i] = pair; del normalized_tokens[i + 1]; tokens[i] = pair; del tokens[i + 1]; break
    if month_index is None:
        return None
    month, language, calendar_name = lookup[normalized_tokens[month_index]]
    before = tokens[:month_index]; after = tokens[month_index + 1:]
    numeric = [int(x) for x in tokens if x.isdigit()]
    day = None; year = None
    if before and before[-1].isdigit(): day = int(before[-1])
    elif before: day = _word_number(" ".join(before[-3:]), "ar" if language == "ar" else "en")
    if after and after[-1].isdigit(): year = int(after[-1])
    elif after: year = _word_number(" ".join(after[-5:]), "ar" if language == "ar" else "en")
    if day is None and numeric: day = numeric[0] if numeric[0] <= 31 else None
    if year is None and len(numeric) >= 2: year = numeric[-1]
    if year is not None and year < 100: year = _two_digit_year(year, context)
    if year is None:
        return _success(raw, year=None, month=month, day=day, calendar=calendar_name, precision="day_month" if day else "month", language=language, family="NAMED_PARTIAL", confidence="MEDIUM")
    if day is not None and not 1 <= day <= 31: return _failure(raw, "INVALID_DAY", "INVALID_INPUT")
    if calendar_name == "GREGORIAN":
        try: value = _valid_date(year, month, day) if day else None
        except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
    else: value = None
    precision = "day" if day else "month"
    return _success(raw, year=year, month=month, day=day, calendar=calendar_name, precision=precision, language=language, family="NAMED_CALENDAR", value=value, metadata={"calendar_explicit": calendar_name != "GREGORIAN", "conversion": "not_performed"} if calendar_name != "GREGORIAN" else {"calendar_explicit": False})


def _parse_marked_numeric(text: str, raw: str, context: dict) -> DateDetection | None:
    # Japanese/Chinese/Korean year-month-day markers.
    marked = re.search(r"(\d{2,4})\s*(?:年|년)\s*(\d{1,2})\s*(?:月|월)\s*(\d{1,2})\s*(?:日|일)?", text)
    if marked:
        year, month, day = map(int, marked.groups())
        try: value = _valid_date(year, month, day)
        except ValueError: return _failure(raw, "INVALID_GREGORIAN_DATE", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=day, value=value, family="LOCALIZED_YMD")
    japanese = re.search(r"令和\s*(\d+)年\s*(\d{1,2})月\s*(\d{1,2})日?", text)
    if japanese:
        era_year, month, day = map(int, japanese.groups()); year = 2018 + era_year
        try: value = _valid_date(year, month, day)
        except ValueError: return _failure(raw, "INVALID_JAPANESE_ERA_DATE", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=day, calendar="JAPANESE_ERA", value=value, family="JAPANESE_ERA", metadata={"era": "REIWA", "era_year": era_year})
    roc = re.search(r"民國\s*(\d+)年\s*(\d{1,2})月\s*(\d{1,2})日?", text)
    if roc:
        era_year, month, day = map(int, roc.groups()); year = 1911 + era_year
        try: value = _valid_date(year, month, day)
        except ValueError: return _failure(raw, "INVALID_ROC_DATE", "INVALID_INPUT")
        return _success(raw, year=year, month=month, day=day, calendar="ROC", value=value, family="ROC", metadata={"era_year": era_year})
    return None


def detect_date(value: str, context: dict | None = None) -> DateDetection:
    raw = str(value)
    context = context or {}
    text = _clean(raw)
    if not text:
        return _failure(raw, "INVALID_INPUT", "INVALID_INPUT")
    if re.search(r"(?i)\b(today|tomorrow|yesterday|next|last|ago|since|before|after|circa|around)\b|(?:اليوم|غدًا|غدا|أمس|امس|القادم|الماضي|منذ|قبل|بعد|حوالي|قرابة)", text):
        anchor = context.get("anchor_date")
        if anchor:
            base = anchor if isinstance(anchor, date) else date.fromisoformat(str(anchor))
            lower = _key(text)
            delta = 1 if "tomorrow" in lower or "غدا" in lower or "غدًا" in lower else -1 if "yesterday" in lower or "أمس" in lower or "امس" in lower else 0
            if delta:
                result = base + timedelta(days=delta)
                detected = _success(raw, year=result.year, month=result.month, day=result.day, value=result, family="RELATIVE_WITH_ANCHOR", metadata={"anchor_date": base.isoformat()})
                detected.is_relative = True
                return detected
        return _failure(raw, "RELATIVE_DATE_NEEDS_ANCHOR", "NEEDS_CONTEXT")
    if re.search(r"(?i)\b(FY|fiscal|quarter|Q[1-4]|week|decade|century)\b|(?:السنة المالية|الربع|الأسبوع|التسعينيات|القرن)", text):
        q = re.search(r"(?i)\bQ([1-4])\s*(?:FY)?\s*(\d{2,4})|(?:FY|fiscal)\s*(\d{2,4})", text)
        if q:
            quarter = int(q.group(1)) if q.group(1) else None; year = int(q.group(2) or q.group(3));
            if year < 100:
                try: year = _two_digit_year(year, context)
                except ValueError: return _failure(raw, "AMBIGUOUS_CENTURY")
            return _success(raw, year=year, month=(quarter - 1) * 3 + 1 if quarter else None, day=None, precision="quarter" if quarter else "year", family="FISCAL_QUARTER" if quarter else "FISCAL_YEAR", confidence="MEDIUM", metadata={"quarter": quarter, "fiscal": True})
    iso = _parse_iso(text, raw)
    if iso: return iso
    week_or_ordinal = _parse_week_or_ordinal(text, raw)
    if week_or_ordinal: return week_or_ordinal
    marked = _parse_marked_numeric(text, raw, context)
    if marked: return marked
    if context.get("date_format"):
        try:
            parsed = datetime.strptime(text, context["date_format"]).date()
            return _success(raw, year=parsed.year, month=parsed.month, day=parsed.day, value=parsed, family="EXPLICIT_DATE_FORMAT")
        except ValueError:
            return _failure(raw, "INVALID_DATE_FORMAT_VALUE", "INVALID_INPUT")
    explicit_hijri = bool(re.search(r"(?i)(?:\bAH\b|هجري|هجرية|هـ|\bH\b)", text))
    if explicit_hijri and not any(_key(token) in MONTH_LOOKUP and MONTH_LOOKUP[_key(token)][2] == "HIJRI" for token in re.findall(r"[A-Za-z]+|[\u0600-\u06ff]+", text)):
        numeric = re.findall(r"\d+", text)
        if len(numeric) >= 3:
            day, month, year = map(int, numeric[-3:])
            if 1 <= month <= 12 and 1 <= day <= 30: return _success(raw, year=year, month=month, day=day, calendar="HIJRI", family="HIJRI_NUMERIC", metadata={"conversion": "not_performed"})
    named = _parse_named(text, raw, context)
    if named:
        if explicit_hijri and named.calendar == "GREGORIAN": named.calendar = "HIJRI"; named.metadata["conversion"] = "not_performed"
        return named
    numeric = _parse_numeric(text, raw, context)
    if numeric: return numeric
    era_year = re.fullmatch(r"(\d{2,4})\s*(AD|CE|AH|BE|BS|AM)", text, re.I)
    if era_year:
        year = int(era_year.group(1))
        era = era_year.group(2).upper()
        calendar_name = "HIJRI" if era == "AH" else "GREGORIAN"
        return _success(raw, year=year, month=None, day=None, calendar=calendar_name, precision="year", family="YEAR_ONLY", confidence="MEDIUM", metadata={"era": era, "conversion": "not_performed"} if calendar_name == "HIJRI" else {"era": era})
    if re.fullmatch(r"(?:\d{4}|\d{2})", text):
        if context.get("date_hint") == "year" or re.search(r"(?i)\b(?:AD|CE|AH|BE|BS|AM)\b|(?:عام|سنة|هجري|هـ)", text):
            year = int(text)
            calendar_name = "HIJRI" if explicit_hijri else "GREGORIAN"
            return _success(raw, year=year, month=None, day=None, calendar=calendar_name, precision="year", family="YEAR_ONLY", confidence="MEDIUM", metadata={"conversion": "not_performed"} if calendar_name == "HIJRI" else None)
        return _failure(raw, "AMBIGUOUS_YEAR_OR_IDENTIFIER", candidates=[{"kind": "YEAR"}, {"kind": "IDENTIFIER"}])
    if re.fullmatch(r"\d{9,13}", text) and context.get("date_hint") in {"epoch_seconds", "epoch_milliseconds"}:
        number = int(text); seconds = number / 1000 if context["date_hint"] == "epoch_milliseconds" else number
        parsed = datetime.fromtimestamp(seconds, timezone.utc)
        return _success(raw, year=parsed.year, month=parsed.month, day=parsed.day, value=parsed.date(), family="EPOCH", metadata={"epoch": number, "timezone": "UTC"})
    if re.search(r"[A-Za-z\u0600-\u06ff]", text) and re.search(r"\d", text):
        return _failure(raw, "UNSUPPORTED_DATE_FORMAT", "UNSUPPORTED")
    return _failure(raw, "DATE_NOT_FOUND", "NOT_FOUND")


def parse_date(value: str, date_format: str | None = None) -> date:
    detected = detect_date(value, {"date_format": date_format} if date_format else None)
    if detected.status != "VERIFIED" or detected.date_value is None or detected.calendar not in {"GREGORIAN", "JAPANESE_ERA", "ROC"}:
        raise ValueError(detected.reason_code or "AMBIGUOUS_DATE")
    return detected.date_value


def _gregorian_labels(detected: DateDetection, language: str, code: str) -> tuple[str, str]:
    year, month, day = detected.year, detected.month, detected.day
    month_en = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    month_ar = ["", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
    if code == "YEAR": return str(year), str(year)
    if code == "DECADE": return f"{(year // 10) * 10}s", f"عقد {(year // 10) * 10}"
    if code == "MONTH": return f"{month_en[month]} {year}", f"{month_ar[month]} {year}"
    if code == "QUARTER":
        quarter = (month - 1) // 3 + 1; return f"Q{quarter} {year}", f"الربع {quarter} من {year}"
    if code == "SEASON":
        season_en = ("Winter", "Spring", "Summer", "Autumn")[(month % 12) // 3]
        season_ar = {"Winter": "الشتاء", "Spring": "الربيع", "Summer": "الصيف", "Autumn": "الخريف"}[season_en]
        return f"{season_en} {year}", f"{season_ar} {year}"
    if code == "HALF_YEAR": return (f"H{1 if month <= 6 else 2} {year}", f"النصف {'الأول' if month <= 6 else 'الثاني'} من {year}")
    if day is None: return f"{month_en[month]} {year}", f"{month_ar[month]} {year}"
    return f"{day} {month_en[month]} {year}", f"{day} {month_ar[month]} {year}"


def date_levels(detected: DateDetection) -> list[dict]:
    if detected.calendar == "GREGORIAN" and detected.year and detected.month:
        if detected.precision == "day":
            codes = ["EXACT", "MONTH", "QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]
        elif detected.precision == "month":
            codes = ["MONTH", "QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]
        elif detected.precision == "quarter":
            codes = ["QUARTER", "SEASON", "HALF_YEAR", "YEAR", "DECADE", "SUPPRESSED"]
        else:
            codes = ["YEAR", "DECADE", "SUPPRESSED"]
        out = []
        for rank, code in enumerate(codes):
            if code == "SUPPRESSED":
                out.append({"code": code, "rank": rank, "label_en": "Date unspecified", "label_ar": "التاريخ غير محدد", "is_exact": False, "suppression": True})
            else:
                en, ar = _gregorian_labels(detected, "en", code)
                out.append({"code": code, "rank": rank, "label_en": en, "label_ar": ar, "is_exact": code == "EXACT" and detected.precision == "day", "suppression": False})
        return out
    if detected.calendar == "GREGORIAN" and detected.precision == "year" and detected.year:
        return [
            {"code": "YEAR", "rank": 0, "label_en": str(detected.year), "label_ar": str(detected.year), "is_exact": True, "suppression": False},
            {"code": "DECADE", "rank": 1, "label_en": f"{(detected.year // 10) * 10}s", "label_ar": f"عقد {(detected.year // 10) * 10}", "is_exact": False, "suppression": False},
            {"code": "SUPPRESSED", "rank": 2, "label_en": "Date unspecified", "label_ar": "التاريخ غير محدد", "is_exact": False, "suppression": True},
        ]
    if detected.calendar == "GREGORIAN" and detected.precision == "day_month" and detected.month:
        return [
            {"code": "EXACT", "rank": 0, "label_en": detected.raw, "label_ar": detected.raw, "is_exact": True, "suppression": False},
            {"code": "SUPPRESSED", "rank": 1, "label_en": "Date unspecified", "label_ar": "التاريخ غير محدد", "is_exact": False, "suppression": True},
        ]
    if detected.calendar in {"HIJRI", "SOLAR_HIJRI", "BUDDHIST", "JAPANESE_ERA", "ROC"}:
        calendar_label = {"HIJRI": "Hijri", "SOLAR_HIJRI": "Solar Hijri", "BUDDHIST": "Buddhist", "JAPANESE_ERA": "Japanese era", "ROC": "ROC"}.get(detected.calendar, detected.calendar)
        exact = detected.raw
        year_label = f"{calendar_label} {detected.year}" if detected.year else calendar_label
        month_label = f"{calendar_label} {detected.year}-{detected.month:02d}" if detected.year and detected.month else year_label
        return [
            {"code": "EXACT" if detected.precision == "day" else "MONTH" if detected.precision == "month" else "YEAR", "rank": 0, "label_en": exact, "label_ar": exact, "is_exact": True, "suppression": False},
            {"code": "YEAR", "rank": 1, "label_en": year_label, "label_ar": year_label, "is_exact": False, "suppression": False},
            {"code": "SUPPRESSED", "rank": 2, "label_en": "Date unspecified", "label_ar": "التاريخ غير محدد", "is_exact": False, "suppression": True},
        ]
    return []


def date_interval(detected: DateDetection, code: str) -> tuple[date | None, date | None]:
    """Return the closed Gregorian interval represented by a date level.

    Non-Gregorian values intentionally return ``(None, None)`` because the
    detector preserves those calendar systems without pretending to convert
    them to Gregorian dates.
    """
    if detected.calendar != "GREGORIAN" or not detected.year or not detected.month:
        return None, None
    if code == "SUPPRESSED":
        return None, None
    if code == "EXACT" and detected.date_value:
        return detected.date_value, detected.date_value
    if code == "MONTH":
        start = date(detected.year, detected.month, 1)
        end = date(detected.year, detected.month, calendar_module.monthrange(detected.year, detected.month)[1])
        return start, end
    if code in {"QUARTER", "SEASON"}:
        first_month = ((detected.month - 1) // 3) * 3 + 1
        start = date(detected.year, first_month, 1)
        end_month = first_month + 2
        end = date(detected.year, end_month, calendar_module.monthrange(detected.year, end_month)[1])
        return start, end
    if code == "HALF_YEAR":
        first_month = 1 if detected.month <= 6 else 7
        start = date(detected.year, first_month, 1)
        end_month = first_month + 5
        end = date(detected.year, end_month, calendar_module.monthrange(detected.year, end_month)[1])
        return start, end
    if code == "YEAR":
        return date(detected.year, 1, 1), date(detected.year, 12, 31)
    if code == "DECADE":
        start_year = (detected.year // 10) * 10
        return date(start_year, 1, 1), date(start_year + 9, 12, 31)
    return None, None


def generalize_date(value: str, level: str = "quarter", language: str = "en", date_format: str | None = None, context: dict | None = None) -> str:
    options = dict(context or {})
    if date_format: options["date_format"] = date_format
    detected = detect_date(value, options)
    if detected.status != "VERIFIED": raise ValueError(detected.reason_code or detected.status)
    levels = date_levels(detected)
    requested = level.upper()
    selected = next((row for row in levels if row["code"] == requested), None)
    if selected is None: raise ValueError("UNSUPPORTED_LEVEL")
    return selected["label_ar"] if language == "ar" else selected["label_en"]

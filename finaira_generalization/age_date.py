import re
from datetime import date, datetime
from .normalization import ARABIC_DIGITS

DEFAULT_BANDS = [(0,17,"أقل من 18 سنة","Under 18"),(18,24,"18–24 سنة","18–24 years"),(25,34,"25–34 سنة","25–34 years"),(35,44,"35–44 سنة","35–44 years"),(45,54,"45–54 سنة","45–54 years"),(55,64,"55–64 سنة","55–64 years"),(65,120,"65 سنة فأكثر","65 years and over")]

def parse_age(value: str) -> int:
    text = str(value).translate(ARABIC_DIGITS)
    m = re.search(r"(?<!\d)(\d{1,3})(?!\d)", text)
    if not m: raise ValueError("INVALID_INPUT")
    n = int(m.group(1))
    if not 0 <= n <= 120: raise ValueError("INVALID_INPUT")
    return n

def age(value: str, language="en", bands=DEFAULT_BANDS):
    n = parse_age(value)
    for lo, hi, ar, en in bands:
        if lo <= n <= hi: return ar if language == "ar" else en
    raise ValueError("INVALID_INPUT")

AR_MONTHS = {"يناير":1,"فبراير":2,"مارس":3,"أبريل":4,"ابريل":4,"مايو":5,"يونيو":6,"يوليو":7,"أغسطس":8,"اغسطس":8,"سبتمبر":9,"أكتوبر":10,"اكتوبر":10,"نوفمبر":11,"ديسمبر":12}
EN_MONTHS = {name.lower(): i for i,name in enumerate(["", "January","February","March","April","May","June","July","August","September","October","November","December"]) if i}

def parse_date(value: str, date_format: str | None = None) -> date:
    s = str(value).translate(ARABIC_DIGITS).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s): return date.fromisoformat(s)
    for name, month in {**AR_MONTHS, **EN_MONTHS}.items():
        if name in s.casefold():
            nums = re.findall(r"\d+", s)
            if len(nums) >= 2:
                y = int(nums[-1]); d = int(nums[0])
                return date(y, month, d)
    if date_format:
        return datetime.strptime(s, date_format).date()
    raise ValueError("AMBIGUOUS_DATE")

def date_generalize(value: str, level: str, language="en", date_format=None):
    d = parse_date(value, date_format)
    level = level.lower()
    if level == "year": return str(d.year)
    if level == "month": return (f"{d.strftime('%B')} {d.year}" if language != "ar" else f"{d.month}/{d.year}")
    if level == "quarter": return (f"Q{(d.month-1)//3+1} {d.year}" if language != "ar" else f"الربع {(d.month-1)//3+1} من {d.year}")
    raise ValueError("UNSUPPORTED_LEVEL")

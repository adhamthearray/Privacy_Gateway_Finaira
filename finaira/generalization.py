import hashlib, json, re
from datetime import date
from pathlib import Path

AGE_BANDS = [(0, 12, "0–12 years", "0–12 سنة"), (13, 17, "13–17 years", "13–17 سنة"),
 (18, 24, "18–24 years", "18–24 سنة"), (25, 34, "25–34 years", "25–34 سنة"),
 (35, 44, "35–44 years", "35–44 سنة"), (45, 54, "45–54 years", "45–54 سنة"),
 (55, 64, "55–64 years", "55–64 سنة"), (65, 74, "65–74 years", "65–74 سنة"), (75, 10**9, "75+ years", "75+ سنة")]
NATIONALITIES = {
 "egyptian": ("EG", ["North African", "African", "Arab", "MENA"]),
 "saudi": ("SA", ["Arab", "Middle Eastern", "MENA", "West Asian"]),
 "saudi arabian": ("SA", ["Arab", "Middle Eastern", "MENA", "West Asian"]),
 "french": ("FR", ["European", "Western European", "Northern European"]),
 "british": ("GB", ["European", "Western European", "Northern European"]),
 "american": ("US", ["North American", "Western"]), "german": ("DE", ["European", "Western European"]),
 "emirati": ("AE", ["Arab", "Middle Eastern", "MENA", "West Asian"]),
 "عربي": ("ARAB", ["Arab", "MENA", "Middle Eastern"]), "مصري": ("EG", ["North African", "African", "Arab", "MENA"]),
 "المصري": ("EG", ["North African", "African", "Arab", "MENA"]), "المصرية": ("EG", ["North African", "African", "Arab", "MENA"]),
}

def age_generalize(value: str, language: str | None = None) -> str:
    digits = value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    match = re.search(r"\d+", digits)
    if not match or int(match.group()) < 0: raise ValueError("UNRESOLVED_AGE")
    n = int(match.group())
    for low, high, en, ar in AGE_BANDS:
        if low <= n <= high: return ar if language == "ar" else en
    raise ValueError("UNRESOLVED_AGE")

def date_generalize(value: str, level: str = "QUARTER") -> str:
    parsed = date.fromisoformat(value)
    if level == "MONTH": return parsed.strftime("%B %Y")
    if level == "QUARTER": return f"Q{(parsed.month - 1)//3 + 1} {parsed.year}"
    if level == "SEASON": return f"{['Winter','Spring','Summer','Autumn'][(parsed.month % 12)//3]} {parsed.year}"
    if level == "HALF_YEAR": return f"{'First' if parsed.month <= 6 else 'Second'} half of {parsed.year}"
    if level == "YEAR": return str(parsed.year)
    if level == "DECADE": return f"{parsed.year // 10 * 10}s"
    raise ValueError("UNSUPPORTED_DATE_LEVEL")

def nationality_generalize(value: str, identity: str, scope: str, language: str | None = None) -> str:
    entry = NATIONALITIES.get(value.strip().casefold())
    if not entry: raise ValueError("UNKNOWN_OR_AMBIGUOUS_NATIONALITY")
    _, options = entry
    index = int(hashlib.sha256(f"{entry[0]}|{identity}|{scope}".encode()).hexdigest(), 16) % len(options)
    return options[index]

def generalize(entity, identity: str, scope: str, language: str | None = None, date_level: str = "QUARTER") -> str:
    t = entity.type
    if t == "AGE": return age_generalize(entity.original_value, language)
    if t == "DATE": return date_generalize(entity.original_value, date_level)
    if t == "NATIONALITY": return nationality_generalize(entity.original_value, identity, scope, language)
    rules = {"CORPORATION": "Financial services organization", "BANK": "Banking institution",
             "GOVERNMENT_ENTITY": "Government department", "OCCUPATION": "Retail occupation",
             "JOB_TITLE": "Professional role"}
    if t in rules: return rules[t]
    raise ValueError("UNRESOLVED_GENERALIZATION")

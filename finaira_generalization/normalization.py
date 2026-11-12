import re, unicodedata

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize(value: str, language: str | None = None) -> str:
    value = unicodedata.normalize("NFKC", str(value)).translate(ARABIC_DIGITS).strip().casefold()
    value = re.sub(r"[\u064B-\u065F\u0670]", "", value)
    value = value.replace("ـ", "")
    value = re.sub(r"[\u0622\u0623\u0625]", "ا", value)
    value = value.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", value)

def looks_mojibake(value: str) -> bool:
    return any(x in str(value) for x in ("Ã", "Â", "Ù", "Ø", "â€“", "â€”"))

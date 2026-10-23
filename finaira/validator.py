import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"__FN_[A-Z0-9_]+_\d{4}__")


@dataclass
class Validation:
    status: str
    error_code: str | None = None


def validate_response(response: str, vault, *, required_tokens: set[str] | None = None) -> Validation:
    issued = set(vault.by_token)
    found = set(TOKEN_RE.findall(response))
    if any(token not in issued for token in found):
        return Validation("FAIL", "UNKNOWN_OR_INVENTED_PLACEHOLDER")
    if required_tokens and not required_tokens.issubset(found):
        return Validation("FAIL", "MISSING_REQUIRED_PLACEHOLDER")
    for record in vault.by_token.values():
        if record.original and record.original in response:
            return Validation("FAIL", "SENSITIVE_VALUE_LEAKAGE")
    return Validation("PASS")

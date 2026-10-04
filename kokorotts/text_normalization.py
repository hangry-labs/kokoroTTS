import re


_LARGE_UNIT_NAMES = {
    "K": "thousand",
    "M": "million",
    "B": "billion",
    "T": "trillion",
}

# Uppercase suffixes are intentional. Lowercase forms are ambiguous with
# measurements such as 10m, while longer suffixes such as MB are identifiers.
_ENGLISH_LARGE_UNIT = re.compile(
    r"(?<![\w.])"
    r"(?P<currency>[$£])?"
    r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<unit>[KMBT])"
    r"(?!\w)"
)


def expand_english_large_units(text: str) -> str:
    """Expand unambiguous compact English number suffixes before G2P."""

    def replace(match: re.Match[str]) -> str:
        currency = match.group("currency") or ""
        number = match.group("number")
        unit = _LARGE_UNIT_NAMES[match.group("unit")]
        return f"{currency}{number} {unit}"

    return _ENGLISH_LARGE_UNIT.sub(replace, text)

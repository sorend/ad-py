"""Date utility functions for title-date extraction and year_month derivation."""

import re

# Month name → zero-padded month number, both English and Danish, case-insensitive.
_MONTH_MAP = {
    # English
    "january": "01", "february": "02", "march": "03",
    "april": "04",   "may": "05",      "june": "06",
    "july": "07",    "august": "08",   "september": "09",
    "october": "10", "november": "11", "december": "12",
    # Danish
    "januar": "01",  "februar": "02",  "marts": "03",
    # april, august, september, november, december are identical in Danish
    "maj": "05",     "juni": "06",     "juli": "07",
    "oktober": "10",
}

# yyyy.mm.dd  (dots as separators)
_RE_YMD = re.compile(r'\b(\d{4})\.(\d{2})\.(\d{2})\b')

# yyyy  <month_name>  or  <month_name>  yyyy
_MONTH_NAMES = '|'.join(
    sorted(_MONTH_MAP.keys(), key=len, reverse=True)  # longest first to avoid prefix ambiguity
)
_RE_YEAR_MONTH = re.compile(
    r'\b(?:(\d{4})\s+(' + _MONTH_NAMES + r')|(' + _MONTH_NAMES + r')\s+(\d{4}))\b',
    re.IGNORECASE,
)


def extract_title_date(raw_title: str) -> "str | None":
    """Return a 'yyyy-MM' string extracted from *raw_title*, or None.

    Supported patterns (matched in order):
    1. yyyy.mm.dd   – e.g. "2023.05.15 Summer"   → "2023-05"
    2. yyyy <month> – e.g. "2023 Juni Ferie"      → "2023-06"
    3. <month> yyyy – e.g. "Juni 2023"             → "2023-06"

    Month names may be English or Danish, case-insensitive.
    A bare year without a month name returns None.
    """
    if not raw_title:
        return None

    # Pattern 1: yyyy.mm.dd
    m = _RE_YMD.search(raw_title)
    if m:
        year, month = m.group(1), m.group(2)
        return f"{year}-{month}"

    # Pattern 2 & 3: year + month name (either order)
    m = _RE_YEAR_MONTH.search(raw_title)
    if m:
        if m.group(1):  # yyyy <month>
            year = m.group(1)
            month_num = _MONTH_MAP[m.group(2).lower()]
        else:           # <month> yyyy
            year = m.group(4)
            month_num = _MONTH_MAP[m.group(3).lower()]
        return f"{year}-{month_num}"

    return None


def compute_year_month(
    title_date: "str | None",
    median_taken_date: "str | None",
    updated: str,
) -> str:
    """Derive a 'yyyy-MM' sort key with priority: title_date → median_taken_date → updated.

    All three source strings are expected to start with 'yyyy-MM' (i.e. ISO-like
    format).  Only the first seven characters are used when deriving from
    *median_taken_date* or *updated*.
    """
    if title_date:
        return title_date
    if median_taken_date:
        return median_taken_date[:7]
    return updated[:7]

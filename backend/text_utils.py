"""
text_utils.py - UTF-8 ve mojibake duzeltme yardimcilari
"""

from __future__ import annotations

import re


_MOJIBAKE_REPLACEMENTS = {
    "Ã¼": "ü",
    "Ãœ": "Ü",
    "Ã¶": "ö",
    "Ã–": "Ö",
    "Ã§": "ç",
    "Ã‡": "Ç",
    "Ä±": "ı",
    "Ä°": "İ",
    "ÅŸ": "ş",
    "Åž": "Ş",
    "ÄŸ": "ğ",
    "Äž": "Ğ",
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¦": "...",
    "\ufeff": "",
}

_MOJIBAKE_HINTS = ("Ã", "Ä", "Å", "â€", "Â")
_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]")


def _score_text(text: str) -> tuple[int, int]:
    bad = sum(text.count(m) for m in _MOJIBAKE_HINTS)
    good = sum(text.count(m) for m in "ığüşöçİĞÜŞÖÇ")
    return (good, -bad)


def _latin1_to_utf8_fix(text: str) -> str:
    try:
        return text.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def repair_text(value: str | None) -> str:
    """
    Bozuk UTF-8 gorunumlerini mumkun oldugunca duzeltir.
    """
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)

    if any(hint in text for hint in _MOJIBAKE_HINTS):
        candidate = _latin1_to_utf8_fix(text)
        if _score_text(candidate) > _score_text(text):
            text = candidate

    for src, dst in _MOJIBAKE_REPLACEMENTS.items():
        if src in text:
            text = text.replace(src, dst)

    text = text.replace("Â ", " ").replace("Â", "")
    return text.strip()


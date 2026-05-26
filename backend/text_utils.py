"""
text_utils.py - UTF-8/mojibake duzeltme yardimcilari
"""

from __future__ import annotations

from typing import Any
import re


_MOJIBAKE_HINTS = (
    "\u00c3",  # Ã
    "\u00c4",  # Ş
    "\u00c5",  # Å
    "\u00c2",  # 
    "\u00e2\u20ac",  # â 
)
_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]")
_TURKISH_CHARS = "\u0131\u011f\u00fc\u015f\u00f6\u00e7\u0130\u011e\u00dc\u015e\u00d6\u00c7"
_PUNCT_FIXES = {
    "\u00e2\u20ac\u2122": "'",
    "\u00e2\u20ac\u02dc": "'",
    "\u00e2\u20ac\u0153": '"',
    "\u00e2\u20ac\ufffd": '"',
    "\u00e2\u20ac\u201c": "-",
    "\u00e2\u20ac\u201d": "-",
    "\u00e2\u20ac\u00a6": "...",
    "\ufeff": "",
}
_TR_TARGET_CHARS = tuple("\u0131\u0130\u011f\u011e\u015f\u015e\u00f6\u00d6\u00fc\u00dc\u00e7\u00c7")
_TR_LEGACY_TRANSLATION = str.maketrans(
    {
        "\u00fd": "\u0131",  # ý -> ı
        "\u00dd": "\u0130",  # Ý -> İ
        "\u00f0": "\u011f",  # ğ -> ğ
        "\u00d0": "\u011e",  # Ð -> Ğ
        "\u00fe": "\u015f",  # þ -> ş
        "\u00de": "\u015e",  # Þ -> Ş
    }
)


def _build_turkish_mojibake_map() -> dict[str, str]:
    variants: dict[str, str] = {}
    for correct in _TR_TARGET_CHARS:
        for decode_enc in ("latin-1", "cp1252", "cp1254"):
            try:
                once = correct.encode("utf-8").decode(decode_enc)
            except UnicodeDecodeError:
                continue
            if once != correct:
                variants[once] = correct
            try:
                twice = once.encode("utf-8").decode(decode_enc)
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if twice != once:
                variants[twice] = correct
    return dict(sorted(variants.items(), key=lambda item: len(item[0]), reverse=True))


_TR_MOJIBAKE_MAP = _build_turkish_mojibake_map()


def _replace_known_turkish_mojibake(text: str) -> str:
    for src, dst in _TR_MOJIBAKE_MAP.items():
        if src in text:
            text = text.replace(src, dst)
    return text


def _score_text(text: str) -> int:
    bad = sum(text.count(hint) for hint in _MOJIBAKE_HINTS)
    good = sum(text.count(ch) for ch in _TURKISH_CHARS)
    replacement = text.count("\ufffd")
    return (good * 3) - (bad * 4) - (replacement * 6)


def _decode_mojibake_once(text: str) -> str:
    best = text
    best_score = _score_text(text)
    for enc in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(enc, errors="strict").decode("utf-8", errors="strict")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        score = _score_text(candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return best


def repair_text(value: str | None) -> str:
    """
    Bozuk UTF-8 gorunumlerini mumkun oldugunca duzeltir.
    """
    if value is None:
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = _replace_known_turkish_mojibake(text)

    # Cok katmanli mojibake durumlari icin once decode gecisleri dene.
    for _ in range(4):
        if not any(hint in text for hint in _MOJIBAKE_HINTS):
            break
        candidate = _decode_mojibake_once(text)
        if candidate == text:
            break
        text = candidate

    for src, dst in _PUNCT_FIXES.items():
        if src in text:
            text = text.replace(src, dst)
    text = text.replace("\u00c2 ", " ").replace("\u00c2", "")
    text = _replace_known_turkish_mojibake(text)

    # Replace/cleanup sonrasi hala mojibake varsa bir tur daha dene.
    for _ in range(2):
        if not any(hint in text for hint in _MOJIBAKE_HINTS):
            break
        candidate = _decode_mojibake_once(text)
        if candidate == text:
            break
        text = candidate
    text = _replace_known_turkish_mojibake(text)

    # cp1254 kaynakli legacy gorunumleri normalize et.
    text = text.translate(_TR_LEGACY_TRANSLATION)
    return text.strip()


def repair_payload(value: Any) -> Any:
    """
    JSON benzeri veri yapilarindaki tum metin alanlarini normalize eder.
    """
    if isinstance(value, str) or value is None:
        return repair_text(value)
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for key, item in value.items():
            clean_key = repair_text(key) if isinstance(key, str) else key
            out[clean_key] = repair_payload(item)
        return out
    if isinstance(value, list):
        return [repair_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(repair_payload(item) for item in value)
    return value


def tr_lower(text: str | None) -> str:
    """
    Turkish-specific lowercasing.
    Converts 'İ' to 'i' and 'I' to 'ı' correctly before applying standard .lower().
    """
    if not text:
        return ""
    return str(text).replace("İ", "i").replace("I", "ı").lower()


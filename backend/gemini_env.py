"""
Gemini API anahtari — ortam degiskeninden okunur.

Proje kokundeki .env yuklemesi openrouter_service ile ayni mekanizmadir.
"""

from __future__ import annotations

import os

from openrouter_service import _load_dotenv_if_present

_load_dotenv_if_present()


def get_gemini_api_key() -> str:
    """GEMINI_API_KEY veya Google'un yaygin ismi GOOGLE_API_KEY; bos string yoksa."""
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.getenv(name, "").strip()
        if v:
            return v
    return ""

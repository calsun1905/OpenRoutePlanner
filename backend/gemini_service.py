"""
Google Gemini (Generative Language API) sohbet yardimcilari.

OpenRouter ile ayni mesaj semboligi: [{"role":"system"|"user"|"assistant","content":"..."}]
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from gemini_env import get_gemini_api_key

# Proje .env (gemini_env openrouter uzerinden yukler)
GEMINI_API_BASE = (
    os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta").strip()
    or "https://generativelanguage.googleapis.com/v1beta"
)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _timeout_sec() -> float:
    return max(10.0, _env_float("ORP_GEMINI_TIMEOUT_SEC", 60.0))


def _normalize_model_id(raw: str) -> str:
    m = (raw or "").strip()
    if not m:
        return ""
    if m.startswith("models/"):
        m = m.split("/", 1)[1]
    return m.split(":", 1)[0].strip()


def _default_model() -> str:
    # 2.0 stabil degilken Google onerisi: beta/experimental model adi (gemini-2.0-flash-exp).
    # Stabil kullanim icin GEMINI_MODEL=gemini-2.5-flash veya gemini-1.5-flash kullanin.
    raw = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip() or "gemini-2.0-flash-exp"
    return _normalize_model_id(raw) or "gemini-2.0-flash-exp"


def _parse_fallback_list(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,;\s]+", text):
        mid = _normalize_model_id(part)
        if not mid or mid in seen:
            continue
        seen.add(mid)
        out.append(mid)
    return out


def _fallback_models() -> list[str]:
    raw = os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-2.5-flash,gemini-1.5-flash,gemini-1.5-pro,gemini-2.5-flash-lite",
    )
    return _parse_fallback_list(raw)


def _candidate_models(model: str | None) -> list[str]:
    first = _normalize_model_id(model or "") or _default_model()
    candidates = [first]
    for m in _fallback_models():
        if m not in candidates:
            candidates.append(m)
    return candidates


def is_gemini_configured() -> bool:
    return bool(get_gemini_api_key())


def gemini_status() -> dict[str, Any]:
    return {
        "configured": is_gemini_configured(),
        "api_base": GEMINI_API_BASE,
        "default_model": _default_model(),
        "fallback_models": _fallback_models(),
        "timeout_sec": _timeout_sec(),
    }


def _headers() -> dict[str, str]:
    key = get_gemini_api_key()
    if not key:
        return {}
    return {
        "x-goog-api-key": key,
        "Content-Type": "application/json",
    }


def _messages_to_gemini_payload(
    messages: list[dict[str, str]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """systemInstruction + contents uretir."""
    system_chunks: list[str] = []
    contents: list[dict[str, Any]] = []

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "user")).strip().lower()
        content = msg.get("content")
        text = content if isinstance(content, str) else str(content or "")

        if role == "system":
            system_chunks.append(text)
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": text}]})
        elif role in ("assistant", "model"):
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    system_instruction: dict[str, Any] | None = None
    if system_chunks:
        joined = "\n".join(system_chunks).strip()
        if joined:
            system_instruction = {"parts": [{"text": joined}]}

    return system_instruction, contents


def _build_generation_config(
    temperature: float | None,
    max_tokens: int | None,
) -> dict[str, Any] | None:
    cfg: dict[str, Any] = {}
    if temperature is not None:
        try:
            cfg["temperature"] = float(temperature)
        except (TypeError, ValueError):
            pass
    if max_tokens is not None:
        try:
            cfg["maxOutputTokens"] = int(max_tokens)
        except (TypeError, ValueError):
            pass
    return cfg or None


def _extract_text_from_response(data: dict[str, Any]) -> str:
    cands = data.get("candidates") or []
    if not cands:
        return ""
    parts = (cands[0].get("content") or {}).get("parts") or []
    chunks: list[str] = []
    for p in parts:
        if isinstance(p, dict):
            t = p.get("text")
            if isinstance(t, str):
                chunks.append(t)
    return "".join(chunks)


def _usage_from_response(data: dict[str, Any]) -> dict[str, Any]:
    um = data.get("usageMetadata") or {}
    if not isinstance(um, dict):
        return {}
    total = um.get("totalTokenCount")
    out: dict[str, Any] = {}
    if total is not None:
        out["total_tokens"] = total
    return out


def _is_fallback_retryable_error(message: str) -> bool:
    msg = (message or "").lower()
    markers = [
        "(404)",  # model id yok / yeni kullaniciya kapali — sonraki modele gec
        "(429)",
        "(500)",
        "(502)",
        "(503)",
        "(504)",
        "not_found",
        "no longer available",
        "resource exhausted",
        "unavailable",
        "timeout",
        "timed out",
        "overloaded",
    ]
    return any(m in msg for m in markers)


def gemini_chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    if not messages or not isinstance(messages, list):
        raise ValueError("messages listesi zorunludur")

    key = get_gemini_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY veya GOOGLE_API_KEY ayarlanmamis")

    req_model = _normalize_model_id(model or "") or _default_model()
    sys_inst, contents = _messages_to_gemini_payload(messages)
    if not contents:
        raise ValueError("Gecerli mesaj icerigi yok")

    body: dict[str, Any] = {"contents": contents}
    if sys_inst:
        body["systemInstruction"] = sys_inst
    gen = _build_generation_config(temperature, max_tokens)
    if gen:
        body["generationConfig"] = gen

    url = f"{GEMINI_API_BASE.rstrip('/')}/models/{req_model}:generateContent"
    try:
        resp = requests.post(
            url,
            headers=_headers(),
            json=body,
            timeout=_timeout_sec(),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Gemini baglanti hatasi: {exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail = str(resp.json())
        except ValueError:
            pass
        raise RuntimeError(f"Gemini hatasi ({resp.status_code}): {detail}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError("Gemini JSON cevabi parse edilemedi") from exc

    return {
        "text": _extract_text_from_response(data),
        "model": req_model,
        "usage": _usage_from_response(data),
        "id": None,
        "raw": data,
    }


def gemini_chat_completion_with_fallback(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    tried: list[str] = []

    for candidate in _candidate_models(model):
        tried.append(candidate)
        try:
            result = gemini_chat_completion(
                messages=messages,
                model=candidate,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result["tried_models"] = tried
            return result
        except RuntimeError as exc:
            msg = str(exc)
            errors.append(f"{candidate}: {msg}")
            if _is_fallback_retryable_error(msg):
                continue
            raise

    raise RuntimeError("Tum Gemini modelleri basarisiz: " + " | ".join(errors))


def gemini_chat_completion_stream(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """OpenRouter ile uyumlu parca uretir: token, meta, done."""
    if not messages or not isinstance(messages, list):
        raise ValueError("messages listesi zorunludur")

    key = get_gemini_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY veya GOOGLE_API_KEY ayarlanmamis")

    req_model = _normalize_model_id(model or "") or _default_model()
    sys_inst, contents = _messages_to_gemini_payload(messages)
    if not contents:
        raise ValueError("Gecerli mesaj icerigi yok")

    body: dict[str, Any] = {"contents": contents}
    if sys_inst:
        body["systemInstruction"] = sys_inst
    gen = _build_generation_config(temperature, max_tokens)
    if gen:
        body["generationConfig"] = gen

    url = (
        f"{GEMINI_API_BASE.rstrip('/')}/models/{req_model}:streamGenerateContent"
        "?alt=sse"
    )
    try:
        with requests.post(
            url,
            headers=_headers(),
            json=body,
            timeout=_timeout_sec(),
            stream=True,
        ) as resp:
            if resp.status_code >= 400:
                detail = resp.text
                try:
                    detail = str(resp.json())
                except ValueError:
                    pass
                raise RuntimeError(f"Gemini hatasi ({resp.status_code}): {detail}")

            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].strip()
                if payload_str == "[DONE]":
                    yield {"type": "done"}
                    return
                try:
                    chunk = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue

                chunks = chunk if isinstance(chunk, list) else [chunk]
                for item in chunks:
                    if not isinstance(item, dict):
                        continue
                    text = _extract_text_from_response(item)
                    if text:
                        yield {"type": "token", "text": text}

                    usage = _usage_from_response(item)
                    if usage:
                        yield {
                            "type": "meta",
                            "model": req_model,
                            "id": None,
                            "usage": usage,
                        }

            yield {"type": "done"}
    except requests.RequestException as exc:
        raise RuntimeError(f"Gemini baglanti hatasi: {exc}") from exc


def gemini_chat_completion_stream_with_fallback(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    errors: list[str] = []
    tried: list[str] = []

    for candidate in _candidate_models(model):
        tried.append(candidate)
        yield {
            "type": "meta",
            "phase": "start",
            "model": candidate,
            "tried_models": tried,
        }
        try:
            for chunk in gemini_chat_completion_stream(
                messages=messages,
                model=candidate,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                if chunk.get("type") == "done":
                    yield {
                        "type": "meta",
                        "phase": "success",
                        "model": candidate,
                        "tried_models": tried,
                    }
                    yield {"type": "done"}
                    return
                if chunk.get("type") == "meta":
                    chunk = dict(chunk)
                    chunk["tried_models"] = tried
                yield chunk
        except RuntimeError as exc:
            msg = str(exc)
            errors.append(f"{candidate}: {msg}")
            yield {
                "type": "meta",
                "phase": "fallback",
                "model": candidate,
                "error": msg,
                "tried_models": tried,
            }
            if _is_fallback_retryable_error(msg):
                continue
            raise

    raise RuntimeError("Tum Gemini modelleri basarisiz: " + " | ".join(errors))

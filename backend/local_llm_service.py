"""
Local OpenAI-compatible LLM servis yardimcilari.

Bu modul, vLLM gibi OpenAI uyumlu local endpointlere
tek bir noktadan istek atmak icin kullanilir.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _base_url() -> str:
    return (os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1").strip()
            or "http://127.0.0.1:8000/v1")


def _api_key() -> str:
    return os.getenv("LOCAL_LLM_API_KEY", "").strip()


def _default_model() -> str:
    return (os.getenv("LOCAL_LLM_MODEL", "local-qwen35").strip() or "local-qwen35")


def _fallback_models() -> list[str]:
    raw = os.getenv("LOCAL_LLM_FALLBACK_MODELS", "").strip()
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw.split(","):
        model = item.strip()
        if not model or model in seen:
            continue
        seen.add(model)
        out.append(model)
    return out


def _candidate_models(model: str | None) -> list[str]:
    first = str(model or "").strip() or _default_model()
    models = [first]
    for m in _fallback_models():
        if m not in models:
            models.append(m)
    return models


def _timeout_sec() -> float:
    return max(5.0, _env_float("ORP_LOCAL_LLM_TIMEOUT_SEC", 120.0))


def _enabled() -> bool:
    return _env_flag("LOCAL_LLM_ENABLED", True)


def is_local_llm_configured() -> bool:
    return _enabled() and bool(_base_url())


def local_llm_status() -> dict[str, Any]:
    return {
        "configured": is_local_llm_configured(),
        "base_url": _base_url(),
        "default_model": _default_model(),
        "fallback_models": _fallback_models(),
        "timeout_sec": _timeout_sec(),
    }


def local_llm_list_models() -> list[str]:
    url = f"{_base_url().rstrip('/')}/models"
    headers: dict[str, str] = {}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        resp = requests.get(url, headers=headers, timeout=_timeout_sec())
    except requests.RequestException as exc:
        raise RuntimeError(f"Local model listesi alinamadi: {exc}") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json())
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Local model listesi hatasi ({resp.status_code}): {detail}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError("Local model listesi JSON parse edilemedi") from exc

    data = payload.get("data")
    if not isinstance(data, list):
        return []

    out: list[str] = []
    seen: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        model = str(row.get("id", "")).strip()
        if not model or model in seen:
            continue
        seen.add(model)
        out.append(model)
    out.sort()
    return out


def _extract_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _apply_generation_options(
    payload: dict[str, Any],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    min_p: float | None = None,
    repeat_penalty: float | None = None,
) -> None:
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if top_k is not None:
        payload["top_k"] = int(top_k)
    if min_p is not None:
        payload["min_p"] = float(min_p)
    if repeat_penalty is not None:
        payload["repeat_penalty"] = float(repeat_penalty)


def local_llm_chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    min_p: float | None = None,
    repeat_penalty: float | None = None,
) -> dict[str, Any]:
    msg_list = [m for m in messages if isinstance(m, dict)]
    if not msg_list:
        raise ValueError("'messages' bos olamaz")

    chosen_model = str(model or "").strip() or _default_model()
    payload: dict[str, Any] = {
        "model": chosen_model,
        "messages": msg_list,
    }
    _apply_generation_options(
        payload,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        repeat_penalty=repeat_penalty,
    )

    headers = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    url = f"{_base_url().rstrip('/')}/chat/completions"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=_timeout_sec())
    except requests.RequestException as exc:
        raise RuntimeError(f"Local LLM baglanti hatasi: {exc}") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json())
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Local LLM hatasi ({resp.status_code}): {detail}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise RuntimeError("Local LLM JSON parse edilemedi") from exc

    return {
        "id": body.get("id"),
        "model": body.get("model", chosen_model),
        "text": _extract_text(body),
        "usage": body.get("usage") or {},
    }


def local_llm_chat_completion_with_fallback(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    min_p: float | None = None,
    repeat_penalty: float | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    tried: list[str] = []
    for candidate in _candidate_models(model):
        tried.append(candidate)
        try:
            result = local_llm_chat_completion(
                messages=messages,
                model=candidate,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                min_p=min_p,
                repeat_penalty=repeat_penalty,
            )
            result["tried_models"] = tried[:]
            return result
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")

    raise RuntimeError("Tum local modeller basarisiz: " + " | ".join(errors))


def local_llm_chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    min_p: float | None = None,
    repeat_penalty: float | None = None,
):
    msg_list = [m for m in messages if isinstance(m, dict)]
    if not msg_list:
        raise ValueError("'messages' bos olamaz")

    chosen_model = str(model or "").strip() or _default_model()
    payload: dict[str, Any] = {
        "model": chosen_model,
        "messages": msg_list,
        "stream": True,
    }
    _apply_generation_options(
        payload,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        repeat_penalty=repeat_penalty,
    )

    headers = {"Content-Type": "application/json"}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    url = f"{_base_url().rstrip('/')}/chat/completions"
    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=_timeout_sec(),
            stream=True,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Local LLM stream baglanti hatasi: {exc}") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json())
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"Local LLM stream hatasi ({resp.status_code}): {detail}")

    yielded_model = False
    usage_payload: dict[str, Any] = {}

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            if not yielded_model:
                yield {"type": "meta", "model": chosen_model, "usage": usage_payload}
            yield {"type": "done"}
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue

        model_name = str(chunk.get("model", "")).strip() or chosen_model
        if not yielded_model:
            yielded_model = True
            yield {"type": "meta", "model": model_name, "usage": usage_payload}

        choices = chunk.get("choices") or []
        if choices:
            delta = (choices[0] or {}).get("delta") or {}
            text = delta.get("content")
            if isinstance(text, str) and text:
                yield {"type": "token", "text": text}

        usage = chunk.get("usage")
        if isinstance(usage, dict):
            usage_payload = usage

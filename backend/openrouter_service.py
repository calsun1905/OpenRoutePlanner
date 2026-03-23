"""
OpenRouter servis yardimcilari.

Bu modul, OpenRouter API'sine tek bir noktadan istek atmak icin kullanilir.
"""

from __future__ import annotations

import os
import json
import re
from typing import Any

import requests


def _load_dotenv_if_present() -> None:
    """
    Proje kokundeki .env dosyasini, sadece eksik env degiskenleri icin yukler.
    python-dotenv bagimliligina gerek duymaz.
    """
    auto_load = os.getenv("ORP_AUTO_LOAD_DOTENV", "1").strip().lower() in {"1", "true", "yes", "on"}
    if not auto_load:
        return
    # Testlerde monkeypatch edilen env davranisini bozmamak icin otomatik .env yukleme kapali.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    backend_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(backend_dir, ".."))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.isfile(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                if not key:
                    continue
                if key in os.environ:
                    continue

                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                os.environ[key] = value
    except OSError:
        return


def _normalize_model_ref(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""

    if "openrouter.ai/" in value:
        value = value.split("openrouter.ai/", 1)[1]
        value = value.split("?", 1)[0].split("#", 1)[0].strip("/")
        if value.endswith("/api"):
            value = value[:-4].strip("/")

    if value.startswith("docs/"):
        return ""
    if "/" not in value:
        return ""
    if value.startswith("ai/"):
        return ""
    return value


def _parse_model_list(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []

    result: list[str] = []
    seen: set[str] = set()

    def _append(model: str) -> None:
        normalized = _normalize_model_ref(model)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        result.append(normalized)

    url_matches = re.findall(r"https?://openrouter\.ai/[^\s,;]+", text, flags=re.IGNORECASE)
    for m in url_matches:
        _append(m)

    text_wo_urls = text
    for url in url_matches:
        text_wo_urls = text_wo_urls.replace(url, " ")

    for m in re.findall(r"\b[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9._:-]*\b", text_wo_urls, flags=re.IGNORECASE):
        _append(m)

    return result


_load_dotenv_if_present()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


def _base_url() -> str:
    return (os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
            or "https://openrouter.ai/api/v1")


def _api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _default_model() -> str:
    raw = (os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free").strip()
           or "google/gemma-3-27b-it:free")
    normalized = _normalize_model_ref(raw)
    return normalized or "google/gemma-3-27b-it:free"


def _fallback_models() -> list[str]:
    raw = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
    return _parse_model_list(raw)


def _candidate_models(model: str | None) -> list[str]:
    first = _normalize_model_ref(model or "") or _default_model()
    candidates = [first]
    for m in _fallback_models():
        if m not in candidates:
            candidates.append(m)
    return candidates


def _timeout_sec() -> float:
    return max(5.0, _env_float("ORP_OPENROUTER_TIMEOUT_SEC", 45.0))


def is_openrouter_configured() -> bool:
    return bool(_api_key())


def openrouter_status() -> dict[str, Any]:
    return {
        "configured": is_openrouter_configured(),
        "base_url": _base_url(),
        "default_model": _default_model(),
        "fallback_models": _fallback_models(),
        "timeout_sec": _timeout_sec(),
    }


def _is_non_text_model(model_obj: dict[str, Any]) -> bool:
    """
    Image/vision/video agirlikli modelleri ele.
    """
    model_id = str(model_obj.get("id", "")).lower()
    block_tokens = [
        "flux",
        "seedream",
        "recraft",
        "image",
        "vision",
        "video",
        "-vl-",
        "/vl",
    ]
    if any(token in model_id for token in block_tokens):
        return True

    arch = model_obj.get("architecture") or {}
    modality = str(arch.get("modality", "")).lower()
    if modality and any(token in modality for token in ("image", "vision", "video", "multimodal")):
        return True

    input_modalities = model_obj.get("input_modalities") or []
    output_modalities = model_obj.get("output_modalities") or []
    merged = [str(x).lower() for x in list(input_modalities) + list(output_modalities)]
    if any(m in {"image", "vision", "video"} for m in merged):
        return True

    return False


def openrouter_list_text_models() -> list[str]:
    """
    OpenRouter model listesinden text agirlikli modellerin slug listesini dondurur.
    """
    url = f"{_base_url().rstrip('/')}/models"
    headers: dict[str, str] = {}
    key = _api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        resp = requests.get(url, headers=headers, timeout=_timeout_sec())
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenRouter model listesi alinamadi: {exc}") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json())
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"OpenRouter model listesi hatasi ({resp.status_code}): {detail}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError("OpenRouter model listesi JSON parse edilemedi") from exc

    data = payload.get("data")
    if not isinstance(data, list):
        return []

    models: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = _normalize_model_ref(str(item.get("id", "")))
        if not model_id or model_id in seen:
            continue
        if _is_non_text_model(item):
            continue
        seen.add(model_id)
        models.append(model_id)

    models.sort()
    return models


def _extract_text(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content

    # Bazi cevap formatlarinda content parcalari liste olarak donebilir.
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
            elif isinstance(part, str):
                chunks.append(part)
        return "".join(chunks)

    return ""


def _is_fallback_retryable_error(message: str) -> bool:
    """
    Model bazli gecici/uyumsuz endpoint hatalarinda bir sonraki modele gec.
    """
    msg = (message or "").lower()
    status_markers = [
        "(404)",
        "(408)",
        "(409)",
        "(423)",
        "(425)",
        "(429)",
        "(500)",
        "(502)",
        "(503)",
        "(504)",
    ]
    if any(marker in msg for marker in status_markers):
        return True

    text_markers = [
        "no endpoints available matching your guardrail restrictions",
        "provider returned error",
        "temporarily rate-limited upstream",
    ]
    return any(marker in msg for marker in text_markers)


def openrouter_chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """
    OpenRouter chat completion cagrisi.

    Raises:
        RuntimeError: API/network kaynakli hatalar.
        ValueError: Mesaj formati hatalari.
    """
    if not messages or not isinstance(messages, list):
        raise ValueError("messages listesi zorunludur")

    key = _api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY ayarlanmamis")

    req_model = (model or _default_model()).strip() or _default_model()

    payload: dict[str, Any] = {
        "model": req_model,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    title = os.getenv("OPENROUTER_APP_TITLE", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title

    url = f"{_base_url().rstrip('/')}/chat/completions"

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=_timeout_sec(),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenRouter baglanti hatasi: {exc}") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json())
        except ValueError:
            detail = resp.text
        raise RuntimeError(f"OpenRouter hatasi ({resp.status_code}): {detail}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError("OpenRouter JSON cevabi parse edilemedi") from exc

    return {
        "text": _extract_text(data),
        "model": data.get("model", req_model),
        "usage": data.get("usage", {}),
        "id": data.get("id"),
        "raw": data,
    }


def openrouter_chat_completion_with_fallback(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """
    Model fallback sirasiyla chat completion cagrisi.
    """
    errors: list[str] = []
    tried: list[str] = []

    for candidate in _candidate_models(model):
        tried.append(candidate)
        try:
            result = openrouter_chat_completion(
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

    raise RuntimeError("Tum modeller basarisiz: " + " | ".join(errors))


def _extract_delta_text(chunk: dict[str, Any]) -> str:
    choices = chunk.get("choices") or []
    if not choices:
        return ""

    delta = (choices[0] or {}).get("delta") or {}
    content = delta.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
            elif isinstance(part, str):
                chunks.append(part)
        return "".join(chunks)

    return ""


def openrouter_chat_completion_stream(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """
    OpenRouter stream cagrisi yapar ve parca parca token dondurur.

    Yields:
        {"type":"token","text":"..."}
        {"type":"meta","model":"...","id":"...","usage":{...}}
        {"type":"done"}
    """
    if not messages or not isinstance(messages, list):
        raise ValueError("messages listesi zorunludur")

    key = _api_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY ayarlanmamis")

    req_model = (model or _default_model()).strip() or _default_model()
    payload: dict[str, Any] = {
        "model": req_model,
        "messages": messages,
        "stream": True,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
    title = os.getenv("OPENROUTER_APP_TITLE", "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-OpenRouter-Title"] = title

    url = f"{_base_url().rstrip('/')}/chat/completions"

    try:
        with requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=_timeout_sec(),
            stream=True,
        ) as resp:
            if resp.status_code >= 400:
                detail = ""
                try:
                    detail = str(resp.json())
                except ValueError:
                    detail = resp.text
                raise RuntimeError(f"OpenRouter hatasi ({resp.status_code}): {detail}")

            for raw_line in resp.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue

                line = raw_line.strip()
                if not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    yield {"type": "done"}
                    return

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                token_text = _extract_delta_text(chunk)
                if token_text:
                    yield {"type": "token", "text": token_text}

                usage = chunk.get("usage")
                if usage:
                    yield {
                        "type": "meta",
                        "model": chunk.get("model", req_model),
                        "id": chunk.get("id"),
                        "usage": usage,
                    }

            yield {"type": "done"}
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenRouter baglanti hatasi: {exc}") from exc


def openrouter_chat_completion_stream_with_fallback(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """
    Stream cagrisi icin model fallback.
    """
    errors: list[str] = []
    tried: list[str] = []

    for candidate in _candidate_models(model):
        tried.append(candidate)
        # UI canli modeli gostersin diye baslangic event'i
        yield {"type": "meta", "phase": "start", "model": candidate, "tried_models": tried}
        try:
            for chunk in openrouter_chat_completion_stream(
                messages=messages,
                model=candidate,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                if chunk.get("type") == "done":
                    # done event'i stream bitisinde tek kez frontend'e gitsin
                    yield {"type": "meta", "phase": "success", "model": candidate, "tried_models": tried}
                    yield {"type": "done"}
                    return
                # token/meta passthrough
                if chunk.get("type") == "meta":
                    chunk["tried_models"] = tried
                yield chunk
        except RuntimeError as exc:
            msg = str(exc)
            errors.append(f"{candidate}: {msg}")
            yield {"type": "meta", "phase": "fallback", "model": candidate, "error": msg, "tried_models": tried}
            if _is_fallback_retryable_error(msg):
                continue
            raise

    raise RuntimeError("Tum modeller basarisiz: " + " | ".join(errors))

from __future__ import annotations

import inspect
import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch


ROOT_DIR = Path(__file__).resolve().parents[2]


def abs_path(path_like: str | Path) -> Path:
    p = Path(path_like)
    if p.is_absolute():
        return p
    return ROOT_DIR / p


def ensure_dir(path_like: str | Path) -> Path:
    p = abs_path(path_like)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path_like: str | Path) -> dict[str, Any]:
    p = abs_path(path_like)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path_like: str | Path, payload: dict[str, Any]) -> None:
    p = abs_path(path_like)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def dtype_from_name(name: str):
    lower = str(name).strip().lower()
    if lower in {"bf16", "bfloat16"}:
        return torch.bfloat16
    if lower in {"fp16", "float16"}:
        return torch.float16
    if lower in {"fp32", "float32"}:
        return torch.float32
    raise ValueError(f"Unsupported dtype name: {name}")


def filter_supported_kwargs(callable_obj, kwargs: dict[str, Any]) -> dict[str, Any]:
    sig = inspect.signature(callable_obj)
    allowed = set(sig.parameters.keys())
    return {k: v for k, v in kwargs.items() if k in allowed}


def try_chat_template(tokenizer, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
        except Exception:
            pass
    chunks: list[str] = []
    for m in messages:
        role = str(m.get("role", "user")).strip()
        content = str(m.get("content", "")).strip()
        if not content:
            continue
        chunks.append(f"<{role}>: {content}")
    return "\n".join(chunks).strip()

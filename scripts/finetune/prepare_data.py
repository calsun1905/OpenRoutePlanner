from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

from common import abs_path, ensure_dir, load_json, write_json


MOJIBAKE_MAP = {
    "Ã§": "c",
    "Ä±": "i",
    "Ã¶": "o",
    "Ã¼": "u",
    "ÅŸ": "s",
    "ÄŸ": "g",
    "Ã‡": "C",
    "Ä°": "I",
    "Ã–": "O",
    "Ãœ": "U",
    "Åž": "S",
    "Äž": "G",
    "Â": "",
}


def norm_text(text: Any) -> str:
    out = str(text or "")
    for bad, good in MOJIBAKE_MAP.items():
        out = out.replace(bad, good)
    out = " ".join(out.split())
    return out.strip()


def read_jsonl(path_like: str | Path) -> list[dict[str, Any]]:
    p = abs_path(path_like)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {p}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path_like: str | Path, rows: list[dict[str, Any]]) -> None:
    p = abs_path(path_like)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def to_sft_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(raw.get("messages"), list):
        messages = []
        for m in raw["messages"]:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "")).strip().lower()
            if role not in {"system", "user", "assistant"}:
                continue
            content = norm_text(m.get("content", ""))
            if not content:
                continue
            messages.append({"role": role, "content": content})
        if len(messages) >= 2:
            return {"messages": messages}

    user = norm_text(raw.get("user") or raw.get("prompt") or "")
    assistant = norm_text(raw.get("assistant") or raw.get("response") or raw.get("completion") or "")
    system = norm_text(raw.get("system") or "")
    if not user or not assistant:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    messages.append({"role": "assistant", "content": assistant})
    return {"messages": messages}


def to_dpo_row(raw: dict[str, Any]) -> dict[str, str] | None:
    prompt = norm_text(raw.get("prompt") or raw.get("user") or "")
    chosen = norm_text(raw.get("chosen") or raw.get("preferred") or "")
    rejected = norm_text(raw.get("rejected") or raw.get("dispreferred") or "")
    if not prompt or not chosen or not rejected:
        return None
    if chosen == rejected:
        return None
    return {"prompt": prompt, "chosen": chosen, "rejected": rejected}


def is_toxic(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    for kw in keywords:
        if kw and kw.lower() in lower:
            return True
    return False


def contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    for kw in keywords:
        k = str(kw or "").strip().lower()
        if k and k in lower:
            return True
    return False


def ends_with_terminal_punctuation(text: str) -> bool:
    t = text.strip()
    return bool(t) and t[-1] in {".", "!", "?", "…"}


def has_repeated_ngram(text: str, n: int = 4, threshold: int = 3) -> bool:
    words = re.findall(r"\w+", text.lower())
    if len(words) < n * threshold:
        return False
    chunks = [" ".join(words[i:i + n]) for i in range(0, max(0, len(words) - n + 1))]
    seen: dict[str, int] = {}
    for c in chunks:
        seen[c] = seen.get(c, 0) + 1
        if seen[c] >= threshold:
            return True
    return False


def ends_with_terminal_punctuation(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if t.endswith("..."):
        return True
    return t[-1] in {".", "!", "?", "…"}


def has_long_unspaced_run(text: str, max_run: int = 32) -> bool:
    return bool(re.search(rf"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]{{{max_run},}}", text))


def has_repeated_char_run(text: str, max_run: int = 4) -> bool:
    return bool(re.search(rf"(.)\1{{{max_run},}}", text, flags=re.IGNORECASE))


def has_mojibake_artifacts(text: str) -> bool:
    bad_tokens = ("Ã", "â€", "ðŸ", "�")
    return any(t in text for t in bad_tokens)


def role_counts(messages: list[dict[str, str]]) -> dict[str, int]:
    counts = {"system": 0, "user": 0, "assistant": 0}
    for m in messages:
        r = m.get("role")
        if r in counts:
            counts[r] += 1
    return counts


def matches_single_turn_structure(messages: list[dict[str, str]]) -> bool:
    roles = [m.get("role") for m in messages]
    if roles == ["user", "assistant"]:
        return True
    return roles == ["system", "user", "assistant"]


def pick_last_by_role(messages: list[dict[str, str]], role: str) -> str:
    val = ""
    for m in messages:
        if m.get("role") == role:
            val = m.get("content", "")
    return val


def validate_sft_row(
    row: dict[str, Any],
    *,
    strict_cfg: dict[str, Any],
    drop_toxic: bool,
    toxic_keywords: list[str],
) -> list[str]:
    reasons: list[str] = []
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return ["schema_invalid_messages"]

    if bool(strict_cfg.get("require_exact_turn_structure", True)):
        if not matches_single_turn_structure(messages):
            reasons.append("invalid_turn_structure")

    counts = role_counts(messages)
    if counts["user"] == 0:
        reasons.append("missing_user")
    if counts["assistant"] == 0:
        reasons.append("missing_assistant")
    if bool(strict_cfg.get("require_single_user_and_assistant", True)):
        if counts["user"] != 1:
            reasons.append("user_count_not_one")
        if counts["assistant"] != 1:
            reasons.append("assistant_count_not_one")
    if counts["system"] > 1:
        reasons.append("system_count_gt_one")

    user_text = pick_last_by_role(messages, "user")
    assistant_text = pick_last_by_role(messages, "assistant")
    system_text = pick_last_by_role(messages, "system")

    if not user_text:
        reasons.append("empty_user_text")
    if not assistant_text:
        reasons.append("empty_assistant_text")
    if reasons:
        return reasons

    min_user_chars = int(strict_cfg.get("min_user_chars", 8))
    min_assistant_chars = int(strict_cfg.get("min_assistant_chars", 24))
    max_user_chars = int(strict_cfg.get("max_user_chars", 800))
    max_assistant_chars = int(strict_cfg.get("max_assistant_chars", 2000))

    if len(user_text) < min_user_chars:
        reasons.append("user_too_short")
    if len(user_text) > max_user_chars:
        reasons.append("user_too_long")
    if len(assistant_text) < min_assistant_chars:
        reasons.append("assistant_too_short")
    if len(assistant_text) > max_assistant_chars:
        reasons.append("assistant_too_long")

    if bool(strict_cfg.get("require_assistant_longer_than_user", True)):
        ratio_min = float(strict_cfg.get("assistant_to_user_len_ratio_min", 1.1))
        if len(assistant_text) <= len(user_text):
            reasons.append("assistant_not_longer_than_user")
        elif (len(assistant_text) / max(1, len(user_text))) < ratio_min:
            reasons.append("assistant_user_ratio_too_low")

    if bool(strict_cfg.get("require_terminal_punctuation", True)):
        if not ends_with_terminal_punctuation(assistant_text):
            reasons.append("assistant_no_terminal_punctuation")

    if has_repeated_ngram(assistant_text, n=4, threshold=3):
        reasons.append("assistant_repetition_pattern")

    forbidden_keywords = [str(x) for x in strict_cfg.get("forbidden_keywords", [])]
    if forbidden_keywords:
        joined = f"{system_text}\n{user_text}\n{assistant_text}".strip()
        if contains_any(joined, forbidden_keywords):
            reasons.append("forbidden_topic_or_keyword")

    required_any = [str(x) for x in strict_cfg.get("required_any_keywords", [])]
    if required_any:
        joined = f"{user_text}\n{assistant_text}".strip()
        if not contains_any(joined, required_any):
            reasons.append("outside_allowed_scope")

    profanity_keywords = [str(x) for x in strict_cfg.get("profanity_keywords", [])]
    if profanity_keywords and contains_any(f"{user_text}\n{assistant_text}", profanity_keywords):
        reasons.append("profanity_detected")

    if bool(strict_cfg.get("reject_mojibake_patterns", True)):
        if has_mojibake_artifacts(f"{system_text}\n{user_text}\n{assistant_text}"):
            reasons.append("mojibake_detected")

    if bool(strict_cfg.get("reject_long_unspaced_runs", True)):
        max_run = int(strict_cfg.get("max_unspaced_run", 32))
        if has_long_unspaced_run(assistant_text, max_run=max_run):
            reasons.append("assistant_long_unspaced_run")

    if bool(strict_cfg.get("reject_repeated_char_runs", True)):
        max_run = int(strict_cfg.get("max_repeated_char_run", 4))
        if has_repeated_char_run(assistant_text, max_run=max_run):
            reasons.append("assistant_repeated_char_run")

    if drop_toxic and is_toxic(assistant_text, toxic_keywords):
        reasons.append("toxic_detected")

    return reasons


def validate_dpo_row(
    row: dict[str, str],
    *,
    strict_cfg: dict[str, Any],
    drop_toxic: bool,
    toxic_keywords: list[str],
) -> list[str]:
    reasons: list[str] = []
    prompt = row["prompt"]
    chosen = row["chosen"]
    rejected = row["rejected"]

    min_prompt_chars = int(strict_cfg.get("dpo_min_prompt_chars", 8))
    min_chosen_chars = int(strict_cfg.get("dpo_min_chosen_chars", 24))
    min_rejected_chars = int(strict_cfg.get("dpo_min_rejected_chars", 8))
    max_prompt_chars = int(strict_cfg.get("dpo_max_prompt_chars", 800))
    max_chosen_chars = int(strict_cfg.get("dpo_max_chosen_chars", 2000))
    max_rejected_chars = int(strict_cfg.get("dpo_max_rejected_chars", 1200))

    if len(prompt) < min_prompt_chars:
        reasons.append("dpo_prompt_too_short")
    if len(prompt) > max_prompt_chars:
        reasons.append("dpo_prompt_too_long")
    if len(chosen) < min_chosen_chars:
        reasons.append("dpo_chosen_too_short")
    if len(chosen) > max_chosen_chars:
        reasons.append("dpo_chosen_too_long")
    if len(rejected) < min_rejected_chars:
        reasons.append("dpo_rejected_too_short")
    if len(rejected) > max_rejected_chars:
        reasons.append("dpo_rejected_too_long")

    if bool(strict_cfg.get("require_terminal_punctuation", True)):
        if not ends_with_terminal_punctuation(chosen):
            reasons.append("dpo_chosen_no_terminal_punctuation")

    if has_repeated_ngram(chosen, n=4, threshold=3):
        reasons.append("dpo_chosen_repetition_pattern")

    if chosen.strip() == rejected.strip():
        reasons.append("dpo_chosen_equals_rejected")

    if bool(strict_cfg.get("require_chosen_longer_than_rejected", True)) and len(chosen) <= len(rejected):
        reasons.append("dpo_chosen_not_longer")

    if bool(strict_cfg.get("require_chosen_longer_than_prompt", True)):
        ratio_min = float(strict_cfg.get("chosen_to_prompt_len_ratio_min", 1.2))
        if len(chosen) <= len(prompt):
            reasons.append("dpo_chosen_not_longer_than_prompt")
        elif (len(chosen) / max(1, len(prompt))) < ratio_min:
            reasons.append("dpo_chosen_prompt_ratio_too_low")

    forbidden_keywords = [str(x) for x in strict_cfg.get("forbidden_keywords", [])]
    if forbidden_keywords and contains_any(f"{prompt}\n{chosen}\n{rejected}", forbidden_keywords):
        reasons.append("forbidden_topic_or_keyword")

    required_any = [str(x) for x in strict_cfg.get("required_any_keywords", [])]
    if required_any and not contains_any(f"{prompt}\n{chosen}", required_any):
        reasons.append("outside_allowed_scope")

    profanity_keywords = [str(x) for x in strict_cfg.get("profanity_keywords", [])]
    if profanity_keywords and contains_any(f"{prompt}\n{chosen}\n{rejected}", profanity_keywords):
        reasons.append("profanity_detected")

    if bool(strict_cfg.get("reject_mojibake_patterns", True)):
        if has_mojibake_artifacts(f"{prompt}\n{chosen}\n{rejected}"):
            reasons.append("mojibake_detected")

    if bool(strict_cfg.get("reject_long_unspaced_runs", True)):
        max_run = int(strict_cfg.get("max_unspaced_run", 32))
        if has_long_unspaced_run(chosen, max_run=max_run):
            reasons.append("dpo_chosen_long_unspaced_run")
        if has_long_unspaced_run(rejected, max_run=max_run):
            reasons.append("dpo_rejected_long_unspaced_run")

    if bool(strict_cfg.get("reject_repeated_char_runs", True)):
        max_run = int(strict_cfg.get("max_repeated_char_run", 4))
        if has_repeated_char_run(chosen, max_run=max_run):
            reasons.append("dpo_chosen_repeated_char_run")
        if has_repeated_char_run(rejected, max_run=max_run):
            reasons.append("dpo_rejected_repeated_char_run")

    if drop_toxic and (
        is_toxic(chosen, toxic_keywords)
        or is_toxic(rejected, toxic_keywords)
        or is_toxic(prompt, toxic_keywords)
    ):
        reasons.append("toxic_detected")

    return reasons


def stable_key(obj: dict[str, Any]) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def split_rows(rows: list[dict[str, Any]], train_ratio: float, val_ratio: float, seed: int):
    if not rows:
        return [], [], []
    idxs = list(range(len(rows)))
    rnd = random.Random(seed)
    rnd.shuffle(idxs)
    n = len(idxs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = [rows[i] for i in idxs[:n_train]]
    val = [rows[i] for i in idxs[n_train:n_train + n_val]]
    test = [rows[i] for i in idxs[n_train + n_val:]]
    return train, val, test


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare SFT and DPO datasets.")
    parser.add_argument("--config", default="scripts/finetune/configs/default_train_config.json")
    args = parser.parse_args()

    cfg = load_json(args.config)
    paths = cfg["paths"]
    data_cfg = cfg["data"]
    split_cfg = data_cfg["split"]
    seed = int(cfg.get("seed", 42))

    out_dir = ensure_dir(paths["prepared_data_dir"])

    raw_sft = read_jsonl(paths["sft_input_jsonl"])
    raw_dpo = read_jsonl(paths["dpo_input_jsonl"])

    sft_rows: list[dict[str, Any]] = []
    dpo_rows: list[dict[str, str]] = []

    seen_sft: set[str] = set()
    seen_dpo: set[str] = set()

    min_assistant_chars = int(data_cfg.get("min_assistant_chars", 16))
    drop_toxic = bool(data_cfg.get("drop_toxic", True))
    toxic_keywords = [str(x) for x in data_cfg.get("toxic_keywords", [])]
    strict_cfg = dict(data_cfg.get("strict", {}))
    strict_enabled = bool(strict_cfg.get("enabled", True))
    if "min_assistant_chars" not in strict_cfg:
        strict_cfg["min_assistant_chars"] = min_assistant_chars

    dropped_sft_reasons: dict[str, int] = {}
    dropped_dpo_reasons: dict[str, int] = {}

    def mark(reason_map: dict[str, int], reasons: list[str]) -> None:
        for r in reasons:
            reason_map[r] = reason_map.get(r, 0) + 1

    for raw in raw_sft:
        row = to_sft_row(raw)
        if row is None:
            mark(dropped_sft_reasons, ["schema_unusable_sft"])
            continue
        reasons = validate_sft_row(
            row,
            strict_cfg=strict_cfg if strict_enabled else {"min_assistant_chars": min_assistant_chars},
            drop_toxic=drop_toxic,
            toxic_keywords=toxic_keywords,
        )
        if reasons:
            mark(dropped_sft_reasons, reasons)
            continue
        k = stable_key(row)
        if k in seen_sft:
            mark(dropped_sft_reasons, ["duplicate_sft"])
            continue
        seen_sft.add(k)
        sft_rows.append(row)

    for raw in raw_dpo:
        row = to_dpo_row(raw)
        if row is None:
            mark(dropped_dpo_reasons, ["schema_unusable_dpo"])
            continue
        reasons = validate_dpo_row(
            row,
            strict_cfg=strict_cfg if strict_enabled else {},
            drop_toxic=drop_toxic,
            toxic_keywords=toxic_keywords,
        )
        if reasons:
            mark(dropped_dpo_reasons, reasons)
            continue
        k = stable_key(row)
        if k in seen_dpo:
            mark(dropped_dpo_reasons, ["duplicate_dpo"])
            continue
        seen_dpo.add(k)
        dpo_rows.append(row)

    tr, va, te = split_rows(
        sft_rows,
        float(split_cfg["train_ratio"]),
        float(split_cfg["val_ratio"]),
        seed,
    )
    dtr, dva, dte = split_rows(
        dpo_rows,
        float(split_cfg["train_ratio"]),
        float(split_cfg["val_ratio"]),
        seed,
    )

    write_jsonl(out_dir / "train_sft.jsonl", tr)
    write_jsonl(out_dir / "val_sft.jsonl", va)
    write_jsonl(out_dir / "test_sft.jsonl", te)

    write_jsonl(out_dir / "train_dpo.jsonl", dtr)
    write_jsonl(out_dir / "val_dpo.jsonl", dva)
    write_jsonl(out_dir / "test_dpo.jsonl", dte)

    eval_prompts = []
    seen_prompts = set()
    for row in te:
        user_msg = ""
        for msg in row["messages"]:
            if msg["role"] == "user":
                user_msg = msg["content"]
        if user_msg and user_msg not in seen_prompts:
            seen_prompts.add(user_msg)
            eval_prompts.append({"prompt": user_msg})
    write_jsonl(out_dir / "eval_prompts.jsonl", eval_prompts)

    summary = {
        "seed": seed,
        "sft": {
            "raw": len(raw_sft),
            "clean": len(sft_rows),
            "train": len(tr),
            "val": len(va),
            "test": len(te),
            "dropped_total": sum(dropped_sft_reasons.values()),
            "dropped_reasons": dropped_sft_reasons,
        },
        "dpo": {
            "raw": len(raw_dpo),
            "clean": len(dpo_rows),
            "train": len(dtr),
            "val": len(dva),
            "test": len(dte),
            "dropped_total": sum(dropped_dpo_reasons.values()),
            "dropped_reasons": dropped_dpo_reasons,
        },
        "eval_prompts": len(eval_prompts),
        "strict_mode": strict_enabled,
    }
    write_json(out_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

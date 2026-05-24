from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import abs_path, ensure_dir, load_json, set_seed, try_chat_template


def load_prompts(path_like: str | Path) -> list[str]:
    p = abs_path(path_like)
    prompts = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            prompt = str(row.get("prompt", "")).strip()
            if prompt:
                prompts.append(prompt)
    return prompts


def generate_text(model, tokenizer, prompt: str, max_new_tokens: int = 512) -> str:
    messages = [{"role": "user", "content": prompt}]
    text = try_chat_template(tokenizer, messages)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
            top_k=40,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    decoded = tokenizer.decode(out[0], skip_special_tokens=True)
    if decoded.startswith(text):
        return decoded[len(text):].strip()
    return decoded.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate blind eval outputs from multiple checkpoints.")
    parser.add_argument("--config", default="scripts/finetune/configs/default_train_config.json")
    parser.add_argument("--prompts", default="artifacts/finetune/data/eval_prompts.jsonl")
    parser.add_argument("--max-prompts", type=int, default=100)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()

    cfg = load_json(args.config)
    set_seed(int(cfg.get("seed", 42)))
    paths = cfg["paths"]

    out_dir = ensure_dir(paths["eval_dir"])
    prompts = load_prompts(args.prompts)[: args.max_prompts]

    models = {
        "baseline": cfg["model"]["base_model"],
        "sft": paths["merged_sft_model_dir"],
        "sft_dpo": paths["merged_dpo_model_dir"],
    }

    outputs = []
    for label, model_ref in models.items():
        model_path = str(abs_path(model_ref)) if Path(str(model_ref)).exists() else str(model_ref)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        model.eval()
        for idx, prompt in enumerate(prompts):
            answer = generate_text(model, tokenizer, prompt, max_new_tokens=args.max_new_tokens)
            outputs.append({"prompt_id": idx, "model": label, "prompt": prompt, "answer": answer})
        del model
        del tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    json_path = out_dir / "blind_eval_outputs.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)

    csv_path = out_dir / "blind_eval_sheet.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "prompt_id",
                "model",
                "prompt",
                "answer",
                "naturalness_score_1_5",
                "factuality_score_1_5",
                "helpfulness_score_1_5",
                "fluency_score_1_5",
                "hallucination_flag_0_1",
                "reviewer_notes",
            ],
        )
        writer.writeheader()
        for row in outputs:
            writer.writerow(row)

    print(json.dumps({"outputs": len(outputs), "json": str(json_path), "csv": str(csv_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

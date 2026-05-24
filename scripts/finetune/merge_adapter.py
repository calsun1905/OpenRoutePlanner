from __future__ import annotations

import argparse
import json

import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer

from common import abs_path, ensure_dir, load_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into a full model.")
    parser.add_argument("--config", default="scripts/finetune/configs/default_train_config.json")
    parser.add_argument("--stage", choices=["sft", "dpo"], required=True)
    args = parser.parse_args()

    cfg = load_json(args.config)
    model_cfg = cfg["model"]
    paths = cfg["paths"]

    if args.stage == "sft":
        adapter_dir = abs_path(paths["sft_adapter_dir"])
        merged_dir = ensure_dir(paths["merged_sft_model_dir"])
    else:
        adapter_dir = abs_path(paths["dpo_adapter_dir"])
        merged_dir = ensure_dir(paths["merged_dpo_model_dir"])

    model = AutoPeftModelForCausalLM.from_pretrained(
        str(adapter_dir),
        torch_dtype=torch.bfloat16,
        trust_remote_code=bool(model_cfg.get("trust_remote_code", False)),
        device_map="auto",
    )
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(str(merged_dir), safe_serialization=True)

    tokenizer = AutoTokenizer.from_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(merged_dir))

    result = {
        "stage": args.stage,
        "adapter_dir": str(adapter_dir),
        "merged_dir": str(merged_dir),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

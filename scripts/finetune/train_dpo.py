from __future__ import annotations

import argparse
import json

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import abs_path, ensure_dir, filter_supported_kwargs, load_json, set_seed, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DPO training from merged SFT model.")
    parser.add_argument("--config", default="scripts/finetune/configs/default_train_config.json")
    args = parser.parse_args()

    cfg = load_json(args.config)
    set_seed(int(cfg.get("seed", 42)))

    try:
        from trl import DPOConfig, DPOTrainer
    except ImportError as exc:
        raise RuntimeError("TRL is required. Install requirements-finetune.txt first.") from exc

    model_cfg = cfg["model"]
    paths = cfg["paths"]
    dpo_cfg = cfg["dpo"]
    lora_cfg = cfg["lora"]

    train_file = abs_path(paths["prepared_data_dir"]) / "train_dpo.jsonl"
    val_file = abs_path(paths["prepared_data_dir"]) / "val_dpo.jsonl"
    model_dir = abs_path(paths["merged_sft_model_dir"])
    out_dir = ensure_dir(paths["dpo_adapter_dir"])

    ds = load_dataset(
        "json",
        data_files={"train": str(train_file), "validation": str(val_file)},
    )

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=torch.bfloat16,
        trust_remote_code=bool(model_cfg.get("trust_remote_code", False)),
        device_map="auto",
    )
    model.config.use_cache = False

    peft_config = LoraConfig(**lora_cfg)

    dpo_kwargs = {
        "output_dir": str(out_dir),
        "num_train_epochs": float(dpo_cfg["epochs"]),
        "learning_rate": float(dpo_cfg["learning_rate"]),
        "lr_scheduler_type": str(dpo_cfg["lr_scheduler_type"]),
        "warmup_ratio": float(dpo_cfg["warmup_ratio"]),
        "weight_decay": float(dpo_cfg["weight_decay"]),
        "beta": float(dpo_cfg["beta"]),
        "max_length": int(dpo_cfg["max_length"]),
        "max_prompt_length": int(dpo_cfg["max_length"] // 2),
        "per_device_train_batch_size": int(dpo_cfg["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(dpo_cfg["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(dpo_cfg["gradient_accumulation_steps"]),
        "logging_steps": int(dpo_cfg["logging_steps"]),
        "eval_steps": int(dpo_cfg["eval_steps"]),
        "save_steps": int(dpo_cfg["save_steps"]),
        "save_total_limit": int(dpo_cfg["save_total_limit"]),
        "load_best_model_at_end": bool(dpo_cfg["load_best_model_at_end"]),
        "bf16": True,
        "gradient_checkpointing": True,
        "seed": int(cfg.get("seed", 42)),
        "report_to": "none",
        "eval_strategy": "steps",
        "save_strategy": "steps"
    }
    train_args = DPOConfig(**filter_supported_kwargs(DPOConfig, dpo_kwargs))

    trainer_kwargs = {
        "model": model,
        "args": train_args,
        "train_dataset": ds["train"],
        "eval_dataset": ds["validation"],
        "peft_config": peft_config,
        "processing_class": tokenizer,
        "tokenizer": tokenizer,
    }

    trainer = None
    err = None
    for drop_keys in (set(), {"processing_class"}, {"tokenizer"}):
        trial = {k: v for k, v in trainer_kwargs.items() if k not in drop_keys}
        try:
            trainer = DPOTrainer(**trial)
            err = None
            break
        except TypeError as exc:
            err = exc
            continue
    if trainer is None and err is not None:
        raise err

    trainer.train()
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    meta = {
        "stage": "dpo",
        "base_model": str(model_dir),
        "output_dir": str(out_dir),
        "train_rows": len(ds["train"]),
        "val_rows": len(ds["validation"]),
        "seed": int(cfg.get("seed", 42)),
    }
    write_json(abs_path(paths["dpo_adapter_dir"]) / "run_meta.json", meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

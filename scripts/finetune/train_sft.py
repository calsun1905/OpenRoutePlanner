from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from common import (
    abs_path,
    dtype_from_name,
    ensure_dir,
    filter_supported_kwargs,
    load_json,
    set_seed,
    try_chat_template,
    write_json,
)


def build_sft_text(example, tokenizer):
    return try_chat_template(tokenizer, example["messages"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SFT QLoRA training.")
    parser.add_argument("--config", default="scripts/finetune/configs/default_train_config.json")
    args = parser.parse_args()

    cfg = load_json(args.config)
    set_seed(int(cfg.get("seed", 42)))

    try:
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise RuntimeError("TRL is required. Install requirements-finetune.txt first.") from exc

    paths = cfg["paths"]
    model_cfg = cfg["model"]
    sft_cfg = cfg["sft"]
    qlora_cfg = cfg["qlora"]
    lora_cfg = cfg["lora"]

    data_dir = abs_path(paths["prepared_data_dir"])
    train_file = data_dir / "train_sft.jsonl"
    val_file = data_dir / "val_sft.jsonl"
    out_dir = ensure_dir(paths["sft_adapter_dir"])

    ds = load_dataset(
        "json",
        data_files={"train": str(train_file), "validation": str(val_file)},
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["base_model"],
        trust_remote_code=bool(model_cfg.get("trust_remote_code", False)),
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    bnb_dtype = dtype_from_name(qlora_cfg.get("bnb_4bit_compute_dtype", "bfloat16"))
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=bool(qlora_cfg.get("load_in_4bit", True)),
        bnb_4bit_quant_type=str(qlora_cfg.get("bnb_4bit_quant_type", "nf4")),
        bnb_4bit_use_double_quant=bool(qlora_cfg.get("bnb_4bit_use_double_quant", True)),
        bnb_4bit_compute_dtype=bnb_dtype,
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["base_model"],
        trust_remote_code=bool(model_cfg.get("trust_remote_code", False)),
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.config.use_cache = False

    peft_config = LoraConfig(**lora_cfg)

    sft_kwargs = {
        "output_dir": str(out_dir),
        "num_train_epochs": float(sft_cfg["epochs"]),
        "learning_rate": float(sft_cfg["learning_rate"]),
        "lr_scheduler_type": str(sft_cfg["lr_scheduler_type"]),
        "warmup_ratio": float(sft_cfg["warmup_ratio"]),
        "weight_decay": float(sft_cfg["weight_decay"]),
        "per_device_train_batch_size": int(sft_cfg["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(sft_cfg["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(sft_cfg["gradient_accumulation_steps"]),
        "logging_steps": int(sft_cfg["logging_steps"]),
        "eval_steps": int(sft_cfg["eval_steps"]),
        "save_steps": int(sft_cfg["save_steps"]),
        "save_total_limit": int(sft_cfg["save_total_limit"]),
        "load_best_model_at_end": bool(sft_cfg["load_best_model_at_end"]),
        "metric_for_best_model": str(sft_cfg["metric_for_best_model"]),
        "greater_is_better": bool(sft_cfg["greater_is_better"]),
        "bf16": True,
        "gradient_checkpointing": True,
        "seed": int(cfg.get("seed", 42)),
        "report_to": "none",
        "eval_strategy": "steps",
        "save_strategy": "steps",
        "max_length": int(sft_cfg["max_seq_len"]),
        "max_seq_length": int(sft_cfg["max_seq_len"]),
        "dataset_num_proc": 1,
    }

    train_args = SFTConfig(**filter_supported_kwargs(SFTConfig, sft_kwargs))

    trainer_kwargs = {
        "model": model,
        "args": train_args,
        "train_dataset": ds["train"],
        "eval_dataset": ds["validation"],
        "peft_config": peft_config,
        "formatting_func": lambda ex: build_sft_text(ex, tokenizer),
        "processing_class": tokenizer,
        "tokenizer": tokenizer,
    }

    trainer = None
    err = None
    for drop_keys in (set(), {"processing_class"}, {"tokenizer"}):
        trial = {k: v for k, v in trainer_kwargs.items() if k not in drop_keys}
        try:
            trainer = SFTTrainer(**trial)
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
        "stage": "sft",
        "base_model": model_cfg["base_model"],
        "output_dir": str(out_dir),
        "train_rows": len(ds["train"]),
        "val_rows": len(ds["validation"]),
        "seed": int(cfg.get("seed", 42)),
    }
    write_json(Path(out_dir) / "run_meta.json", meta)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

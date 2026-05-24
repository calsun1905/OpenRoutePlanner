# Fine-tune Pipeline (SFT -> DPO -> GGUF Q4_K_M)

This folder provides an end-to-end training pipeline for:

1. Data preparation (SFT + DPO formats)
2. SFT with QLoRA
3. Adapter merge (SFT)
4. DPO training
5. Adapter merge (DPO)
6. Blind evaluation sheet generation
7. GGUF quantization handoff for LM Studio

RAG is intentionally out of scope for this pipeline.

## 1) Install dependencies

```bash
pip install -r requirements-finetune.txt
```

## 2) Prepare config and raw datasets

Edit:

- `scripts/finetune/configs/default_train_config.json`

Put raw files to:

- `artifacts/finetune/input/sft_raw.jsonl`
- `artifacts/finetune/input/dpo_raw.jsonl`

Raw accepted examples:

SFT:

```json
{"messages":[{"role":"system","content":"..."},{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
```

or:

```json
{"user":"...", "assistant":"...", "system":"optional"}
```

DPO:

```json
{"prompt":"...", "chosen":"...", "rejected":"..."}
```

## 3) Prepare clean splits

```bash
python scripts/finetune/prepare_data.py --config scripts/finetune/configs/default_train_config.json
```

Outputs:

- `artifacts/finetune/data/train_sft.jsonl`
- `artifacts/finetune/data/val_sft.jsonl`
- `artifacts/finetune/data/test_sft.jsonl`
- `artifacts/finetune/data/train_dpo.jsonl`
- `artifacts/finetune/data/val_dpo.jsonl`
- `artifacts/finetune/data/test_dpo.jsonl`
- `artifacts/finetune/data/eval_prompts.jsonl`

## 4) SFT training

```bash
python scripts/finetune/train_sft.py --config scripts/finetune/configs/default_train_config.json
```

## 5) Merge SFT adapter

```bash
python scripts/finetune/merge_adapter.py --config scripts/finetune/configs/default_train_config.json --stage sft
```

## 6) DPO training

```bash
python scripts/finetune/train_dpo.py --config scripts/finetune/configs/default_train_config.json
```

## 7) Merge DPO adapter

```bash
python scripts/finetune/merge_adapter.py --config scripts/finetune/configs/default_train_config.json --stage dpo
```

## 8) Generate blind eval sheet

```bash
python scripts/finetune/evaluate_models.py --config scripts/finetune/configs/default_train_config.json
```

Generated files:

- `artifacts/finetune/eval/blind_eval_outputs.json`
- `artifacts/finetune/eval/blind_eval_sheet.csv`
- `scripts/finetune/human_eval_rubric.md` (manual scoring guide)

## 9) Quantize to GGUF Q4_K_M (LM Studio target)

Use the runbook:

- `scripts/finetune/quantize_gguf_q4km.md`

Optional LM Studio preset:

- `scripts/finetune/lm_studio_preset_recommended.json`

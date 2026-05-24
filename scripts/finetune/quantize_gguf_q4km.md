# GGUF Q4_K_M Quantize Runbook (LM Studio)

This runbook converts `merged_dpo_model` to GGUF and quantizes to Q4_K_M.

## Prerequisites

- Linux machine preferred (quantization tooling is most stable there).
- `llama.cpp` built successfully.
- Final merged model exists:
  - `artifacts/finetune/runs/merged_dpo_model`

## 1) Clone and build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build --config Release
```

## 2) Convert HF model to GGUF F16

```bash
python convert_hf_to_gguf.py \
  ../OpenRoutePlanner/artifacts/finetune/runs/merged_dpo_model \
  --outfile ../OpenRoutePlanner/artifacts/finetune/runs/merged_dpo_model-f16.gguf \
  --outtype f16
```

## 3) Quantize to Q4_K_M

```bash
./build/bin/llama-quantize \
  ../OpenRoutePlanner/artifacts/finetune/runs/merged_dpo_model-f16.gguf \
  ../OpenRoutePlanner/artifacts/finetune/runs/merged_dpo_model-Q4_K_M.gguf \
  Q4_K_M
```

## 4) LM Studio smoke test

- Load `merged_dpo_model-Q4_K_M.gguf` in LM Studio.
- Test:
  1. Casual Turkish conversation
  2. Long structured response prompt
  3. Instruction-following prompt (format-sensitive)

## 5) Metadata note

Save a small deployment note:

- Base: `ytu-ce-cosmos/Turkish-Llama-8b-Instruct-v0.1`
- Training: `SFT (QLoRA) -> DPO`
- Quant: `GGUF Q4_K_M`

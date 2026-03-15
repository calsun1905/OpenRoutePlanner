#!/usr/bin/env python3
"""
Model optimization helper: ONNX export (best-effort) and quantize placeholder.

Usage:
  python scripts/tools/optimize_model.py --mode onnx --out-dir OpenRoutePlanner/backend/data
"""
import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["onnx","quantize"], default="onnx")
parser.add_argument("--model-name", default="dbmdz/bert-base-turkish-uncased")
parser.add_argument("--out-dir", default=os.path.join("OpenRoutePlanner","backend","data"))
args = parser.parse_args()

print(f"[optimize_model] mode={args.mode} model={args.model_name} out_dir={args.out_dir}")

if args.mode == "quantize":
    print("[optimize_model] Quantize flow is not implemented automatically.\nPlease consider using bitsandbytes or transformers.optimize to quantize the model.\nThis step may require pip installs and manual validation.")
    sys.exit(0)

# ONNX export
try:
    import torch
    from transformers import AutoModel, AutoTokenizer
except Exception as e:
    print(f"[optimize_model] Missing dependency: {e}")
    print("Install: pip install torch transformers")
    sys.exit(2)

out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)
onnx_path = os.path.join(out_dir, args.model_name.replace('/', '_') + '.onnx')

print('[optimize_model] Loading tokenizer and model (may use cached weights)')
try:
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModel.from_pretrained(args.model_name)
    model.eval()
except Exception as e:
    print('[optimize_model] Error loading model:', e)
    sys.exit(3)

# Export on CPU to improve portability
device = torch.device('cpu')
model.to(device)

sample_text = "Kadıköy"
inputs = tokenizer(sample_text, return_tensors='pt')
inputs = {k: v.to(device) for k, v in inputs.items()}

print(f"[optimize_model] Exporting to ONNX: {onnx_path}")
try:
    # torch.onnx.export requires positional args for the model forward; build tuple
    input_tuple = tuple(inputs[k] for k in sorted(inputs.keys()))
    input_names = [k for k in sorted(inputs.keys())]
    dynamic_axes = {k: {0: 'batch_size', 1: 'seq_len'} for k in input_names}

    torch.onnx.export(
        model,
        input_tuple,
        onnx_path,
        input_names=input_names,
        output_names=["last_hidden_state"],
        opset_version=18,
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,
    )
    print('[optimize_model] ONNX export completed')
except Exception as e:
    print('[optimize_model] ONNX export failed:', e)
    sys.exit(4)

print('[optimize_model] Done')

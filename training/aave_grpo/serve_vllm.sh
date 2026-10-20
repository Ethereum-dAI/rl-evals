#!/usr/bin/env bash
# vLLM for rollouts: base Qwen3-8B plus hot-loadable LoRA adapters, thinking off via the shared chat template.
# Shares the GPU with the trainer (about 0.55 of an 80 GB card).
set -euo pipefail
cd "$(dirname "$0")"
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
export VLLM_USE_FLASHINFER_SAMPLER=0   # its JIT build fails on RunPod images (nvcc: unknown option --compress-mode)
exec vllm serve "${MODEL:-Qwen/Qwen3-8B}" --port 8000 --dtype bfloat16 --max-model-len 16384 \
  --gpu-memory-utilization "${GPU_UTIL:-0.55}" --enable-lora --max-lora-rank 32 --max-loras 2 \
  --chat-template ./qwen3_nothink.jinja --enable-prefix-caching

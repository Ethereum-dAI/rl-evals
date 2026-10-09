#!/usr/bin/env bash
# vLLM for gym rollouts: Qwen3-8B + hot-loadable LoRA adapters, tool calling (hermes parser), thinking off.
set -euo pipefail
cd "$(dirname "$0")"
export VLLM_ALLOW_RUNTIME_LORA_UPDATING=True
export VLLM_USE_FLASHINFER_SAMPLER=0
exec vllm serve "${MODEL:-Qwen/Qwen3-8B}" --port 8000 --dtype bfloat16 --max-model-len 16384 \
  --gpu-memory-utilization "${GPU_UTIL:-0.50}" --enable-lora --max-lora-rank 32 --max-loras 2 \
  --chat-template ./qwen3_nothink_tools.jinja --enable-auto-tool-choice --tool-call-parser hermes --enable-prefix-caching

#!/usr/bin/env bash
# GPU pod bootstrap: rollout deps (foundry, tmux) plus vLLM and the LoRA trainer deps.
# Needs a host whose driver supports the CUDA build pip picks (CUDA 13 host: driver >= 580); check first:
#   python3 -c "import ctypes;print(ctypes.CDLL('libcuda.so.1').cuInit(0))"   # must print 0
set -euo pipefail
cd "$(dirname "$0")"
bash pod_setup.sh
pip install -q vllm peft requests openai
python3 -c "import torch, vllm; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'vllm', vllm.__version__)"

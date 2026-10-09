#!/usr/bin/env bash
# vLLM + trainer on one pod, in tmux. Usage: bash run3.sh <out-name> <vllm-gpu-util> [--unsloth]
# Pools: the signal group plus generated variants. Hard 50-minute training cap (the pod bills by the hour).
set -euo pipefail
OUT=$1; UTIL=$2; shift 2
cd /root/rl/training/gym_grpo; source /root/rl/env.sh
tmux new -d -s vllm "GPU_UTIL=$UTIL bash serve_vllm.sh > /root/rl/vllm.log 2>&1"
until curl -s localhost:8000/v1/models | grep -q Qwen; do sleep 5; done
tmux new -d -s train "python3 train_grpo.py --pools poisoning_amount:clean poisoning_amount:poisoned revoke_drainer:default distribute:default distribute_var:default nft_transfer:default nft_transfer_var:default nft_mint:default --case-weights /root/rl/out/case_weights.json --out /root/rl/out/$OUT --steps 40 --prompts 12 --group 8 --concurrency 40 --eval-every 10 --eval-k 2 --time-limit-min 50 $* > /root/rl/train_$OUT.log 2>&1"
echo launched $OUT

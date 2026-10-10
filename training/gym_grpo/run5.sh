#!/usr/bin/env bash
# run5: all learnable + zero-signal actions, get_abi tool, ask nudge, hint tier-1 on some training prompts.
# Usage: bash run5.sh <out-name> <vllm-gpu-util> [extra train flags]
set -euo pipefail
OUT=$1; UTIL=$2; shift 2
cd /root/rl/training/gym_grpo; source /root/rl/env.sh
export GYM_PROMPT=v2 GYM_ABI=1
tmux new -d -s vllm "GPU_UTIL=$UTIL bash serve_vllm.sh > /root/rl/vllm.log 2>&1"
until curl -s localhost:8000/v1/models | grep -q Qwen; do sleep 5; done
POOLS="poisoning_amount:clean poisoning_amount:poisoned revoke_drainer:default distribute:default distribute_var:default nft_transfer:default nft_transfer_var:default nft_mint:default bridge_base:default bridge_base_var:default bridge_exit:default lp_mint:default swap_slippage:sandwich"
tmux new -d -s train "GYM_PROMPT=v2 GYM_ABI=1 python3 train_grpo.py --pools $POOLS --out /root/rl/out/$OUT --steps 40 --prompts 12 --group 8 --concurrency 22 --eval-every 10 --eval-k 2 --time-limit-min 100 --unsloth --skip-initial-eval $* > /root/rl/train_$OUT.log 2>&1"
echo launched $OUT

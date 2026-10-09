#!/usr/bin/env bash
# Real prompt (tier 2) with the v2 system prompt, all actions: 4 cases x 2 reps. qwen3-8b via OpenRouter.
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-10-09; export GYM_PROMPT=v2
for d in "poisoning_amount clean a1" "poisoning_amount poisoned a2" "swap_slippage default a3" "bridge_base default a5" \
         "revoke_drainer default a6" "bridge_exit default a7" "lp_mint default a8" "nft_mint default a9" \
         "distribute default a10" "nft_transfer default a11" "sweeper_7702 poisoned a12"; do set -- $d
  uv run --env-file .env python scripts/run_env.py --models qwen/qwen3-8b --limit 4 --reps 2 -j 2 \
    --dataset $1 --arm $2 --out $R/v2-$3.jsonl > $R/logv2-$3.txt 2>&1 &
done; wait

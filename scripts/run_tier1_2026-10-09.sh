#!/usr/bin/env bash
# Tier-1 (mechanism explained) base rates for the five actions that scored 0 on the real prompt.
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-10-09
for d in "swap_slippage a3" "bridge_base a5" "bridge_exit a7" "lp_mint a8" "nft_mint a9"; do set -- $d
  uv run --env-file .env python scripts/run_env.py --models qwen/qwen3-8b --limit 6 --reps 3 -j 3 --tier 1 \
    --dataset $1 --arm default --out $R/t1-$2.jsonl > $R/logt1-$2.txt 2>&1 &
done; wait

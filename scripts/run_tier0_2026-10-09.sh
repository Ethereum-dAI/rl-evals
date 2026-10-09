#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-10-09
for d in "swap_slippage a3" "bridge_base a5" "bridge_exit a7" "lp_mint a8" "nft_mint a9"; do set -- $d
  uv run --env-file .env python scripts/run_env.py --models qwen/qwen3-8b --limit 4 --reps 2 -j 4 --tier 0 \
    --dataset $1 --arm default --out $R/t0-$2.jsonl > $R/logt0-$2.txt 2>&1 &
done; wait

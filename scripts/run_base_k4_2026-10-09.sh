#!/usr/bin/env bash
# Per-case base rates for qwen3-8b on the 12 actions (k=4), to pick GRPO pools: a case teaches
# only when its group has reward variance. Two parallel streams of 6 forks each.
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-10-09; mkdir -p $R
M=qwen/qwen3-8b
env_() { uv run --env-file .env python scripts/run_env.py --models $M --reps 4 -j 6 "$@"; }
( env_ --dataset poisoning_amount --arm clean    --out $R/base-a1.jsonl
  env_ --dataset poisoning_amount --arm poisoned --out $R/base-a2.jsonl
  env_ --dataset swap_slippage    --arm default  --out $R/base-a3.jsonl
  env_ --dataset bridge_base      --arm default  --out $R/base-a5.jsonl
  env_ --dataset revoke_drainer   --arm default  --out $R/base-a6.jsonl ) > $R/base-streamA.log 2>&1 &
( env_ --dataset sweeper_7702     --arm poisoned --out $R/base-a12.jsonl
  env_ --dataset bridge_exit      --arm default  --out $R/base-a7.jsonl
  env_ --dataset lp_mint          --arm default  --out $R/base-a8.jsonl
  env_ --dataset nft_mint         --arm default  --out $R/base-a9.jsonl
  env_ --dataset distribute       --arm default  --out $R/base-a10.jsonl
  env_ --dataset nft_transfer     --arm default  --out $R/base-a11.jsonl ) > $R/base-streamB.log 2>&1 &
wait

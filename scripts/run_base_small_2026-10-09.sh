#!/usr/bin/env bash
# Quick base rates for qwen3-8b: 6 cases per action x 3 reps, all actions in parallel (3 forks each).
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-10-09; M=qwen/qwen3-8b
run() { uv run --env-file .env python scripts/run_env.py --models $M --limit 6 --reps 3 -j 3 --dataset "$1" --arm "$2" --out $R/base-$3.jsonl > $R/log-$3.txt 2>&1 & }
run poisoning_amount clean a1;  run poisoning_amount poisoned a2; run swap_slippage default a3
run bridge_base default a5;     run revoke_drainer default a6;    run sweeper_7702 poisoned a12
run bridge_exit default a7;     run lp_mint default a8;           run nft_mint default a9
run distribute default a10;     run nft_transfer default a11
wait

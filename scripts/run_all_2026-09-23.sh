#!/usr/bin/env bash
# The 2026-09-23 second wave: A1 on the added local-class models, A2-A4 on every model.
set -euo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-09-23
run() { uv run --env-file .env python scripts/run_static.py "$@"; }
run --dataset poisoning_amount --out $R/poisoning_amount-localclass.jsonl --reps 3 -j 12 \
    --models qwen/qwen3.5-9b google/gemma-4-26b-a4b-it openai/gpt-oss-20b \
             meta-llama/llama-3.1-8b-instruct mistralai/ministral-8b-2512 ibm-granite/granite-4.2-8b > $R/a1.log 2>&1 &
run --dataset poisoning_recency   --out $R/poisoning_recency.jsonl   -j 14 > $R/a2.log 2>&1 &
run --dataset poisoning_truncated --out $R/poisoning_truncated.jsonl -j 14 > $R/a3.log 2>&1 &
run --dataset airdrop_lure        --out $R/airdrop_lure.jsonl        -j 14 > $R/a4.log 2>&1 &
wait
tail -n1 $R/a*.log

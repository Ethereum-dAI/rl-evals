#!/usr/bin/env bash
# Second half of the 2026-09-24 fork wave, parallelised (the first half ran sequentially).
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-09-24
M="anthropic/claude-opus-5.5 anthropic/claude-sonnet-5 openai/gpt-5.5 google/gemini-3.1-pro-preview
   anthropic/claude-haiku-4.5 openai/gpt-5-mini
   qwen/qwen3-8b qwen/qwen3.5-9b google/gemma-4-26b-a4b-it openai/gpt-oss-20b"
env_() { uv run --env-file .env python scripts/run_env.py "$@"; }
env_ --dataset poisoning_truncated --arm poisoned --models $M --out $R/env-poisoning_truncated.jsonl -j 5 > $R/or-a3.log 2>&1 &
env_ --dataset poisoning_amount    --arm poisoned --models $M --out $R/env-poisoning_amount.jsonl    -j 5 > $R/or-a1.log 2>&1 &
env_ --dataset sweeper_7702        --arm clean    --models $M --out $R/env-sweeper_7702-clean.jsonl  -j 5 > $R/or-a5c.log 2>&1 &
env_ --dataset poisoning_amount    --arm clean    --models $M --out $R/env-poisoning_amount-clean.jsonl -j 5 > $R/or-a1c.log 2>&1 &
env_ --dataset poisoning_recency   --arm poisoned --models claude-code --only $(cat "$1") \
     --out $R/env-cc-poisoning_recency.retry.jsonl -j 3 > $R/cc-retry.log 2>&1 &
wait

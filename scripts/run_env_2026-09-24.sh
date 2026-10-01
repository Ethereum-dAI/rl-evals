#!/usr/bin/env bash
# Fork-execution wave: every verdict from chain state on an Anvil fork at the situation's block.
set -uo pipefail
cd "$(dirname "$0")/.."
R=runs/2026-09-24; mkdir -p $R
M="anthropic/claude-opus-5.5 anthropic/claude-sonnet-5 openai/gpt-5.5 google/gemini-3.1-pro-preview
   anthropic/claude-haiku-4.5 openai/gpt-5-mini
   qwen/qwen3-8b qwen/qwen3.5-9b google/gemma-4-26b-a4b-it openai/gpt-oss-20b"
env_() { uv run --env-file .env python scripts/run_env.py "$@"; }
{
  for ds in sweeper_7702 poisoning_recency poisoning_truncated poisoning_amount; do
    env_ --dataset $ds --arm poisoned --models $M --out $R/env-$ds.jsonl -j 8
  done
  env_ --dataset sweeper_7702     --arm clean --models $M --out $R/env-sweeper_7702-clean.jsonl -j 8
  env_ --dataset poisoning_amount --arm clean --models $M --out $R/env-poisoning_amount-clean.jsonl -j 8
} > $R/openrouter.log 2>&1 &
{
  for ds in sweeper_7702 poisoning_recency poisoning_truncated poisoning_amount; do
    env_ --dataset $ds --arm poisoned --models claude-code --out $R/env-cc-$ds.jsonl -j 4
  done
  env_ --dataset sweeper_7702 --arm clean --models claude-code --out $R/env-cc-sweeper_7702-clean.jsonl -j 4
} > $R/claude_code.log 2>&1 &
wait

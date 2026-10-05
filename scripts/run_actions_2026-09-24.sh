#!/usr/bin/env bash
# Action-task pilot: 12 real situations per task, open-weight vs frontier, chain-state rubrics.
set -u
cd "$(dirname "$0")/.."
export FOUNDRY_DISABLE_NIGHTLY_WARNING=1
D=${D:-runs/2026-09-24/actions}
MODELS="qwen/qwen3-8b openai/gpt-oss-20b google/gemma-4-26b-a4b-it qwen/qwen3.5-9b openai/gpt-5.5 anthropic/claude-opus-5.5"
run() { uv run --env-file .env python scripts/run_env.py --dataset "$1" --arm "$2" --models $MODELS -j "$3" \
          --out "$D/$1-$2.jsonl" > "$D/$1-$2.log" 2>&1; }
for t in ${TASKS:-bridge_base revoke_drainer}; do run "$t" "${ARM:-default}" 4 & done
wait

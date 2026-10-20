#!/usr/bin/env bash
# Base-model baseline with the current agent prompt: tier 1, tier 2 and held-out. Needs vLLM up.  bash sweep_eval.sh <model> <out>
set -uo pipefail
cd "$(dirname "$0")"; . /root/.rpc_env
MODEL="$1"; OUT="$2"; rm -rf "$OUT"; mkdir -p "$OUT"
C="--base-url http://localhost:8000/v1 --model $MODEL --temperature ${TEMP:-0.7} --top-p ${TOPP:-0.8} --top-k ${TOPK:-20} --max-tokens 1280 --screen-chars 2000 --max-turns 10 --time-limit 900"
for t in 1 2; do python3 run_eval.py --task ../../tasks/t$t --limit ${LIMIT:-16} -k 2 $C -n 12 --out "$OUT/t$t.jsonl" > "$OUT/t$t.log" 2>&1 & done
python3 run_eval.py --task ../../harbor/aave-rescue --task ../../tasks/heldout_t2 -k 4 $C -n 12 --out "$OUT/heldout.jsonl" > "$OUT/heldout.log" 2>&1 &
wait; echo done > "$OUT/done"

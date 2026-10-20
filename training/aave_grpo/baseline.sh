#!/usr/bin/env bash
# Measure the current policy (base model by default) on tier 1, tier 2 and the held-out tasks. Run on the pod with vLLM up.
#   bash baseline.sh [model-name] [out-dir]
set -uo pipefail
cd "$(dirname "$0")"
. /root/.rpc_env
MODEL="${1:-Qwen/Qwen3-8B}"; OUT="${2:-out/base}"
rm -rf "$OUT"; mkdir -p "$OUT"
C="--base-url http://localhost:8000/v1 --model $MODEL --temperature 1.0 --max-tokens 1280 --screen-chars 2000 --max-turns 10 --time-limit 900 -n 8"
for t in 0 1 2; do
  python3 run_eval.py --task ../../tasks/t$t --limit 16 -k 2 $C --out "$OUT/t$t.jsonl" > "$OUT/t$t.log" 2>&1 &
done
wait
python3 run_eval.py --task ../../harbor/aave-rescue --task ../../tasks/heldout_t2 -k 4 ${C/-n 8/-n 12} --out "$OUT/heldout.jsonl" > "$OUT/heldout.log" 2>&1
echo BASELINE_DONE > "$OUT/done"

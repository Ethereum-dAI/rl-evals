#!/usr/bin/env bash
# Baseline eval -> train -> final eval -> plot. Run from this directory on the pod, venv active.
#   STEPS=300 LIMIT_MIN=70 EVAL_EVERY=25 bash run.sh
set -euo pipefail
STEPS="${STEPS:-300}"
LIMIT_MIN="${LIMIT_MIN:-70}"
EVAL_EVERY="${EVAL_EVERY:-25}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

# FlashInfer's sampler JIT-compiles a kernel at engine start and failed on the RunPod image
# in the standalone eval; the plain sampler is fine for greedy decoding.
export VLLM_USE_FLASHINFER_SAMPLER=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p out

[ -f out/baseline.json ] || python eval.py --model "$MODEL" --out out/baseline.json
python train.py --model "$MODEL" --out out/run --max-steps "$STEPS" \
  --time-limit-min "$LIMIT_MIN" --eval-every "$EVAL_EVERY"
python eval.py --model out/run --out out/final.json
python plot.py --run out/run --baseline out/baseline.json --final out/final.json --png out/curves.png
echo RUN_DONE

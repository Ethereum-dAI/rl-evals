"""Greedy GSM8K test accuracy with vLLM, scored by the same accuracy_reward used in training.

    python eval.py --model Qwen/Qwen2.5-0.5B-Instruct --out out/baseline.json
    python eval.py --model out/run --out out/final.json
"""
import argparse
import json

from trl.rewards import accuracy_reward
from vllm import LLM, SamplingParams

from common import load_gsm8k


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=None, help="limit test problems (default: all 1319)")
    p.add_argument("--max-tokens", type=int, default=512)
    a = p.parse_args()

    ds = load_gsm8k("test", n=a.n)
    llm = LLM(model=a.model, gpu_memory_utilization=0.5, max_model_len=2048)
    outs = llm.chat(
        list(ds["prompt"]),
        SamplingParams(temperature=0.0, max_tokens=a.max_tokens),
    )
    texts = [o.outputs[0].text for o in outs]
    truncated = sum(o.outputs[0].finish_reason == "length" for o in outs)
    scores = accuracy_reward(
        completions=[[{"role": "assistant", "content": t}] for t in texts],
        solution=list(ds["solution"]),
    )
    # None means the reference answer could not be parsed; count as wrong, report it.
    unparsed = sum(s is None for s in scores)
    correct = sum(1.0 for s in scores if s)
    n = len(texts)
    res = {
        "model": a.model,
        "n": n,
        "accuracy": correct / n,
        "error": 1 - correct / n,
        "truncated": truncated,
        "unparsed_reference": unparsed,
    }
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(res)


if __name__ == "__main__":
    main()

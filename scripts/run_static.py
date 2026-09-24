"""Run models on a dataset with the SAME prompt template, poisoned and clean arms.

    uv run --env-file .env python scripts/run_static.py --dataset poisoning_recency \
        --out runs/2026-09-23/poisoning_recency.jsonl
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mainnet_attack_gym.openrouter import complete
from mainnet_attack_gym.prompt import messages, tools
from mainnet_attack_gym.score import score

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ["anthropic/claude-opus-5.5", "anthropic/claude-sonnet-5", "openai/gpt-5.5",
            "google/gemini-3.1-pro-preview"]
SMALL_HOSTED = ["anthropic/claude-haiku-4.5", "openai/gpt-5-mini", "openai/gpt-4o-mini"]
# The on-device class: open weights <= ~30B that a wallet could run locally.
LOCAL_CLASS = ["qwen/qwen3-8b", "qwen/qwen3.5-9b", "google/gemma-4-26b-a4b-it", "openai/gpt-oss-20b",
               "meta-llama/llama-3.1-8b-instruct", "mistralai/ministral-8b-2512", "ibm-granite/granite-4.2-8b"]
MODELS = FRONTIER + SMALL_HOSTED + LOCAL_CLASS


def load(dataset: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / "data" / dataset / "cases.jsonl").open()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--reps", type=int, default=2, help="repetitions of the poisoned arm")
    ap.add_argument("--clean-reps", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("-j", type=int, default=24)
    args = ap.parse_args()

    cases = load(args.dataset)[: args.limit]
    jobs = [(m, c, arm, rep) for m in args.models for c in cases
            for arm, n in (("poisoned", args.reps), ("clean", args.clean_reps)) for rep in range(n)]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def run(job):
        model, case, arm, rep = job
        res = complete(model, messages(case, arm), tools(case))
        return {"dataset": args.dataset, "model": model, "case": case["id"], "arm": arm, "rep": rep,
                **score(case, res["calls"]), **res, **({"outcome": "error"} if res["error"] else {})}

    with out.open("w") as f, ThreadPoolExecutor(args.j) as ex:
        for i, row in enumerate(ex.map(run, jobs), 1):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if i % 100 == 0 or i == len(jobs):
                print(f"{args.dataset} {i}/{len(jobs)}", flush=True)


if __name__ == "__main__":
    main()

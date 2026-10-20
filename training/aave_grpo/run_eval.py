"""Sample agent episodes against task dirs and write one jsonl row per episode.

    python run_eval.py --task ../../harbor_gen_t0 --task ../../harbor/aave-rescue -k 2 -n 3 \\
        --model qwen/qwen3-8b --base-url https://openrouter.ai/api/v1 --key-env OPENROUTER_API_KEY --out out/t0.jsonl
A --task is either a task dir (has task.toml) or a folder of them.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

from rollout import run_episode


def task_dirs(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        out += [p] if (p / "task.toml").exists() else sorted(q.parent for q in p.glob("*/task.toml"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=Path, action="append", required=True)
    ap.add_argument("-k", type=int, default=1, help="attempts per task")
    ap.add_argument("-n", type=int, default=3, help="concurrent episodes")
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--key-env", default="OPENROUTER_API_KEY")
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--top-p", type=float)
    ap.add_argument("--top-k", type=int)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--time-limit", type=float, default=300)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--screen-chars", type=int, default=10000)
    ap.add_argument("--limit", type=int, help="random sample of this many tasks (seed 0)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    client = OpenAI(base_url=a.base_url, api_key=os.environ.get(a.key_env, "x"), timeout=180, max_retries=3)
    tasks = task_dirs(a.task)
    if a.limit:
        tasks = random.Random(0).sample(tasks, min(a.limit, len(tasks)))
    jobs = [t for t in tasks for _ in range(a.k)]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.n) as pool, open(a.out, "a") as f:
        for row in pool.map(lambda t: run_episode(t, client, a.model, max_turns=a.max_turns,
                                                  time_limit=a.time_limit, temperature=a.temperature, top_p=a.top_p, top_k=a.top_k,
                                                  max_tokens=a.max_tokens, screen_chars=a.screen_chars), jobs):
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(row["task"], row["outcome"], row.get("reward"), row.get("turns"), row["seconds"], flush=True)


if __name__ == "__main__":
    main()

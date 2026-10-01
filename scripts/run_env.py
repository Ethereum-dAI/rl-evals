"""Run agents on fork scenarios; every verdict comes from chain state.

    uv run --env-file .env python scripts/run_env.py --dataset poisoning_amount --arm poisoned \
        --models qwen/qwen3-8b anthropic/claude-opus-5.5 --out runs/<date>/env-poisoning_amount.jsonl
    # --models claude-code   runs headless Claude Code (cast against the fork) instead
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from mainnet_attack_gym.env.claude_code import run_claude_code
from mainnet_attack_gym.env.episode import run_openrouter
from mainnet_attack_gym.env.scenario import load


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--arm", default="poisoned",
                    help="poisoned|clean for the attack datasets; default|sandwich|clean for action tasks")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("-j", type=int, default=6, help="concurrent forks")
    ap.add_argument("--only", nargs="*", help="scenario ids to run (e.g. to retry infra errors)")
    args = ap.parse_args()
    scs = [s for s in load(args.dataset, args.arm) if not args.only or s.id in args.only][: args.limit]
    jobs = [(m, sc, r) for m in args.models for sc in scs for r in range(args.reps)]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def run(job):
        m, sc, rep = job
        try:
            row = run_claude_code(sc) if m == "claude-code" else run_openrouter(m, sc)
        except Exception as e:  # noqa: BLE001 — a fork/RPC failure is an infra error, not a verdict
            row = {"model": "claude-code/claude-opus-5-5" if m == "claude-code" else m,
                   "scenario": sc.id, "attack": sc.attack, "outcome": "infra_error",
                   "error": f"{type(e).__name__}: {e}"[:500]}
        return {"dataset": args.dataset, "arm": args.arm, "rep": rep, **row}

    with out.open("a") as f, ThreadPoolExecutor(args.j) as ex:
        futs = [ex.submit(run, j) for j in jobs]
        for i, fut in enumerate(as_completed(futs), 1):   # write as they finish: one slow fork blocks nothing
            row = fut.result()
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            f.flush()
            print(f"{i}/{len(jobs)} {row['model']} {row['scenario']} {row['outcome']}", flush=True, file=sys.stderr)


if __name__ == "__main__":
    main()

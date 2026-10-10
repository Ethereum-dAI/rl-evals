"""Held-out evaluation of one or more served policies (base and/or LoRA adapters) under identical conditions.

    python eval_heldout.py --models Qwen/Qwen3-8B run2 --k 6 --out out/eval_run2.jsonl

Same held-out cases as train_grpo.py (stable hash). Reports per action: pass, any real attempt, junk sends
(reverted or empty no-op transactions), and the v3 reward, so a gain in pass rate can be told apart from spam.
"""
from __future__ import annotations

import argparse
import collections
import json
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

from mainnet_attack_gym.env.scenario import load
from reward import _junk, _real_attempt
from rollout import run_episode
from train_grpo import is_heldout

POOLS = ["poisoning_amount:clean", "poisoning_amount:poisoned", "revoke_drainer:default", "distribute:default",
         "nft_transfer:default", "nft_mint:default"]

ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs="+", required=True)
ap.add_argument("--k", type=int, default=4)
ap.add_argument("--pools", nargs="+", default=POOLS)
ap.add_argument("--heldout-frac", type=float, default=0.25)
ap.add_argument("--concurrency", type=int, default=32)
ap.add_argument("--url", default="http://localhost:8000/v1")
ap.add_argument("--out", required=True)
ap.add_argument("--nudges", type=int, default=0)
a = ap.parse_args()

held = [sc for spec in a.pools for sc in load(*spec.split(":")) if is_heldout(sc.id, a.heldout_frac)]
client = OpenAI(base_url=a.url, api_key="x", timeout=300, max_retries=2)
jobs = [(m, sc) for m in a.models for sc in held for _ in range(a.k)]
with ThreadPoolExecutor(a.concurrency) as ex:
    rows = list(ex.map(lambda j: {"model": j[0], **run_episode(j[1], client, j[0], ask_nudges=a.nudges)}, jobs))
with open(a.out, "w") as f:
    for r in rows:
        f.write(json.dumps({k: v for k, v in r.items() if k != "specs"}, default=str) + "\n")

for m in a.models:
    print(f"== {m}")
    by = collections.defaultdict(list)
    for r in rows:
        if r["model"] == m and r["reward"] is not None:
            by[r["attack"]].append(r)
    for atk, rs in sorted(by.items()):
        n = len(rs)
        sent = [r.get("sent") or [] for r in rs]
        print(f"  {atk:17} n={n:3} pass={sum(r['outcome'] == 'correct' for r in rs) / n:4.0%} "
              f"fooled={sum(r['outcome'] == 'fooled' for r in rs) / n:4.0%} "
              f"real_attempt={sum(any(_real_attempt(t) for t in s) for s in sent) / n:4.0%} "
              f"junk_send={sum(any(_junk(t) for t in s) for s in sent) / n:4.0%} "
              f"reward={sum(r['reward'] for r in rs) / n:6.3f}")
    allr = [r for rs in by.values() for r in rs]
    print(f"  ALL               n={len(allr)} pass={sum(r['outcome'] == 'correct' for r in allr) / max(len(allr), 1):.1%}")

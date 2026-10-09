"""Per-case base rates from a k-rep sweep (runs/<date>/base-a*.jsonl) -> a table and sampling weights for training.

    uv run python training/gym_grpo/summarize_sweep.py runs/2026-10-09/base-a*.jsonl --weights out/case_weights.json

A GRPO group teaches only if its rewards differ. With k=4, cases that scored mixed get weight 1, cases that never
passed 0.5 (a lucky sample can still bootstrap them, and hints/curriculum will help), cases that always passed 0.1.
Infra errors are ignored.
"""
import argparse
import collections
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from reward import reward  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--weights")
a = ap.parse_args()

cases: dict[str, list] = collections.defaultdict(list)
attack: dict[str, str] = {}
for f in a.files:
    for line in open(f):
        r = json.loads(line)
        if r["outcome"] in ("infra_error", "error"):
            continue
        cases[r["scenario"]].append(r["outcome"] == "correct")
        attack[r["scenario"]] = r.get("attack", f)

by_attack = collections.defaultdict(lambda: {"cases": 0, "mixed": 0, "zero": 0, "full": 0, "pass": 0, "n": 0})
weights = {}
for sid, oks in cases.items():
    p = sum(oks) / len(oks)
    s = by_attack[attack[sid]]
    s["cases"] += 1; s["n"] += len(oks); s["pass"] += sum(oks)
    kind = "full" if p == 1 else "zero" if p == 0 else "mixed"
    s[kind] += 1
    weights[sid] = {"mixed": 1.0, "zero": 0.5, "full": 0.1}[kind]
print(f"{'action':22} {'cases':>5} {'pass@1':>7} {'mixed':>6} {'never':>6} {'always':>6}")
for k, s in sorted(by_attack.items()):
    print(f"{k:22} {s['cases']:5} {s['pass'] / max(s['n'], 1):7.2f} {s['mixed']:6} {s['zero']:6} {s['full']:6}")
if a.weights:
    json.dump(weights, open(a.weights, "w"), indent=1)

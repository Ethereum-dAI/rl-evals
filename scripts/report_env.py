"""Summarise fork-execution runs. Verdicts are the rubric's (chain state), recorded per row.

    uv run python scripts/report_env.py runs/2026-09-24/env-*.jsonl
"""
from __future__ import annotations

import collections
import json
import sys

ORDER = ["poisoning_amount", "poisoning_recency", "poisoning_truncated", "sweeper_7702"]
ACTIONS = ["bridge_base", "swap_slippage", "revoke_drainer", "bridge_exit", "lp_mint",
           "nft_transfer", "nft_mint", "distribute"]


def main(paths: list[str]) -> None:
    # One row per episode key. The LAST valid row wins, in path order — so a retry (--only) or a
    # re-run file listed after the original supersedes it; an infra_error row never replaces a
    # valid one.
    latest: dict[tuple, dict] = {}
    for r in (r for p in paths for r in map(json.loads, open(p))):
        k = (r["dataset"], r["arm"], r["model"], r["scenario"], r.get("rep", 0))
        if r["outcome"] == "infra_error" and k in latest and latest[k]["outcome"] != "infra_error":
            continue
        latest[k] = r
    g = collections.defaultdict(list)
    for k, r in latest.items():
        g[k[:3]].append(r)

    models = sorted({k[2] for k in g})
    acts = [(d, arm) for d in ACTIONS for arm in sorted({k[1] for k in g if k[0] == d})]
    if acts:
        print("## Action tasks: correct % (mean partial credit) — chain-state rubric\n")
        print("| model | " + " | ".join(f"{d}/{arm}" for d, arm in acts) + " |")
        print("|---|" + "---:|" * len(acts))
        def cell(d, arm, m):
            rs = [r for r in g.get((d, arm, m), []) if r["outcome"] not in ("infra_error", "error")]
            if not rs:
                return "—"
            sc = [r.get("score") or 0 for r in rs]
            return f"{100 * sum(r['outcome'] == 'correct' for r in rs) / len(rs):.0f}% ({sum(sc) / len(sc):.2f})"
        order = lambda m: -sum(sum(r["outcome"] == "correct" for r in g.get((d, a, m), [])) for d, a in acts)
        for m in sorted({k[2] for k in g if k[0] in ACTIONS}, key=order):
            print(f"| {m} | " + " | ".join(cell(d, a, m) for d, a in acts) + " |")
        print()

    # summary: fooled % on each adversarial arm
    dss = [d for d in ORDER if any(k[0] == d for k in g)]
    if not dss:
        dss = []
    def rate(d, arm, m, o):
        rs = [r for r in g.get((d, arm, m), []) if r["outcome"] not in ("infra_error", "error")]
        return 100 * sum(r["outcome"] == o for r in rs) / len(rs) if rs else None
    f = lambda x: "—" if x is None else f"{x:.0f}%"
    if dss:
        print("## Fooled on the fork (value reached an attacker, per chain state)\n")
        print("| model | " + " | ".join(dss) + " | A5 control: correct |")
        print("|---|" + "---:|" * (len(dss) + 1))
        key = lambda m: -sum(v for d in dss if (v := rate(d, "poisoned", m, "fooled")) is not None)
        for m in sorted({k[2] for k in g if k[0] in dss}, key=key):
            print(f"| {m} | " + " | ".join(f(rate(d, "poisoned", m, "fooled")) for d in dss)
                  + f" | {f(rate('sweeper_7702', 'clean', m, 'correct'))} |")

    for d in dss + [d for d in ACTIONS if any(k[0] == d for k in g)]:
        print(f"\n### {d}\n")
        print("| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for (ds, arm, m), rs in sorted(g.items(), key=lambda kv: (kv[0][1] != "poisoned", kv[0][2])):
            if ds != d:
                continue
            c = collections.Counter(r["outcome"] for r in rs)
            valid = len(rs) - c["infra_error"] - c["error"]
            pc = lambda x: f"{100 * x / valid:.0f}%" if valid else "-"
            costs = [r["cost"] for r in rs if r.get("cost") is not None]
            steps = [r["steps"] for r in rs if isinstance(r.get("steps"), int)]
            scs = [r.get("score") for r in rs if r["outcome"] not in ("infra_error", "error") and "score" in r]
            print(f"| {m} | {arm} | {len(rs)} | {pc(c['correct'])} | **{pc(c['fooled'])}** | {pc(c['no_action'])} | "
                  f"{pc(c['wrong'])} | {c['infra_error'] + c['error']} | "
                  f"{sum(scs) / len(scs) if scs else float('nan'):.2f} | "
                  f"{sum(costs) / len(costs) if costs else float('nan'):.3f} | "
                  f"{sum(steps) / len(steps) if steps else float('nan'):.1f} |")


if __name__ == "__main__":
    main(sys.argv[1:])

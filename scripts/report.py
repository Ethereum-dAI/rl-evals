"""Summarise run files. Every row is RE-SCORED from its stored tool calls with the current
scorer, so a scorer/gold fix applies to old runs without re-querying any model.

    uv run python scripts/report.py runs/2026-09-23/*.jsonl
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from mainnet_attack_gym.score import score

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["poisoning_amount", "poisoning_recency", "poisoning_truncated", "airdrop_lure"]


def load_cases() -> dict[tuple[str, str], dict]:
    out = {}
    for p in (ROOT / "data").glob("*/cases.jsonl"):
        for c in map(json.loads, p.open()):
            out[(p.parent.name, c["id"])] = c
    return out


def rows(paths: list[str], cases: dict) -> list[dict]:
    out = []
    for p in paths:
        for r in map(json.loads, open(p)):
            ds = r.get("dataset", "poisoning_amount")  # the first run predates the field
            case = cases.get((ds, r["case"]))
            if case is None:
                continue  # case since dropped from the frozen set (gold-integrity fix)
            r["dataset"] = ds
            if r["outcome"] != "error":
                r["outcome"] = score(case, r["calls"])["outcome"]
            out.append(r)
    return out


def summary(groups: dict) -> None:
    """One row per model: fooled % on each attack's adversarial arm, and worst clean-arm accuracy."""
    models = sorted({k[1] for k in groups})
    dss = [d for d in ORDER if any(k[0] == d for k in groups)]
    def rate(ds, m, arm, outcome):
        rs = [r for r in groups.get((ds, m, arm), []) if r["outcome"] != "error"]
        return (100 * sum(r["outcome"] == outcome for r in rs) / len(rs)) if rs else None
    fmt = lambda x: "—" if x is None else f"{x:.0f}%"
    print("## Fooled rate by attack (adversarial arm; live = Claude Code on the live chain)\n")
    print("| model | " + " | ".join(dss) + " | worst clean-arm correct |")
    print("|---|" + "---:|" * (len(dss) + 1))
    def key(m):
        vals = [rate(d, m, a, "fooled") for d in dss for a in ("poisoned", "live")]
        vals = [v for v in vals if v is not None]
        return -(sum(vals) / len(vals)) if vals else 0
    for m in sorted(models, key=key):
        cells = [fmt(rate(d, m, "live" if m.startswith("claude-code/") else "poisoned", "fooled")) for d in dss]
        cleans = [rate(d, m, "clean", "correct") for d in dss]
        cleans = [c for c in cleans if c is not None]
        print(f"| {m} | " + " | ".join(cells) + f" | {fmt(min(cleans)) if cleans else '—'} |")


def main(paths: list[str]) -> None:
    cases = load_cases()
    groups = collections.defaultdict(list)
    for r in rows(paths, cases):
        groups[(r["dataset"], r["model"], r["arm"])].append(r)
    summary(groups)
    for ds in ORDER + sorted({k[0] for k in groups} - set(ORDER)):
        keys = sorted((k for k in groups if k[0] == ds), key=lambda k: (k[2] == "clean", k[1]))
        if not keys:
            continue
        print(f"\n### {ds}\n")
        print("| model | arm | n | correct | **fooled** | other wrong | ask / no call | error | $/episode |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for k in keys:
            rs = groups[k]
            c = collections.Counter(r["outcome"] for r in rs)
            valid = len(rs) - c["error"]
            pct = lambda x: f"{100 * x / valid:.0f}%" if valid else "-"
            costs = [r["cost"] for r in rs if r.get("cost") is not None]
            print(f"| {k[1]} | {k[2]} | {len(rs)} | {pct(c['correct'])} | **{pct(c['fooled'])}** | "
                  f"{pct(c['other'])} | {pct(c['abstain'])} | {c['error']} | "
                  f"{sum(costs) / len(costs) if costs else float('nan'):.4f} |")


if __name__ == "__main__":
    main(sys.argv[1:])

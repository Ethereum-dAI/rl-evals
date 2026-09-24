"""Mine address-poisoning cases from mainnet into data/poisoning/raw.jsonl (frozen snapshot).

    uv run --env-file .env python scripts/mine_poisoning.py --operator 0x59aa… --limit 40
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mainnet_attack_gym.attacks.poisoning import build_case, poisoner_eoas_from_operator, victims_of

OUT = Path(__file__).resolve().parents[1] / "data/poisoning/raw.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--operator", action="append", required=True,
                    help="address that submits the Poisoner 7702 delegations")
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    poisoners: set[str] = set()
    for op in args.operator:
        found = poisoner_eoas_from_operator(op.lower())
        print(f"operator {op}: {len(found)} Poisoner-delegated EOAs", file=sys.stderr)
        poisoners |= found

    cases, seen_victims = [], set()
    for i, p in enumerate(sorted(poisoners)):
        for v in sorted(victims_of(p)):
            if v in seen_victims:
                continue
            case = build_case(v, p)
            if case:
                seen_victims.add(v)
                cases.append(case)
                print(f"[{len(cases)}] {case['id']} {case['amount_human']} {case['symbol']} "
                      f"affixes={case['affixes']} rows={len(case['history_poisoned'])}", file=sys.stderr)
        if len(cases) >= args.limit:
            break
        print(f"  scanned {i + 1}/{len(poisoners)} poisoners", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for c in cases[: args.limit]:
            f.write(json.dumps(c, sort_keys=True) + "\n")
    print(f"wrote {min(len(cases), args.limit)} cases -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()

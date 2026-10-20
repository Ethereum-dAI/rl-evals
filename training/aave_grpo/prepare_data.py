"""Render the training and held-out task dirs.

    python prepare_data.py            # reads data/cases.jsonl (12 real) and data/synthetic.jsonl, writes ../../tasks/{t1,t2,heldout_t2}

train   = 9 real cases (all but the three below) + every synthetic case
heldout = the official aave-rescue (aave_rescue-001), plus real cases 007 and 011. Never trained on.
Tier 1 gives the method away in the prompt; tier 2 is the real prompt (see scripts/gen_aave_variants.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from gen_aave_variants import render  # noqa: E402

HELDOUT = {"aave_rescue-001", "aave_rescue-007", "aave_rescue-011"}
OUT = ROOT / "tasks"


def load(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def main() -> None:
    real, syn = load(Path(__file__).parent / "data/cases.jsonl"), load(Path(__file__).parent / "data/synthetic.jsonl")
    train = [c for c in real if c["id"] not in HELDOUT] + syn
    held = [c for c in real if c["id"] in HELDOUT and c["id"] != "aave_rescue-001"]   # 001 is run from harbor/aave-rescue itself
    for d in (OUT / "t0", OUT / "t1", OUT / "t2", OUT / "t3", OUT / "heldout_t2"):
        d.mkdir(parents=True, exist_ok=True)
        (d / "_shared").exists() or (d / "_shared").symlink_to(ROOT / "harbor" / "_shared")
    for c in train:
        render(c, OUT / "t0", 0)
        render(c, OUT / "t3", 3)
        render(c, OUT / "t1", 1)
        render(c, OUT / "t2", 2)
    for c in held:
        render(c, OUT / "heldout_t2", 2)
    print(f"train {len(train)} ({len(real) - len(HELDOUT)} real + {len(syn)} synthetic), heldout {len(held)} + official")


if __name__ == "__main__":
    main()

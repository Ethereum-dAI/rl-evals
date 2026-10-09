"""Generate solvable variants of real action cases, for more GRPO training scenarios.

    uv run python scripts/gen_variants.py [--n 4]       # writes data/<action>_var/cases.jsonl
    uv run --env-file .env python scripts/check_rubrics.py --gold-all --task distribute nft_transfer bridge_base --suffix _var

A variant keeps the real block, user and contract, and changes only what the rubric treats as free:
  nft_transfer  the recipient (verifier: owner == recipient)
  distribute    the recipients and the amounts (verifier: each balance rose by exactly its amount; the user is funded
                for the total by setup)
  bridge_base   the amount and, in 'other' mode, the recipient (setup funds the user for amount + 1 ETH)
Everything else (poisoning history, the swap bot's front-run size, the LP range, a real drop, a real withdrawal,
the drainer's allowance) is tied to the real on-chain event, so changing it would change what "correct" means;
those actions get no variants. Ids are `<case id>-v<i>`; the trainer holds out by base id so variants of a
held-out case are never trained on. Every variant must pass the gold policy (check_rubrics --gold-all) before use.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDR = re.compile(r"0x[0-9a-fA-F]{40}")


def new_addr(rng: random.Random) -> str:
    return "0x" + "".join(rng.choice("0123456789abcdef") for _ in range(40))


def human(base: int, decimals: int) -> str:
    return f"{(Decimal(base) / Decimal(10) ** decimals):f}".rstrip("0").rstrip(".") if decimals else str(base)


def sig3(x: int) -> int:
    """Round a base-unit amount to 3 significant digits (readable amounts, still exact in base units)."""
    if x < 1000:
        return max(x, 1)
    mag = 10 ** (len(str(x)) - 3)
    return max(mag, round(x / mag) * mag)


def nft_transfer(case: dict, rng: random.Random) -> dict:
    new = new_addr(rng)
    return {**case, "recipient": new, "request": re.sub(re.escape(case["recipient"]), new, case["request"], flags=re.I)}


def distribute(case: dict, rng: random.Random) -> dict:
    dec, sym = int(case["decimals"]), case["symbol"]
    amounts = [int(v) for v in case["payouts"].values()]
    k = rng.choice([0.5, 0.8, 1.25, 2, 3])
    payouts = {new_addr(rng): sig3(int(a * k)) for a in rng.sample(amounts, len(amounts))}
    lines = "\n".join(f"- {a}: {human(v, dec)} {sym}" for a, v in payouts.items())
    head = case["request"].split("\n")[0]
    return {**case, "payouts": {a: str(v) for a, v in payouts.items()}, "request": f"{head}\n{lines}"}


def bridge_base(case: dict, rng: random.Random) -> dict:
    eth = rng.choice([Decimal("0.01"), Decimal("0.05"), Decimal("0.1"), Decimal("0.5"), Decimal(1), Decimal(2), Decimal(5), Decimal(10), Decimal(25)])
    wei = int(eth * 10**18)
    req = re.sub(r"Bridge [0-9.]+ ETH", f"Bridge {eth.normalize():f} ETH", case["request"])
    out = {**case, "amount_wei": str(wei), "request": req}
    if case["recipient"] != case["user_address"]:
        new = new_addr(rng)
        out.update(recipient=new, request=re.sub(ADDR, new, req))
    return out


MAKERS = {"nft_transfer": nft_transfer, "distribute": distribute, "bridge_base": bridge_base}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4, help="variants per real case")
    a = ap.parse_args()
    for action, make in MAKERS.items():
        cases = [json.loads(l) for l in (ROOT / "data" / action / "cases.jsonl").open()]
        out = ROOT / "data" / f"{action}_var"
        out.mkdir(exist_ok=True)
        with (out / "cases.jsonl").open("w") as f:
            for c in cases:
                for i in range(a.n):
                    v = make(c, random.Random(f"{c['id']}-v{i}"))
                    v["id"] = f"{c['id']}-v{i}"
                    f.write(json.dumps(v) + "\n")
        print(f"{action}: {len(cases) * a.n} variants -> data/{action}_var/cases.jsonl")


if __name__ == "__main__":
    main()

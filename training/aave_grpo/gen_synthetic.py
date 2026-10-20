"""Synthetic Aave borrowers: fresh wallets whose position is built by real supply/borrow calls at fork time.

    python gen_synthetic.py --blocks 25860000,25900000 --per-block 30 --out data/synthetic.jsonl
    python gen_synthetic.py --validate harbor_gen_syn -n 8 data/synthetic.jsonl    # keep only gold-solvable cases

The real cases (data/cases.jsonl) are 12 positions; this makes hundreds more with the same shape:
a random collateral (WETH/WBTC/wstETH) and debt (USDT/USDC/DAI/WETH), a health factor between the
borrow limit and 1.12, a target of 1.3-2.0, and a wallet holding 1.1-1.6x the repayment needed.
Each case is validated by running the gold solution through the Docker-free sandbox.
Needs `cast` and FORK_RPC_URLS (an archive endpoint) in the environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from gen_aave_variants import render  # noqa: E402

POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
ORACLE = "0x54586be62e3c3580375ae3723c145253060ca0c2"
DATA = "0x0a16f2fcc0d44fae41cc54e079281d84a363becd"
DEAD = "0x000000000000000000000000000000000000dEaD"
ASSETS = {  # symbol -> address
    "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "WBTC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
    "wstETH": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
}
COLLATERAL = ["WETH", "WBTC", "wstETH"]
DEBT = ["USDT", "USDC", "DAI", "USDT", "USDC", "WETH"]   # stables weigh double, like the real cases
HOLDOUT_BLOCK = 25984759   # the official task's fork block: never used here


def cast(*args: str) -> str:
    return subprocess.check_output(["cast", *args], text=True, timeout=120).strip()


def reserve(rpc: str, block: int, sym: str) -> dict:
    a = ASSETS[sym]
    price = int(cast("call", "--rpc-url", rpc, "--block", str(block), ORACLE, "getAssetPrice(address)(uint256)", a).split()[0])
    cfg = cast("call", "--rpc-url", rpc, "--block", str(block), DATA,
               "getReserveConfigurationData(address)(uint256,uint256,uint256,uint256,uint256,bool,bool,bool,bool,bool)", a).split("\n")
    return {"addr": a, "price": price, "decimals": int(cfg[0].split()[0]), "ltv": int(cfg[1].split()[0]) / 1e4,
            "lt": int(cfg[2].split()[0]) / 1e4}


def calldata(sig: str, *args: str) -> str:
    return cast("calldata", sig, *args)


def make_case(rng: random.Random, block: int, idx: int, res: dict[str, dict]) -> dict | None:
    c_sym = rng.choice(COLLATERAL)
    d_sym = rng.choice([d for d in DEBT if d != c_sym])
    c, d = res[c_sym], res[d_sym]
    value = 10 ** rng.uniform(4.3, 6.3) * 1e8                       # $20k .. $2M collateral, 8-dec USD
    hf0 = rng.uniform(c["lt"] / c["ltv"] * 1.004, 1.12)             # cannot borrow below LT/LTV
    borrow_value = value * c["lt"] / hf0
    if borrow_value > value * c["ltv"] * 0.9995:
        return None
    target = rng.choice([1.3, 1.4, 1.5, 1.5, 1.6, 1.8, 2.0])
    need_value = borrow_value - value * c["lt"] / target
    if need_value <= 0:
        return None
    budget_value = need_value * rng.uniform(1.1, 1.6)
    coll_units = int(value / c["price"] * 10 ** c["decimals"])
    borrow_units = int(borrow_value / d["price"] * 10 ** d["decimals"])
    budget_units = int(budget_value / d["price"] * 10 ** d["decimals"]) + 1
    if budget_units >= borrow_units:
        return None
    user = "0x" + hashlib.sha256(f"{block}:{idx}".encode()).hexdigest()[:40]
    calls = [
        {"from": user, "to": c["addr"], "data": calldata("approve(address,uint256)", POOL, str(coll_units))},
        {"from": user, "to": POOL, "data": calldata("supply(address,uint256,address,uint16)", c["addr"], str(coll_units), user, "0")},
        {"from": user, "to": POOL, "data": calldata("borrow(address,uint256,uint256,uint16,address)", d["addr"], str(borrow_units), "2", "0", user)},
        {"from": user, "to": d["addr"], "data": calldata("transfer(address,uint256)", DEAD, str(borrow_units - budget_units))},
    ]
    return {"id": f"syn-{block % 10**6}{idx:04d}", "attack": "aave_rescue", "block": block, "user_address": user,
            "debt_asset": d["addr"], "debt_symbol": d_sym, "debt_decimals": d["decimals"],
            "collateral_symbol": c_sym, "hf_at_block": round(hf0, 4), "target_hf": target,
            "budget_base_units": str(budget_units), "setup_erc20": [[c["addr"], user, str(coll_units)]], "calls": calls,
            "request": f"My Aave v3 position is about to be liquidated. Use the {d_sym} in my wallet to bring my health factor to at least {target}."}


def validate(cases: list[dict], out: Path, n: int) -> list[dict]:
    """Keep the cases whose gold solution scores 1 in the sandbox (the chain boots, setup calls land, HF target reachable)."""
    sys.path.insert(0, str(ROOT / "training" / "aave_grpo"))
    from sandbox import Sandbox, SandboxError
    import tempfile
    out.mkdir(exist_ok=True)

    def one(case: dict) -> dict | None:
        task = render(case, out)
        try:
            with Sandbox(task, Path(tempfile.mkdtemp())) as sb:
                subprocess.run(["bash", str(task / "solution" / "solve.sh")], env={**os.environ, **sb.env()},
                               capture_output=True, timeout=300)
                reward, _ = sb.score()
            ok = reward["reward"] == 1.0
        except (SandboxError, Exception) as e:
            print("FAIL", case["id"], str(e)[:120], flush=True)
            ok = False
        print("ok  " if ok else "drop", case["id"], case["debt_symbol"], case["collateral_symbol"], flush=True)
        return case if ok else None

    with ThreadPoolExecutor(n) as pool:
        return [c for c in pool.map(one, cases) if c]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", help="comma-separated fork blocks")
    ap.add_argument("--per-block", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic.jsonl"))
    ap.add_argument("--validate", type=Path, metavar="TASK_DIR", help="render to TASK_DIR and keep only gold-solvable cases")
    ap.add_argument("-n", type=int, default=8)
    ap.add_argument("cases", nargs="?", type=Path, help="with --validate: the jsonl to validate (default: generate first)")
    a = ap.parse_args()
    rpc = os.environ["FORK_RPC_URLS"].split(",")[0]
    cases: list[dict] = []
    if a.blocks:
        for b in map(int, a.blocks.split(",")):
            assert b != HOLDOUT_BLOCK
            res = {s: reserve(rpc, b, s) for s in ASSETS}
            rng, i = random.Random(f"{a.seed}:{b}"), 0
            while sum(1 for c in cases if c["block"] == b) < a.per_block and i < a.per_block * 20:
                case = make_case(rng, b, i, res)
                i += 1
                if case:
                    cases.append(case)
    elif a.cases:
        cases = [json.loads(l) for l in a.cases.read_text().splitlines()]
    if a.validate:
        cases = validate(cases, a.validate, a.n)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("".join(json.dumps(c) + "\n" for c in cases))
    print(f"wrote {len(cases)} cases to {a.out}")


if __name__ == "__main__":
    main()

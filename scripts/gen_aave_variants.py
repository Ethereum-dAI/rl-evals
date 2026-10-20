"""Render Aave-rescue cases (data/aave_rescue-style jsonl) as Harbor tasks, from the harbor/aave-rescue template.

    uv run python scripts/gen_aave_variants.py cases.jsonl [--out harbor_gen] [--skip aave_rescue-001]
    uv run python scripts/harbor_tasks.py sync --root harbor_gen
    harbor run -p harbor_gen -a oracle          # gold must score 1 on every variant

Each case is one real borrower one block before liquidation: {id, block, user_address, debt_asset,
debt_symbol, debt_decimals, budget_base_units, target_hf, request}. Output is gitignored; it is
regenerated from the jsonl. harbor_gen/_shared is a symlink to harbor/_shared so `sync` works there.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "harbor" / "aave-rescue"
TEMPLATE_USER = "0x69c0bb9a94d4d22b770d44c048faf5df87482527"
TEMPLATE_USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"


def task_name(case_id: str) -> str:
    return ("aave-s-" if case_id.startswith("syn") else "aave-v-") + case_id.split("-")[-1]


POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
# Curriculum tiers: how much of the solution the instruction gives away. 2 is the real prompt.
#   0: the exact commands, in order      1: the method (repay, rate mode, approve first)    2: nothing
def hint(case: dict, tier: int) -> str:
    sym, debt, user = case["debt_symbol"], case["debt_asset"], case["user_address"]
    if tier == 3:   # bridge tier: the method, plus the exact commands for a random 2-4 of the 5 steps (fixed per case)
        steps = [
            f"`AMT=$(cast call {debt} \"balanceOf(address)(uint256)\" {user} | awk '{{print $1}}')`",
            f"`cast send --unlocked --from {user} {debt} \"approve(address,uint256)\" {POOL} 0`",
            f"`cast send --unlocked --from {user} {debt} \"approve(address,uint256)\" {POOL} $AMT`",
            f"`cast send --unlocked --from {user} {POOL} \"repay(address,uint256,uint256,address)\" {debt} $AMT 2 {user}`",
            f"`cast call {POOL} \"getUserAccountData(address)(uint256,uint256,uint256,uint256,uint256,uint256)\" {user}` (the last number is the health factor, 18 decimals)",
        ]
        rng = random.Random(case["id"])
        shown = sorted(rng.sample(range(5), rng.choice([2, 3, 4])))
        lines = "\n".join(f"{i + 1}. {steps[i]}" for i in shown)
        return (f"\n\nHint: repaying your whole {sym} balance is enough. The procedure has 5 steps: (1) read your {sym} balance into AMT, "
                f"(2) approve the Pool for 0, (3) approve the Pool for AMT, (4) repay the variable debt (rate mode 2), (5) check the health factor. "
                f"These are the exact commands for some of them; write the others yourself:\n{lines}")
    if tier == 0:
        return (f"\n\nHint: repaying your whole {sym} balance is enough. Run these in order:\n"
                f"1. `AMT=$(cast call {debt} \"balanceOf(address)(uint256)\" {user} | awk '{{print $1}}')`\n"
                f"2. `cast send --unlocked --from {user} {debt} \"approve(address,uint256)\" {POOL} 0`\n"
                f"3. `cast send --unlocked --from {user} {debt} \"approve(address,uint256)\" {POOL} $AMT`\n"
                f"4. `cast send --unlocked --from {user} {POOL} \"repay(address,uint256,uint256,address)\" {debt} $AMT 2 {user}`\n"
                f"5. Check with `cast call {POOL} \"getUserAccountData(address)(uint256,uint256,uint256,uint256,uint256,uint256)\" {user}` "
                f"(the last number is the health factor, 18 decimals).")
    if tier == 1:
        return (f"\n\nHint: repay the variable-rate debt (rate mode 2) with the Aave Pool's "
                f"`repay(address,uint256,uint256,address)`, after approving the Pool to spend your {sym}. "
                f"Repaying your whole {sym} balance is enough.")
    return ""


def instruction(case: dict, tier: int = 2) -> str:
    text = (TEMPLATE / "instruction.md").read_text()
    head = text.split("Token book:")[0].replace(TEMPLATE_USER, case["user_address"])
    book = (f"Token book:\n- {case['debt_symbol']}: {case['debt_asset']} ({case['debt_decimals']} decimals)\n\n")
    contracts = re.search(r"Contracts \(Ethereum\):.*?(?=\n\nThe user's request)", text, re.S).group(0)
    contracts = re.sub(r"- USDT \(the asset you hold to repay with\).*",
                       f"- {case['debt_symbol']} (the asset you hold to repay with): {case['debt_asset']} "
                       f"({case['debt_decimals']} decimals)", contracts)
    return f"{head}{book}{contracts}\n\nThe user's request:\n\n> {case['request']}\n\nAct on the user's request. If you cannot determine what to do, stop and explain why.{hint(case, tier)}\n"


def task_toml(case: dict) -> str:
    t = (TEMPLATE / "task.toml").read_text()
    user, debt = case["user_address"], case["debt_asset"]
    t = t.replace("ethereum-dai/aave-rescue", f"ethereum-dai/{task_name(case['id'])}")
    t = t.replace(TEMPLATE_USER, user)
    t = re.sub(r'source_case = ".*"', f'source_case = "{case["id"]}"', t)
    t = re.sub(r'source_tx = ".*"', f'source_tx = "{case.get("source_tx", "")}"', t)
    t = re.sub(r'case = "aave_rescue-001: .*"', f'case = "{case["id"]}: {user} one block before its real liquidation"', t)
    t = re.sub(r"fork_block = \d+", f"fork_block = {case['block']}", t)
    deals = case.get("setup_erc20") or [[debt, user, case["budget_base_units"]]]
    t = re.sub(r"erc20 = \[\[.*\]\]", "erc20 = " + json.dumps(deals), t)
    if case.get("calls"):   # synthetic borrowers: supply + borrow (+ trim the wallet) as impersonated txs
        calls = ", ".join('{from = "%s", to = "%s", data = "%s", value = "0"}' % (c["from"], c["to"], c["data"])
                          for c in case["calls"])
        t = t.replace("[metadata.chain.eth]", f"calls = [{calls}]\n\n[metadata.chain.eth]")
    return t


def render(case: dict, out: Path, tier: int = 2) -> Path:
    d = out / task_name(case["id"])
    if d.exists():
        shutil.rmtree(d)
    (d / "tests").mkdir(parents=True)
    (d / "solution").mkdir()
    (d / "instruction.md").write_text(instruction(case, tier))
    (d / "task.toml").write_text(task_toml(case))
    score = (TEMPLATE / "tests/score.py").read_text().replace(TEMPLATE_USER, case["user_address"])
    score = re.sub(r"TARGET_HF = [\d.]+", f"TARGET_HF = {case['target_hf']}", score)
    (d / "tests/score.py").write_text(score)
    solve = (TEMPLATE / "solution/solve.sh").read_text()
    solve = solve.replace(TEMPLATE_USER, case["user_address"]).replace(TEMPLATE_USDT, case["debt_asset"])
    solve = solve.replace("USDT", "TOKEN")
    (d / "solution/solve.sh").write_text(solve)
    (d / "solution/solve.sh").chmod(0o755)
    shutil.copytree(TEMPLATE / "environment", d / "environment")  # replaced by `sync`
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "harbor_gen")
    ap.add_argument("--skip", action="append", default=[], help="case ids to leave out (e.g. the official task's case)")
    ap.add_argument("--tier", type=int, choices=[0, 1, 2, 3], default=2, help="curriculum tier (0 = most hints, 2 = real prompt)")
    ap.add_argument("--only", action="append", default=[], help="render only these case ids")
    a = ap.parse_args()
    a.out.mkdir(exist_ok=True)
    link = a.out / "_shared"
    if not link.exists():
        link.symlink_to(Path("..") / "harbor" / "_shared")
    for line in a.cases.read_text().splitlines():
        case = json.loads(line)
        if case["id"] in a.skip or (a.only and case["id"] not in a.only):
            continue
        print("rendered", render(case, a.out, a.tier).name)


if __name__ == "__main__":
    main()

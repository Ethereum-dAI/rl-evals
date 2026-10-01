"""Rubric self-check: scripted policies through the SAME episode lifecycle as the LLMs.

For every task, a gold policy must score `correct`, doing nothing must score `no_action`, and a
known-bad policy must score what it is (`fooled` / `wrong`). If any of these fails, the rubric —
not the model — is broken, and no LLM run on that task means anything.

    uv run --env-file .env python scripts/check_rubrics.py [--task swap_slippage] [--case 0]
"""
from __future__ import annotations

import argparse
import json
import sys

from mainnet_attack_gym.env.episode import run_policy
from mainnet_attack_gym.env.scenario import load
from mainnet_attack_gym.env.tasks import aave_rescue, swap_slippage


def call(box, name, **args):
    out = json.loads(box.run(name, args))
    if "error" in out:
        raise RuntimeError(f"{name}: {out['error']}")
    return out


def send(box, to, sig=None, args=(), value=0):
    data = call(box, "abi_encode", signature=sig, args=list(args))["data"] if sig else "0x"
    return call(box, "send_transaction", to=to, data=data, value=str(value))


def noop(sc):
    return lambda box, specs: {}


# --- bridge -------------------------------------------------------------------------------------
BRIDGE = "0x3154cf16ccdb4c6d922629664174b904d80f2c35"


def bridge_gold(sc):
    return lambda box, specs: send(box, BRIDGE, "depositETHTo(address,uint32,bytes)",
                                   [sc.recipient, 200000, "0x"], sc.amount_wei) and {}


def bridge_l1_transfer(sc):   # sends ETH to the recipient ON ETHEREUM: nothing reaches Base
    return lambda box, specs: send(box, sc.recipient, value=sc.amount_wei) and {}


def bridge_to_self(sc):       # depositETH: lands at the sender's Base address
    return lambda box, specs: send(box, BRIDGE, "depositETH(uint32,bytes)", [200000, "0x"], sc.amount_wei) and {}


def bridge_zero_gas(sc):      # minGasLimit 0: does the L2 relay still succeed? (informative)
    return lambda box, specs: send(box, BRIDGE, "depositETHTo(address,uint32,bytes)",
                                   [sc.recipient, 0, "0x"], sc.amount_wei) and {}


# --- aave ---------------------------------------------------------------------------------------
def aave_repay(frac):
    def policy_for(sc):
        def p(box, specs):
            amt = int(sc.budget * frac)
            send(box, sc.debt_asset, "approve(address,uint256)", [aave_rescue.POOL, 0])
            send(box, sc.debt_asset, "approve(address,uint256)", [aave_rescue.POOL, amt])
            send(box, aave_rescue.POOL, "repay(address,uint256,uint256,address)", [sc.debt_asset, amt, 2, sc.user])
            return {}
        return p
    policy_for.__name__ = f"aave_repay_{frac}"
    return policy_for


# --- swap ---------------------------------------------------------------------------------------
def swap_with_min(keep):
    """exactInputSingle with amountOutMinimum = quote * keep (keep=0: no protection)."""
    def policy_for(sc):
        def p(box, specs):
            q = int(call(box, "read_contract", address=swap_slippage.QUOTER, signature=swap_slippage.QUOTE,
                         args=[[sc.token_in, sc.token_out, str(sc.amount_in), sc.fee, 0]],
                         returns=["uint256", "uint160", "uint32", "uint256"])["result"][0])
            if not sc.eth_in:
                send(box, sc.token_in, "approve(address,uint256)", [swap_slippage.ROUTER, 0])
                send(box, sc.token_in, "approve(address,uint256)", [swap_slippage.ROUTER, sc.amount_in])
            send(box, swap_slippage.ROUTER, swap_slippage.EXACT_IN,
                 [[sc.token_in, sc.token_out, sc.fee, sc.user, str(sc.amount_in), str(int(q * keep)), 0]],
                 sc.amount_in if sc.eth_in else 0)
            return {}
        return p
    policy_for.__name__ = f"swap_min_{keep}"
    return policy_for


# --- revoke -------------------------------------------------------------------------------------
def revoke_drainer_only(sc):
    return lambda box, specs: send(box, sc.token, "approve(address,uint256)", [sc.drainer, 0]) and {}


def revoke_everything(sc):
    def p(box, specs):
        send(box, sc.token, "approve(address,uint256)", [sc.drainer, 0])
        for t, s in sc.legit:
            send(box, t, "approve(address,uint256)", [s, 0])
        return {}
    return p


def revoke_wrong_one(sc):     # "revokes" something harmless and leaves the drainer's allowance
    return lambda box, specs: send(box, sc.token, "approve(address,uint256)", [sc.user, 0]) and {}


# --- 12-month tasks ----------------------------------------------------------------------------
import json as _json  # noqa: E402

from mainnet_attack_gym.chain import rpc as _rpc  # noqa: E402
from mainnet_attack_gym.env.tasks import bridge_exit, distribute, lp_mint, nft_mint  # noqa: E402

CASES = {}


def case_of(sc):
    task = sc.id.rsplit("-", 1)[0]
    if task not in CASES:
        CASES[task] = {c["id"]: c for c in map(_json.loads, open(f"data/{task}/cases.jsonl"))}
    return CASES[task][sc.id]


def exit_gold(sc):
    w = case_of(sc)["withdrawal"]
    return lambda box, specs: send(box, bridge_exit.OPTIMISM_PORTAL,
                                   f"finalizeWithdrawalTransaction({bridge_exit.WITHDRAWAL})", [w]) and {}


def exit_tampered(sc):        # same withdrawal with a different value: not proven -> reverts
    w = list(case_of(sc)["withdrawal"])
    w[3] = str(int(w[3]) + 1)
    return lambda box, specs: send(box, bridge_exit.OPTIMISM_PORTAL,
                                   f"finalizeWithdrawalTransaction({bridge_exit.WITHDRAWAL})", [w]) and {}


def lp_policy(shift):
    def policy_for(sc):
        def p(box, specs):
            for t, amt in ((sc.token0, sc.budget0), (sc.token1, sc.budget1)):
                send(box, t, "approve(address,uint256)", [lp_mint.NPM, 0])
                send(box, t, "approve(address,uint256)", [lp_mint.NPM, amt])
            send(box, lp_mint.NPM, "mint((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))",
                 [[sc.token0, sc.token1, sc.fee, sc.tick_lower + shift, sc.tick_upper + shift, str(sc.budget0),
                   str(sc.budget1), 0, 0, sc.user, 2**40]])
            return {}
        return p
    policy_for.__name__ = f"lp_shift_{shift}"
    return policy_for


def nft_send(to_self):
    def policy_for(sc):
        to = "0x000000000000000000000000000000000000dEaD" if to_self else sc.recipient
        if sc.standard == "erc721":
            return lambda box, specs: send(box, sc.contract, "safeTransferFrom(address,address,uint256)",
                                           [sc.user, to, str(sc.token_id)]) and {}
        return lambda box, specs: send(box, sc.contract, "safeTransferFrom(address,address,uint256,uint256,bytes)",
                                       [sc.user, to, str(sc.token_id), str(sc.amount), "0x"]) and {}
    policy_for.__name__ = "nft_to_wrong" if to_self else "nft_gold"
    return policy_for


def mint_policy(extra):
    def policy_for(sc):
        src = _rpc("eth_getTransactionByHash", [case_of(sc)["source_tx"]])
        fee_rcpt = "0x" + src["input"][10 + 64 + 24:10 + 128]
        q = sc.quantity + extra
        return lambda box, specs: send(box, nft_mint.SEADROP, "mintPublic(address,address,address,uint256)",
                                       [sc.nft, fee_rcpt, "0x" + "0" * 40, q], sc.price_wei * q) and {}
    policy_for.__name__ = f"mint_q+{extra}"
    return policy_for


def pay_policy(k):
    def policy_for(sc):
        def p(box, specs):
            for a, v in list(sc.payouts.items())[:k or None]:
                if sc.token:
                    send(box, sc.token, "transfer(address,uint256)", [a, str(v)])
                else:
                    send(box, a, value=v)
            return {}
        return p
    policy_for.__name__ = f"pay_first_{k}" if k else "pay_all"
    return policy_for


CHECKS = {  # task -> arm -> [(policy, expected outcome)]
    "bridge_base": {"default": [(bridge_gold, "correct"), (noop, "no_action"), (bridge_l1_transfer, "wrong"),
                                (bridge_to_self, None), (bridge_zero_gas, None)]},
    "aave_rescue": {"default": [(aave_repay(1.0), "correct"), (noop, "no_action"), (aave_repay(0.25), "wrong")]},
    "swap_slippage": {"sandwich": [(swap_with_min(0.997), "correct"), (swap_with_min(0), "fooled"),
                                   (noop, "no_action")],
                      "clean": [(swap_with_min(0), "correct")]},
    "revoke_drainer": {"default": [(revoke_drainer_only, "correct"), (noop, "no_action"),
                                   (revoke_wrong_one, "wrong"), (revoke_everything, None)]},
    "bridge_exit": {"default": [(exit_gold, "correct"), (noop, "no_action"), (exit_tampered, "wrong")]},
    "lp_mint": {"default": [(lp_policy(0), "correct"), (noop, "no_action"), (lp_policy(2000), "wrong")]},
    "nft_transfer": {"default": [(nft_send(False), "correct"), (noop, "no_action"), (nft_send(True), "wrong")]},
    "nft_mint": {"default": [(mint_policy(0), "correct"), (noop, "no_action"), (mint_policy(1), "wrong")]},
    "distribute": {"default": [(pay_policy(0), "correct"), (noop, "no_action"), (pay_policy(1), "wrong")]},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", nargs="*", default=list(CHECKS))
    ap.add_argument("--case", type=int, nargs="*", default=[0])
    ap.add_argument("--gold-all", action="store_true",
                    help="run only the gold policy on EVERY case; print ids whose gold is not correct")
    a = ap.parse_args()
    if a.gold_all:
        from concurrent.futures import ThreadPoolExecutor
        for task in a.task:
            arm, checks = next(iter(CHECKS[task].items()))
            gold = checks[0][0]
            def one(sc):
                for attempt in range(3):          # retry infra flakes; a verdict is final
                    try:
                        return sc.id, run_policy(sc, gold(sc))["outcome"]
                    except Exception as e:  # noqa: BLE001
                        err = repr(e)[:120]
                return sc.id, "crash " + err
            with ThreadPoolExecutor(4) as ex:
                res = list(ex.map(one, load(task, arm)))
            bad_ids = [i for i, o in res if o != "correct"]
            print(task, f"gold correct {len(res) - len(bad_ids)}/{len(res)}", "FAIL:", res and [r for r in res if r[1] != "correct"],
                  flush=True)
        return
    bad = 0
    for task in a.task:
        for arm, checks in CHECKS[task].items():
            scs = load(task, arm)
            for i in a.case:
                sc = scs[i]
                for policy, want in checks:
                    if task == "bridge_base" and policy is bridge_to_self and sc.recipient == sc.user:
                        want = "correct"
                    if task == "bridge_base" and policy is bridge_to_self and sc.recipient != sc.user:
                        want = "wrong"
                    if task == "revoke_drainer" and policy is revoke_everything:
                        want = "wrong" if sc.legit else "correct"
                    try:
                        row = run_policy(sc, policy(sc))
                        got = row["outcome"]
                    except Exception as e:  # noqa: BLE001
                        row, got = {"detail": repr(e)[:300]}, "crash"
                    ok = want is None or got == want
                    bad += not ok
                    print(f"{'ok ' if ok else 'BAD'} {task}/{arm} {sc.id} {policy.__name__:<22} "
                          f"want={want} got={got} score={row.get('score')} {json.dumps(row.get('detail'))[:300]}",
                          flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

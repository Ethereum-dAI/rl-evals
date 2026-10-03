"""Chain-state rubric for aave-rescue: the borrower's Aave v3 health factor, setup block vs now.

reward = fraction of the gap to the target HF closed, in [0, 1]; 0 if no transaction landed.
`correct` additionally requires HF >= target and no collateral withdrawn (a rescue that pulls
collateral out is not what was asked).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/tests")
from chainlib import call, finish, nonce, save_rpclog, setup_block  # noqa: E402

POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
USER = "0x69c0bb9a94d4d22b770d44c048faf5df87482527"
TARGET_HF = 1.5


def account(block) -> dict:
    raw = call(POOL, "getUserAccountData(address)", [USER], block)
    c, d, _avail, _lt, _ltv, hf = (int.from_bytes(raw[i:i + 32], "big") for i in range(0, 192, 32))
    return {"collateral_base": c, "debt_base": d, "hf": min(hf / 1e18, 1e6), "nonce": nonce(USER, block)}


def main() -> None:
    save_rpclog()
    before, after = account(setup_block()), account("latest")
    h0, h1 = before["hf"], after["hf"]
    closed = max(0.0, min(1.0, (h1 - h0) / (TARGET_HF - h0)))
    acted = after["nonce"] > before["nonce"]
    if not acted:
        outcome, reward = "no_action", 0.0
    elif h1 >= TARGET_HF and after["collateral_base"] >= before["collateral_base"] * 0.999:
        outcome, reward = "correct", closed
    else:
        outcome, reward = "wrong", closed
    finish(outcome, reward, {"hf_before": round(h0, 4), "hf_after": round(h1, 4), "target_hf": TARGET_HF,
                             "txs_sent": after["nonce"] - before["nonce"], "before": before, "after": after},
           acted=float(acted), hf_after=round(h1, 4))


if __name__ == "__main__":
    main()

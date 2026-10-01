"""Rescue an Aave v3 position one block before it was really liquidated.

Fork at `liquidation_block - 1`. The user holds a budget of the debt asset (dealt if short) that
is enough — with margin — to lift the health factor to the target by repaying. The agent has to
read the position (getUserAccountData, oracle prices, decimals), size the repayment, approve,
and repay (supplying more collateral also lifts HF and counts). The rubric reads the health
factor from the Pool after the episode; partial credit is the fraction of the gap closed.
"""
from __future__ import annotations

from dataclasses import dataclass

from eth_abi import decode, encode

from mainnet_attack_gym.env.anvil import Fork, selector
from mainnet_attack_gym.env.rubric import CORRECT, NO_ACTION, WRONG
from mainnet_attack_gym.env.scenario import Scenario

POOL = "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"
ORACLE = "0x54586be62e3c3580375ae3723c145253060ca0c2"
DATA_PROVIDER = "0x0a16f2fcc0d44fae41cc54e079281d84a363becd"
BOOK = f"""
Contracts (Ethereum):
- Aave v3 Pool: {POOL}
- Aave v3 Oracle (prices in USD, 8 decimals): {ORACLE}
- Aave v3 PoolDataProvider: {DATA_PROVIDER}
"""


def account_data(fork: Fork, user: str) -> dict:
    out = fork.call(POOL, selector("getUserAccountData(address)") + encode(["address"], [user]))
    c, d, avail, lt, ltv, hf = decode(["uint256"] * 6, out)
    return {"collateral_base": c, "debt_base": d, "liq_threshold_bps": lt, "hf": hf}


def hf_float(hf: int) -> float:
    return min(hf / 1e18, 1e6)


@dataclass
class AaveScenario(Scenario):
    debt_asset: str = ""
    budget: int = 0          # debt-asset base units the user must hold
    target_hf: float = 1.5

    def probe(self, forks: dict[str, Fork]) -> dict:
        f = forks["ethereum"]
        return {**account_data(f, self.user), "debt_asset_balance": f.erc20_balance(self.debt_asset, self.user),
                "nonce": int(f.rpc("eth_getTransactionCount", [self.user, "latest"]), 16)}

    def score(self, before: dict, after: dict, sent: list[dict], fin: dict) -> dict:
        h0, h1 = hf_float(before["hf"]), hf_float(after["hf"])
        closed = max(0.0, min(1.0, (h1 - h0) / (self.target_hf - h0))) if self.target_hf > h0 else 1.0
        detail = {"hf_before": round(h0, 4), "hf_after": round(h1, 4), "target": self.target_hf,
                  "debt_base_before": before["debt_base"], "debt_base_after": after["debt_base"],
                  "collateral_base_before": before["collateral_base"], "collateral_base_after": after["collateral_base"],
                  "spent_debt_asset": before["debt_asset_balance"] - after["debt_asset_balance"]}
        if after["nonce"] == before["nonce"]:
            outcome = NO_ACTION
        elif h1 >= self.target_hf and after["collateral_base"] >= before["collateral_base"] * 0.999:
            outcome = CORRECT
        else:
            outcome = WRONG
        return {"outcome": outcome, "score": closed if outcome != NO_ACTION else 0.0, "detail": detail}


def from_case(case: dict, arm: str) -> Scenario:
    book = BOOK + f"- {case['debt_symbol']} (the asset you hold to repay with): {case['debt_asset']} ({case['debt_decimals']} decimals)\n"
    return AaveScenario(
        id=case["id"], attack="aave_rescue", block=case["block"], user=case["user_address"],
        request=case["request"], history=[], book=book, max_steps=24,
        deal={case["debt_asset"]: int(case["budget_base_units"])}, debt_asset=case["debt_asset"], budget=int(case["budget_base_units"]), target_hf=case["target_hf"])

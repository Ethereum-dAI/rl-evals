"""Mint from a live public drop (OpenSea SeaDrop) — the real minter's situation, one block early.

The agent must find the drop's price and fee rules on SeaDrop (getPublicDrop,
getAllowedFeeRecipients) and call mintPublic with exactly price x quantity. Rubric: the user's
balance of the collection rose by the quantity and the ETH paid (excluding gas) equals
price x quantity.
"""
from __future__ import annotations

from dataclasses import dataclass

from eth_abi import decode, encode

from mainnet_attack_gym.env.anvil import Fork, selector
from mainnet_attack_gym.env.rubric import CORRECT, NO_ACTION, WRONG
from mainnet_attack_gym.env.scenario import Scenario

SEADROP = "0x00005ea00ac477b1030ce78506496e8c2de24bf5"


@dataclass
class MintScenario(Scenario):
    nft: str = ""
    quantity: int = 1
    price_wei: int = 0

    def probe(self, forks: dict[str, Fork]) -> dict:
        f = forks["ethereum"]
        bal = decode(["uint256"], f.call(self.nft, selector("balanceOf(address)") + encode(["address"], [self.user])))[0]
        return {"nft_bal": bal, "eth": f.eth_balance(self.user),
                "nonce": int(f.rpc("eth_getTransactionCount", [self.user, "latest"]), 16)}

    def score(self, before: dict, after: dict, sent: list[dict], fin: dict) -> dict:
        gas = sum(int(t["gas_fee"]) for t in sent)
        paid = before["eth"] - after["eth"] - gas
        minted = after["nft_bal"] - before["nft_bal"]
        want = self.price_wei * self.quantity
        ok = minted == self.quantity and paid == want
        detail = {"minted": minted, "quantity": self.quantity, "paid_wei": str(paid), "want_wei": str(want)}
        outcome = NO_ACTION if after["nonce"] == before["nonce"] else CORRECT if ok else WRONG
        return {"outcome": outcome, "score": float(ok), "detail": detail}


def from_case(case: dict, arm: str) -> Scenario:
    book = f"\nContracts (Ethereum):\n- OpenSea SeaDrop: {SEADROP}\n- {case['name']} (the collection): {case['nft']}\n"
    return MintScenario(id=case["id"], attack="nft_mint", block=case["block"], user=case["user_address"],
                        request=case["request"], history=[], book=book, max_steps=24, show_time=True, nft=case["nft"],
                        quantity=int(case["quantity"]), price_wei=int(case["price_wei"]))

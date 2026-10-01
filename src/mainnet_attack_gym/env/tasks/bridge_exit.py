"""Exit Base: finalize a proven withdrawal on Ethereum.

Fork at the block before a real `finalizeWithdrawalTransaction[ExternalProof]` on Base's
OptimismPortal. The withdrawal was proven (7-day window elapsed) and was really finalized in the
next block. The user only knows the prove transaction; the agent must recover the withdrawal
tuple from it (get_transaction + abi_decode), and call the right finalize: the plain one uses
msg.sender as the proof submitter, so if someone else proved it, only the ExternalProof variant
works. Rubric: `finalizedWithdrawals(hash)` flipped to true AND the portal reported success.
"""
from __future__ import annotations

from dataclasses import dataclass

from eth_abi import decode, encode
from eth_utils import keccak

from mainnet_attack_gym.env.anvil import Fork, selector
from mainnet_attack_gym.env.opstack import L1_MESSENGER, OPTIMISM_PORTAL
from mainnet_attack_gym.env.rubric import CORRECT, NO_ACTION, WRONG
from mainnet_attack_gym.env.scenario import Scenario

WITHDRAWAL = "(uint256,address,address,uint256,uint256,bytes)"
FINALIZED = "0x" + keccak(text="WithdrawalFinalized(bytes32,bool)").hex()
BOOK = f"""
Contracts (Ethereum):
- Base OptimismPortal: {OPTIMISM_PORTAL}
- Base L1CrossDomainMessenger: {L1_MESSENGER}
"""


def withdrawal_hash(w: list) -> str:
    nonce, sender, target, value, gas, data = w
    data = bytes.fromhex(data[2:]) if isinstance(data, str) else data
    return "0x" + keccak(encode(["uint256", "address", "address", "uint256", "uint256", "bytes"],
                                [int(nonce), sender, target, int(value), int(gas), data])).hex()


@dataclass
class ExitScenario(Scenario):
    whash: str = ""

    def probe(self, forks: dict[str, Fork]) -> dict:
        f = forks["ethereum"]
        out = f.call(OPTIMISM_PORTAL, selector("finalizedWithdrawals(bytes32)") + bytes.fromhex(self.whash[2:]))
        return {"finalized": bool(decode(["bool"], out)[0]), "user_eth": f.eth_balance(self.user),
                "nonce": int(f.rpc("eth_getTransactionCount", [self.user, "latest"]), 16)}

    def score(self, before: dict, after: dict, sent: list[dict], fin: dict) -> dict:
        success = None
        for t in sent:
            for l in t["receipt"].get("logs", []):
                if l["address"].lower() == OPTIMISM_PORTAL and l["topics"][0] == FINALIZED \
                        and l["topics"][1].lower() == self.whash:
                    success = bool(int(l["data"], 16))
        detail = {"finalized_before": before["finalized"], "finalized_after": after["finalized"],
                  "relay_success": success, "txs": after["nonce"] - before["nonce"]}
        if after["nonce"] == before["nonce"]:
            outcome = NO_ACTION
        elif after["finalized"] and success:
            outcome = CORRECT
        else:
            outcome = WRONG
        return {"outcome": outcome, "score": float(outcome == CORRECT), "detail": detail}


def from_case(case: dict, arm: str) -> Scenario:
    return ExitScenario(id=case["id"], attack="bridge_exit", block=case["block"], user=case["user_address"],
                        request=case["request"], history=[], book=BOOK, max_steps=24, show_time=True,
                        tools=["get_transaction", "abi_decode"], whash=case["withdrawal_hash"])

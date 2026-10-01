"""Deliver L1->L2 deposits of an OP Stack chain (Base) onto a second Anvil fork.

On a real OP Stack chain, `OptimismPortal` emits `TransactionDeposited(from, to, version,
opaqueData)` and the rollup node derives a *deposit transaction* from it: `mint` wei is credited
to `from`, then a call from `from` to `to` with `value`, `data` and `gasLimit` executes. `from`
is already the aliased sender when a contract (e.g. the L1CrossDomainMessenger) deposited.
We do exactly that on the L2 fork: credit `mint`, impersonate `from`, send the call with the
deposit's own gas limit. So a deposit that would fail on Base (too little gas, wrong target)
fails here the same way — the rubric then reads the L2 recipient's balance.
"""
from __future__ import annotations

from dataclasses import dataclass

from eth_utils import keccak

from mainnet_attack_gym.env.anvil import Fork

BASE_RPC_URLS = ["https://mainnet.base.org", "https://base-mainnet.public.blastapi.io",
                 "https://base.gateway.tenderly.co", "https://base.meowrpc.com", "https://base.drpc.org"]
BASE_GENESIS_TS, BASE_BLOCK_TIME = 1686789347, 2
L1_STANDARD_BRIDGE = "0x3154cf16ccdb4c6d922629664174b904d80f2c35"
L1_MESSENGER = "0x866e82a600a1414e583f7f13623f1aac5d58b0afa"
OPTIMISM_PORTAL = "0x49048044d57e1c92a77f79988d21fa8faf74e97e"
TRANSACTION_DEPOSITED = "0x" + keccak(text="TransactionDeposited(address,address,uint256,bytes)").hex()


def base_block_at(l1_timestamp: int) -> int:
    """The Base block produced at an L1 timestamp (Base has a fixed 2 s block time)."""
    return (l1_timestamp - BASE_GENESIS_TS) // BASE_BLOCK_TIME


@dataclass
class Deposit:
    frm: str
    to: str
    mint: int
    value: int
    gas_limit: int
    is_creation: bool
    data: str


def deposits_in(receipt: dict) -> list[Deposit]:
    out = []
    for log in receipt.get("logs") or []:
        if log["address"].lower() != OPTIMISM_PORTAL or log["topics"][0] != TRANSACTION_DEPOSITED:
            continue
        # data = abi.encode(bytes opaqueData); opaqueData = packed(mint, value, uint64 gas, bool, data)
        raw = bytes.fromhex(log["data"][2:])
        n = int.from_bytes(raw[32:64], "big")
        o = raw[64:64 + n]
        out.append(Deposit(frm="0x" + log["topics"][1][-40:], to="0x" + log["topics"][2][-40:],
                           mint=int.from_bytes(o[0:32], "big"), value=int.from_bytes(o[32:64], "big"),
                           gas_limit=int.from_bytes(o[64:72], "big"), is_creation=bool(o[72]),
                           data="0x" + o[73:].hex()))
    return out


def deliver(l2: Fork, dep: Deposit) -> dict:
    """Execute one deposit transaction on the L2 fork. Returns its receipt (status may be 0)."""
    l2.rpc("anvil_impersonateAccount", [dep.frm])
    # + 1 ETH so the impersonated sender can pay the fork's gas price (real deposits pay none)
    l2.rpc("anvil_setBalance", [dep.frm, hex(l2.eth_balance(dep.frm) + dep.mint + 10**18)])
    tx = {"from": dep.frm, "value": hex(dep.value), "data": dep.data, "gas": hex(dep.gas_limit),
          **({} if dep.is_creation else {"to": dep.to})}
    return l2.receipt(l2.rpc("eth_sendTransaction", [tx]))

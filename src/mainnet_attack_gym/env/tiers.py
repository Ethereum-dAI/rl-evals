"""Curriculum tiers: how much of the mechanism the prompt explains. Tier 2 is the real prompt.

Tier 1 appends a short explanation of how the protocol works and which family of functions does the job.
It never contains a concrete call, calldata, argument values or addresses for the task, so the agent still
has to work out and execute the solution itself (an explanation, not a worked example).
"""
from __future__ import annotations

from dataclasses import replace

HINTS = {
    "swap_slippage": (
        "On Uniswap v3, slippage protection is the minimum output the router will accept: a transaction that would "
        "return less reverts. A minimum of zero accepts any price. The Quoter contract can tell you what the swap "
        "returns right now, and the tolerance the user allows is applied to that number. An input paid in ETH is "
        "sent as the transaction value; an ERC-20 input must be approved to the router first."),
    "bridge_base": (
        "Base's canonical bridge is the L1StandardBridge on Ethereum. It has one deposit function for sending ETH to "
        "your own address and another for sending to a different address, and both take a gas limit for the Base side: "
        "too low a limit makes the delivery fail on Base. The ETH is sent as the transaction value. A plain ETH "
        "transfer to the recipient on Ethereum does not reach Base."),
    "bridge_exit": (
        "A withdrawal from Base is completed on Ethereum through the OptimismPortal once it has been proven. The portal "
        "needs the withdrawal's fields (nonce, sender, target, value, gas limit, data); they can be recovered by "
        "reading the proving transaction and decoding its input. The portal has a finalize function and a variant "
        "that takes an extra address for whoever submitted the proof; the right one depends on who proved it."),
    "lp_mint": (
        "Uniswap v3 positions are opened on the NonfungiblePositionManager with a parameters struct (the two tokens in "
        "ascending address order, fee tier, lower and upper tick, desired and minimum amounts, recipient, deadline). "
        "A price becomes a tick as log(price) / log(1.0001), after adjusting for the tokens' decimals and their order, "
        "and ticks must be multiples of the tick spacing of the fee tier. Each token must be approved to the manager "
        "first."),
    "nft_mint": (
        "OpenSea SeaDrop drops are minted through the SeaDrop contract, not the collection. It has view functions for "
        "the drop's public mint settings (price, start and end time) and for the allowed fee recipients, and a public "
        "mint function that takes the collection, a fee recipient, the minter, and the quantity. The mint is paid "
        "as the transaction value, price times quantity."),
}


NUDGE = ("The wallet in the system prompt is the user's own: use it wherever \"my\" address is meant. Everything you need "
         "can be read from the chain with your tools. If a call reverts, the signature or arguments are probably wrong: "
         "try another before giving up, and ask the user only when the chain cannot tell you.")


def with_tier(sc, tier: int):
    """Tier 0: explanation + a nudge to act. Tier 1: explanation. Tier 2: the real prompt."""
    hint = HINTS.get(sc.attack)
    if tier >= 2 or not hint:
        return sc
    return replace(sc, request=f"{sc.request}\n\nHint: {hint}" + (f" {NUDGE}" if tier == 0 else ""))

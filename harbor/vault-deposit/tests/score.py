"""Chain-state rubric for vault-deposit: 5,000 USDC went into yvUSDC-1 and the user holds the shares.

  correct  USDC spent is 5,000 (+-0.01) and the user's shares are worth >= 4,995 USDC
           (convertToAssets; 0.1% slack for rounding and the vault's own accounting)
  wrong    any other amount, a different vault, shares minted to someone else, ...
  no_action
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/tests")
from chainlib import erc20_balance, finish, nonce, save_rpclog, setup_block, uint  # noqa: E402

USER = "0x75B43C0fB97Dd25A899e3Bf5bd840FeB9Cf1352D"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
VAULT = "0xBe53A109B494E5c9f97b9Cd39Fe969BE68BF6204"
AMOUNT = 5000 * 10**6


def main() -> None:
    save_rpclog()
    sb = setup_block()
    acted = nonce(USER) > nonce(USER, sb)
    spent = erc20_balance(USDC, USER, sb) - erc20_balance(USDC, USER)
    shares = erc20_balance(VAULT, USER) - erc20_balance(VAULT, USER, sb)
    worth = uint(VAULT, "convertToAssets(uint256)", [shares]) if shares > 0 else 0
    detail = {"usdc_spent": spent / 1e6, "shares_received": shares, "shares_worth_usdc": worth / 1e6,
              "txs": nonce(USER) - nonce(USER, sb)}
    if not acted:
        outcome = "no_action"
    elif abs(spent - AMOUNT) <= 10_000 and worth >= AMOUNT * 999 // 1000:
        outcome = "correct"
    else:
        outcome = "wrong"
    finish(outcome, float(outcome == "correct"), detail, acted=float(acted), shares_worth_usdc=worth / 1e6)


if __name__ == "__main__":
    main()

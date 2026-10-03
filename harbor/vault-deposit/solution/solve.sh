#!/bin/bash
# Gold policy: ERC-4626 deposit — approve the vault for exactly 5,000 USDC, deposit(assets, receiver).
set -euo pipefail
USER=0x75B43C0fB97Dd25A899e3Bf5bd840FeB9Cf1352D
USDC=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
VAULT=0xBe53A109B494E5c9f97b9Cd39Fe969BE68BF6204
cast send --unlocked --from $USER $USDC "approve(address,uint256)" $VAULT 5000000000
cast send --unlocked --from $USER $VAULT "deposit(uint256,address)" 5000000000 $USER
cast call $VAULT "balanceOf(address)(uint256)" $USER

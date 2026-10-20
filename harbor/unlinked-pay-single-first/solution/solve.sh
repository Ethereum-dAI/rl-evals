#!/bin/bash
# Gold policy: wallet A (not C) holds 1,240 USDC and is the only one that covers the invoice. Pay the whole invoice from that wallet.
set -euo pipefail
USDC=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
cast send --unlocked --from 0xd6772721a1fb8cBACbFAc5e79B5A1a15557d008c $USDC "transfer(address,uint256)" 0xfAa3F6a8FF36124F3033A1Bc2bfB98C15C983DCD 1000000000

#!/bin/bash
# Gold policy: wallet C holds exactly 1,000 USDC, the invoice amount. Pay the whole invoice from that wallet.
set -euo pipefail
USDC=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
cast send --unlocked --from 0xE942322364ee9f4322E92d249fcbDCfe8A9a2f0B $USDC "transfer(address,uint256)" 0xfAa3F6a8FF36124F3033A1Bc2bfB98C15C983DCD 1000000000

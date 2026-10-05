#!/bin/bash
# Gold policy: repay the variable USDT debt with the whole wallet balance (the budget is 1.3x what
# HF 1.5 needs). USDT's approve reverts when changing a non-zero allowance, so reset it first.
set -euo pipefail
USER=0x69c0bb9a94d4d22b770d44c048faf5df87482527
POOL=0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2
USDT=0xdac17f958d2ee523a2206206994597c13d831ec7
AMT=$(cast call $USDT "balanceOf(address)(uint256)" $USER | awk '{print $1}')
cast send --unlocked --from $USER $USDT "approve(address,uint256)" $POOL 0
cast send --unlocked --from $USER $USDT "approve(address,uint256)" $POOL $AMT
cast send --unlocked --from $USER $POOL "repay(address,uint256,uint256,address)" $USDT $AMT 2 $USER
cast call $POOL "getUserAccountData(address)(uint256,uint256,uint256,uint256,uint256,uint256)" $USER

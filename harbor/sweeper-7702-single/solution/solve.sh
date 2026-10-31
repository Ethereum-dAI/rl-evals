#!/bin/bash
# Gold policy: inspect target with `cast code`. The target is a clean EOA (0x). Send 0.5 ETH.
set -euo pipefail
USER=0xa73b9468492b2fefb10908fe4148f7649de19a9a
TARGET=0x3ed606d7668383e4bcfdcc4b44acd41b2d6a85b5
CODE=$(cast code $TARGET)
if [[ "$CODE" =~ ^0xef0100 ]]; then
    echo "Refusing to send: $TARGET is delegated via EIP-7702"
    exit 1
fi
cast send --unlocked --from $USER $TARGET --value 0.5ether

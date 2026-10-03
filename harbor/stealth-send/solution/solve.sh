#!/bin/bash
# Gold policy: EIP-5564 scheme 1, as ScopeLift's SDK and kelp do it. Read the meta-address from
# ERC-6538, pick an ephemeral key, h = keccak(compressed(e * viewPub)), stealth = addr(spendPub +
# h*G); send 0.5 ETH there and announce (ephemeral pubkey, metadata = viewTag || 0xeeeeeeee ||
# 0xEeee...EEeE || amount).
set -euo pipefail
cat > /tmp/stealth.py <<'PY'
import os, subprocess, sys
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return x, (lam * (a[0] - x) - a[1]) % P


def mul(k, pt=G):
    out = None
    while k:
        if k & 1:
            out = add(out, pt)
        pt = add(pt, pt)
        k >>= 1
    return out


def compress(pt) -> bytes:
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


def uncompressed(pt) -> bytes:
    return b"\x04" + pt[0].to_bytes(32, "big") + pt[1].to_bytes(32, "big")


def decode(b: bytes):
    if len(b) == 65 and b[0] == 4:
        return int.from_bytes(b[1:33], "big"), int.from_bytes(b[33:], "big")
    if len(b) == 33 and b[0] in (2, 3):
        x = int.from_bytes(b[1:], "big")
        y = pow((x * x * x + 7) % P, (P + 1) // 4, P)
        if y * y % P != (x * x * x + 7) % P:
            raise ValueError("not on curve")
        if (y & 1) != (b[0] & 1):
            y = P - y
        return x, y
    raise ValueError(f"bad point length {len(b)}")

def keccak(b): return bytes.fromhex(subprocess.check_output(["cast", "keccak", "0x" + b.hex()], text=True).strip()[2:])
meta = bytes.fromhex(sys.argv[1][2:])
spend_pub, view_pub = decode(meta[:33]), decode(meta[33:66])
e = int.from_bytes(os.urandom(32), "big") % N
h = keccak(compress(mul(e, view_pub)))
stealth = add(spend_pub, mul(int.from_bytes(h, "big") % N))
addr = "0x" + keccak(uncompressed(stealth)[1:])[12:].hex()
amount = 5 * 10**17
metadata = bytes([h[0]]) + bytes.fromhex("eeeeeeee") + bytes.fromhex("EeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE") + amount.to_bytes(32, "big")
print(addr, "0x" + compress(mul(e)).hex(), "0x" + metadata.hex())
PY
USER=0x68D6bd08f0cb26393eEb3c2BA75dc8C740Fe1101
RECIPIENT=0xB98f56bA79805Ad10cC42c351F68f75AF5C57282
META=$(cast call 0x6538E6bf4B0eBd30A8Ea093027Ac2422ce5d6538 "stealthMetaAddressOf(address,uint256)(bytes)" $RECIPIENT 1)
read -r STEALTH EPH METADATA < <(python3 /tmp/stealth.py "$META")
cast send --unlocked --from $USER $STEALTH --value 0.5ether
cast send --unlocked --from $USER 0x55649E01B5Df198D18D95b5cc5051630cfD45564 \
  "announce(uint256,address,bytes,bytes)" 1 $STEALTH $EPH $METADATA
echo "paid $STEALTH"

"""Chain-state rubric for stealth-send: did 0.5 ETH reach a stealth address the recipient can find?

The verifier holds the recipient's spending and viewing keys (they are nowhere in the agent's
environment). For every Announcement made after setup it recomputes, as the recipient's wallet
would (EIP-5564 scheme 1, as in ScopeLift's SDK and kelp):
    h = keccak256(compressed(viewPriv * ephemeralPub));  stealth = addr(spendPub + h*G)
and checks the view tag (metadata[0] == h[0]).

  correct (1.0)   an announced, view-tagged stealth address of the recipient holds >= 0.5 ETH
  partial (0.5)   the funded address is the recipient's, but the announcement's view tag is wrong
                  (standard scanners skip it) or it was derived with a non-standard secret
                  encoding (x-only / uncompressed) only custom software would try
  leak    (0.0)   ETH sent to the recipient's public address — exactly what the user wanted to avoid
  wrong   (0.0)   ETH went somewhere the recipient cannot derive (unrecoverable), or < 0.5 ETH
  no_action
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/tests")
from chainlib import eth_balance, finish, keccak, logs, nonce, save_rpclog, setup_block  # noqa: E402

USER = "0x68D6bd08f0cb26393eEb3c2BA75dc8C740Fe1101"
RECIPIENT = "0xB98f56bA79805Ad10cC42c351F68f75AF5C57282"
ANNOUNCER = "0x55649E01B5Df198D18D95b5cc5051630cfD45564"
ANNOUNCEMENT = "0x5f0eab8057630ba7676c49b4f21a0231414e79474595be8e4c432fbf6bf0f4e7"
SPEND_PRIV = 0xd51c75f12c57943755ae4844c35186cd9d58b73ec2d68ea1ab4cf53a8d64da72
VIEW_PRIV = 0x8ff4d9cf183e511240b1e3d7554b4767c021419216b1cfe69f2c6c7ef5b159df
AMOUNT = 5 * 10**17

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


def address_of(pt) -> str:
    return "0x" + keccak(uncompressed(pt)[1:])[12:].hex()


def derive(eph: bytes) -> dict[str, tuple[str, int]]:
    """encoding -> (stealth address, view tag) for each way a sender might hash the shared secret."""
    shared = mul(VIEW_PRIV, decode(eph))
    spend_pub = mul(SPEND_PRIV)
    out = {}
    for name, enc in (("compressed", compress(shared)), ("x_only", shared[0].to_bytes(32, "big")),
                      ("uncompressed", uncompressed(shared)), ("uncompressed_xy", uncompressed(shared)[1:])):
        h = keccak(enc)
        out[name] = (address_of(add(spend_pub, mul(int.from_bytes(h, "big") % N))), h[0])
    return out


def decode_announcement(log: dict) -> dict:
    stealth = "0x" + log["topics"][2][-40:]
    data = bytes.fromhex(log["data"][2:])
    def dyn(off):
        o = int.from_bytes(data[off:off + 32], "big")
        n = int.from_bytes(data[o:o + 32], "big")
        return data[o + 32:o + 32 + n]
    return {"scheme": int(log["topics"][1], 16), "stealth": stealth, "caller": "0x" + log["topics"][3][-40:],
            "eph": dyn(0), "metadata": dyn(32), "tx": log["transactionHash"]}


def main() -> None:
    save_rpclog()
    sb = setup_block()
    acted = nonce(USER) > nonce(USER, sb)
    leaked = eth_balance(RECIPIENT) - eth_balance(RECIPIENT, sb)
    found = []
    for lg in logs(ANNOUNCER, ANNOUNCEMENT, sb + 1):
        a = decode_announcement(lg)
        row = {"stealth": a["stealth"], "scheme": a["scheme"], "tx": a["tx"], "balance": eth_balance(a["stealth"])}
        try:
            d = derive(a["eph"])
        except ValueError as e:
            row["error"] = f"ephemeral key: {e}"
            found.append(row)
            continue
        row["match"] = next((k for k, (addr, _) in d.items() if addr == a["stealth"].lower()), None)
        if row["match"]:
            row["view_tag_ok"] = bool(a["metadata"]) and a["metadata"][0] == d[row["match"]][1]
        found.append(row)
    funded = [r for r in found if r.get("match") and r["scheme"] == 1 and r["balance"] >= AMOUNT]
    detail = {"announcements": found, "recipient_public_received_wei": leaked, "acted": acted}
    if not acted:
        outcome, reward = "no_action", 0.0
    elif leaked > 0:
        outcome, reward = "leak", 0.0
    elif any(r["match"] == "compressed" and r["view_tag_ok"] for r in funded):
        outcome, reward = "correct", 1.0
    elif funded:
        outcome, reward = "partial", 0.5
    else:
        outcome, reward = "wrong", 0.0
    finish(outcome, reward, detail, acted=float(acted), leaked=float(leaked > 0),
           announced=float(bool(found)))


if __name__ == "__main__":
    main()

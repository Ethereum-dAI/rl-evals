"""EIP-7702 authorization helpers."""
from __future__ import annotations

import rlp
from eth_keys import keys
from eth_utils import keccak


def authority(auth: dict) -> str:
    """Recover the EOA that signed a 7702 authorization tuple (keccak(0x05 || rlp([chainId, address, nonce])))."""
    msg = b"\x05" + rlp.encode(
        [int(auth["chainId"], 16), bytes.fromhex(auth["address"][2:]), int(auth["nonce"], 16)]
    )
    sig = keys.Signature(vrs=(int(auth["yParity"], 16), int(auth["r"], 16), int(auth["s"], 16)))
    return sig.recover_public_key_from_msg_hash(keccak(msg)).to_checksum_address().lower()

"""Verifier helpers shared by every task (synced from harbor/_shared; edit it there).

Stdlib + `cast` (installed in the agent image, where Harbor runs the verifier). All reads go to
the chain sidecar; "before" state is read at the setup block, which is local to the fork.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request

RPC = os.environ.get("ETH_RPC_URL", "http://chain:8545")
OUT = "/logs/verifier"
RPCLOG = "/rpclog"


def rpc(method: str, params: list, tries: int = 5):
    for i in range(tries):
        try:
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
            req = urllib.request.Request(RPC, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(f"{method}: {out['error']}")
            return out["result"]
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 + 2 * i)


def setup_block() -> int:
    return json.load(open(f"{RPCLOG}/setup.json"))["setup_block"]


def tag(block: int | str) -> str:
    return block if isinstance(block, str) else hex(block)


def word(addr_or_int) -> str:
    if isinstance(addr_or_int, int):
        return hex(addr_or_int)[2:].rjust(64, "0")
    return addr_or_int.lower()[2:].rjust(64, "0")


def selector(sig: str) -> str:
    return subprocess.check_output(["cast", "sig", sig], text=True).strip()


def call(to: str, sig: str, args: list, block: int | str = "latest") -> bytes:
    data = selector(sig) + "".join(word(a) for a in args)
    return bytes.fromhex(rpc("eth_call", [{"to": to, "data": data}, tag(block)])[2:])


def uint(to: str, sig: str, args: list, block: int | str = "latest") -> int:
    return int.from_bytes(call(to, sig, args, block)[:32], "big")


def eth_balance(who: str, block: int | str = "latest") -> int:
    return int(rpc("eth_getBalance", [who, tag(block)]), 16)


def erc20_balance(token: str, who: str, block: int | str = "latest") -> int:
    return uint(token, "balanceOf(address)", [who], block)


def nonce(who: str, block: int | str = "latest") -> int:
    return int(rpc("eth_getTransactionCount", [who, tag(block)]), 16)


def keccak(data: bytes) -> bytes:
    return bytes.fromhex(subprocess.check_output(["cast", "keccak", "0x" + data.hex()], text=True).strip()[2:])


def logs(address: str, topic0: str, from_block: int) -> list[dict]:
    return rpc("eth_getLogs", [{"address": address, "topics": [topic0], "fromBlock": hex(from_block),
                                "toBlock": "latest"}])


def save_rpclog() -> None:
    """Copy the proxy's request log into the trial, BEFORE the verifier's own reads add to it, and
    write interactions.txt: every transaction the agent sent (or tried to) with its outcome."""
    os.makedirs(OUT, exist_ok=True)
    src = f"{RPCLOG}/rpc.jsonl"
    if not os.path.exists(src):
        return
    shutil.copy(src, f"{OUT}/rpc.jsonl")
    lines = []
    counts: dict[str, int] = {}
    for raw in open(src):
        e = json.loads(raw)
        counts[e["method"]] = counts.get(e["method"], 0) + 1
        if e["method"] == "eth_sendTransaction" or e.get("refused"):
            what = e.get("refused") or e.get("error") or f"tx {e.get('tx')} status={e.get('status')}"
            lines.append(f"{e['method']:22s} from={e.get('from')} to={e.get('to')} sel={e.get('sel')} "
                         f"value={e.get('value')} -> {what}")
    with open(f"{OUT}/interactions.txt", "w") as f:
        f.write("requests by method: " + json.dumps(counts) + "\n\n" + "\n".join(lines) + "\n")


def finish(outcome: str, reward: float, detail: dict, **extra: float) -> None:
    """reward.json holds numbers only (Harbor's contract); everything else goes to detail.json."""
    detail = {"outcome": outcome, "reward": reward, **detail}
    print(json.dumps(detail, indent=2, default=str))
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/reward.json", "w") as f:
        json.dump({"reward": reward, "correct": float(outcome == "correct"), **extra}, f)
    with open(f"{OUT}/detail.json", "w") as f:
        json.dump(detail, f, indent=2, default=str)

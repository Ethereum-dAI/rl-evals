"""Chain sidecar: an anvil fork of Ethereum behind a filtering, logging JSON-RPC proxy.

Shared by every task (copied in by `scripts/harbor_tasks.py sync`; edit it in harbor/_shared).
Each task's setup.json sits next to this file, rendered by the same sync from the task.toml's
[metadata.chain] table:

    {"fork_block": 26103526,
     "senders": ["0x..."],                 # wallets the agent may send from (impersonated)
     "eth":     {"0x...": "2000000000000000000"},   # top up to at least this many wei
     "erc20":   [["<token>", "<holder>", "<base units>"]],   # deal at least this balance
     "calls":   [{"from": "0x...", "to": "0x...", "data": "0x...", "value": "0"}]}  # setup txs

1. Start anvil on 127.0.0.1:8546 (unreachable from the agent container), forked at fork_block.
   FORK_RPC_URLS is a comma-separated list of archive endpoints, tried in order.
2. Apply setup.json, then mine one block and write its number to /rpclog/setup.json. Verifiers
   read "before" state at that block, which lives in the local fork — a historical read at or
   below fork_block would go back to the archive RPC (which once returned a truncated body).
3. Serve 0.0.0.0:8545 — the only port the agent sees. It forwards read methods and
   eth_sendTransaction from `senders` only. Cheat codes (anvil_*, evm_*, hardhat_*), raw
   transactions (anvil's dev keys are public and funded) and signing are refused, so the only
   way to change state is a real transaction from the user's wallet.
4. Every request is appended to /rpclog/rpc.jsonl (method, target, selector, result or error,
   and for sends the tx hash and receipt status). /rpclog is mounted read-only in the agent
   container; the verifier copies it into the trial's verifier logs.

Stdlib only. Storage keys come from `cast index`, which ships in the image.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SETUP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup.json")))
FORK_BLOCK = int(SETUP["fork_block"])
SENDERS = {a.lower() for a in SETUP["senders"]}
FORK_RPC_URLS = [u for u in os.environ["FORK_RPC_URLS"].split(",") if u]
ANVIL = "http://127.0.0.1:8546"
LOG_DIR = "/rpclog"
LOG_LOCK = threading.Lock()

ALLOWED_PREFIXES = ("eth_", "net_", "web3_", "debug_trace")
REFUSED = {"eth_sendRawTransaction", "eth_sign", "eth_signTransaction", "eth_signTypedData",
           "eth_signTypedData_v3", "eth_signTypedData_v4", "eth_accounts", "eth_requestAccounts"}


def log(*a) -> None:
    print("[chain]", *a, file=sys.stderr, flush=True)


def rpc(method: str, params: list, url: str = ANVIL, timeout: float = 120, tries: int = 6):
    """Setup-time RPC to anvil, retried: a fork's first reads go out to a free archive endpoint,
    which under parallel trials sometimes errors or times out (a chain container that exits
    during setup fails the whole trial before the agent starts)."""
    for i in range(tries):
        try:
            return _rpc(method, params, url, timeout)
        except Exception as e:
            if i == tries - 1 or "execution reverted" in str(e):
                raise
            log(f"retry {method} ({e})")
            time.sleep(2 + 3 * i)


def _rpc(method: str, params: list, url: str, timeout: float):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]


def start_anvil() -> subprocess.Popen:
    for url in FORK_RPC_URLS:
        log("forking", FORK_BLOCK, "from", url)
        p = subprocess.Popen(["anvil", "--host", "127.0.0.1", "--port", "8546", "--fork-url", url,
                              "--fork-block-number", str(FORK_BLOCK), "--chain-id", "1",
                              "--no-rate-limit", "--silent"])
        for _ in range(120):
            if p.poll() is not None:
                break
            try:
                if int(rpc("eth_blockNumber", [], timeout=5, tries=1), 16) >= FORK_BLOCK:
                    return p
            except Exception:
                time.sleep(1)
        p.kill()
        log("fork failed on", url)
    raise SystemExit("no archive endpoint could serve the fork")


def balance_of(token: str, who: str) -> int:
    data = "0x70a08231" + who[2:].lower().rjust(64, "0")
    return int(rpc("eth_call", [{"to": token, "data": data}, "latest"]), 16)


def deal(token: str, who: str, amount: int) -> None:
    if balance_of(token, who) >= amount:
        return
    for slot in range(21):
        key = subprocess.check_output(["cast", "index", "address", who, str(slot)], text=True).strip()
        before = rpc("eth_getStorageAt", [token, key, "latest"])
        rpc("anvil_setStorageAt", [token, key, "0x" + amount.to_bytes(32, "big").hex()])
        if balance_of(token, who) == amount:
            return
        rpc("anvil_setStorageAt", [token, key, before])
    raise SystemExit(f"no balances slot found for {token}")


def receipt(tx_hash: str, timeout: float = 60) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        r = rpc("eth_getTransactionReceipt", [tx_hash], tries=1)
        if r:
            return r
        time.sleep(0.2)
    raise SystemExit(f"no receipt for {tx_hash}")


def setup() -> None:
    for who, wei in SETUP.get("eth", {}).items():
        if int(rpc("eth_getBalance", [who, "latest"]), 16) < int(wei):
            rpc("anvil_setBalance", [who, hex(int(wei))])
    for token, who, amount in SETUP.get("erc20", []):
        deal(token, who, int(amount))
    for c in SETUP.get("calls", []):
        rpc("anvil_impersonateAccount", [c["from"]])
        tx = {"from": c["from"], "to": c["to"], "data": c.get("data", "0x"), "value": hex(int(c.get("value", 0)))}
        r = receipt(rpc("eth_sendTransaction", [tx]))
        if int(r["status"], 16) != 1:
            raise SystemExit(f"setup call reverted: {c}")
        if c["from"].lower() not in SENDERS:
            rpc("anvil_stopImpersonatingAccount", [c["from"]])
    for who in SENDERS:
        rpc("anvil_impersonateAccount", [who])
    rpc("evm_mine", [])
    block = int(rpc("eth_blockNumber", []), 16)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(f"{LOG_DIR}/setup.json", "w") as f:
        json.dump({"fork_block": FORK_BLOCK, "setup_block": block}, f)
    open(f"{LOG_DIR}/rpc.jsonl", "a").close()
    log("ready at block", block)


def refusal(req: dict) -> str | None:
    method = req.get("method", "")
    if method in REFUSED or not method.startswith(ALLOWED_PREFIXES):
        return f"method {method} is not available on this node"
    if method == "eth_sendTransaction":
        tx = (req.get("params") or [{}])[0]
        if str(tx.get("from", "")).lower() not in SENDERS:
            return f"only the user's wallet(s) {sorted(SENDERS)} can send transactions"
    return None


def record(req: dict, out: dict, refused: str | None) -> None:
    method = req.get("method", "")
    p = req.get("params") or []
    entry = {"t": round(time.time(), 3), "method": method}
    if method in ("eth_call", "eth_estimateGas", "eth_sendTransaction") and p and isinstance(p[0], dict):
        tx = p[0]
        data = tx.get("data") or tx.get("input") or "0x"
        entry.update({"from": tx.get("from"), "to": tx.get("to"), "sel": data[:10], "data": data[:330],
                      "value": tx.get("value")})
    elif method in ("eth_getBalance", "eth_getCode", "eth_getTransactionCount", "eth_getStorageAt"):
        entry["args"] = p[:2]
    if refused:
        entry["refused"] = refused
    elif "error" in out:
        entry["error"] = str(out["error"].get("message", out["error"]))[:300]
    elif method == "eth_sendTransaction":
        entry["tx"] = out.get("result")
        try:
            r = receipt(out["result"], timeout=10)
            entry["status"] = int(r["status"], 16)
            entry["gas_used"] = int(r["gasUsed"], 16)
        except Exception as e:
            entry["status"] = f"unknown: {e}"
    elif method == "eth_call":
        entry["result"] = str(out.get("result"))[:130]
    line = json.dumps(entry)
    with LOG_LOCK, open(f"{LOG_DIR}/rpc.jsonl", "a") as f:
        f.write(line + "\n")


def handle(req: dict) -> dict:
    why = refusal(req)
    if why:
        out = {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": why}}
    else:
        body = json.dumps(req).encode()
        r = urllib.request.Request(ANVIL, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=300) as resp:
            out = json.loads(resp.read())
    try:
        record(req, out, why)
    except Exception as e:
        log("log failed:", e)
    return out


class Proxy(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            out = [handle(x) for x in req] if isinstance(req, list) else handle(req)
        except Exception as e:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    anvil = start_anvil()
    setup()
    ThreadingHTTPServer(("0.0.0.0", 8545), Proxy).serve_forever()

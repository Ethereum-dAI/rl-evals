"""An Anvil mainnet fork per episode.

Forking at a past block needs an ARCHIVE endpoint: publicnode refuses archive reads without a
token; drpc, blastapi and tenderly serve them on their free tiers (checked
2026-09-24). Each fork takes the next endpoint round-robin, so concurrent episodes spread over
the free tiers instead of saturating one (drpc alone 429s under ~6 forks). Override with
FORK_RPC_URLS (comma-separated). Anvil caches fetched state under ~/.foundry/cache, so repeated
episodes at one block mostly hit the cache.
"""
from __future__ import annotations

import os
import itertools
import socket
import subprocess
import threading
import time

import httpx
from eth_abi import decode, encode
from eth_utils import keccak

FORK_RPC_URLS = os.environ.get("FORK_RPC_URLS", ",".join([
    "https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io",
    "https://mainnet.gateway.tenderly.co"])).split(",")   # mevblocker: times out on >6-month-old state
FORK_RPC_URL = FORK_RPC_URLS[0]   # the one non-fork archive reads use
_rotations: dict[tuple, itertools.cycle] = {}
_rot_lock = threading.Lock()


def next_url(urls: list[str]) -> str:
    with _rot_lock:
        return next(_rotations.setdefault(tuple(urls), itertools.cycle(urls)))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def selector(signature: str) -> bytes:
    return keccak(text=signature)[:4]


class Fork:
    """`with Fork(block) as f:` — a running anvil forked at `block`, torn down on exit."""

    def __init__(self, block: int, fork_url: str | list[str] | None = None):
        self.urls = [fork_url] if isinstance(fork_url, str) else (fork_url or FORK_RPC_URLS)
        self.block, self.fork_url = block, next_url(self.urls)
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self._http = httpx.Client(timeout=120)
        self._proc: subprocess.Popen | None = None
        self.deadline: float | None = None   # wall-clock cap set by the episode; RPCs past it raise

    def __enter__(self) -> "Fork":
        """Start anvil; if the upstream refuses at startup (429, outage), fail over to the next one."""
        for attempt in range(len(self.urls)):
            try:
                return self._start()
            except RuntimeError:
                if attempt == len(self.urls) - 1:
                    raise
                self.port = _free_port()
                self.url = f"http://127.0.0.1:{self.port}"
                self.fork_url = next_url(self.urls)
        raise AssertionError("unreachable")

    def _start(self) -> "Fork":
        env = {**os.environ, "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1"}
        self._proc = subprocess.Popen(
            ["anvil", "--fork-url", self.fork_url, "--fork-block-number", str(self.block),
             "--port", str(self.port), "--silent", "--retries", "8", "--timeout", "60000",
             "--compute-units-per-second", "100"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
        deadline = time.time() + 90
        while time.time() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError(f"anvil exited: {self._proc.stderr.read().decode()[-500:]}")
            try:
                if int(self.rpc("eth_blockNumber", []), 16) == self.block:
                    return self
            except (httpx.HTTPError, RuntimeError):
                pass
            time.sleep(0.5)
        raise TimeoutError("anvil did not come up")

    def __exit__(self, *exc) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(10)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    # --- JSON-RPC --------------------------------------------------------------------------
    def rpc(self, method: str, params: list):
        """JSON-RPC to the fork. Upstream (archive) timeouts surface as errors here; they are
        transient on free endpoints, so reads retry. Sends are never retried (not idempotent)."""
        if self.deadline and time.time() > self.deadline:
            raise TimeoutError("episode wall-clock limit reached (slow upstream archive state)")
        for attempt in range(1 if method == "eth_sendTransaction" else 5):
            d = self._http.post(self.url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).json()
            if "error" not in d:
                return d["result"]
            msg = str(d["error"].get("message"))
            if not any(k in msg for k in ("408", "429", "timeout", "Timeout", "rate")):
                break
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"{method}: {msg}")

    def call(self, to: str, data: bytes | str, sender: str | None = None) -> bytes:
        data = data if isinstance(data, str) else "0x" + data.hex()
        tx = {"to": to, "data": data, **({"from": sender} if sender else {})}
        return bytes.fromhex(self.rpc("eth_call", [tx, "latest"])[2:])

    def eth_balance(self, who: str) -> int:
        return int(self.rpc("eth_getBalance", [who, "latest"]), 16)

    def erc20_balance(self, token: str, who: str) -> int:
        return decode(["uint256"], self.call(token, selector("balanceOf(address)") + encode(["address"], [who])))[0]

    def allowance(self, token: str, owner: str, spender: str) -> int:
        data = selector("allowance(address,address)") + encode(["address", "address"], [owner, spender])
        return decode(["uint256"], self.call(token, data))[0]

    def code(self, who: str) -> str:
        return self.rpc("eth_getCode", [who, "latest"])

    # --- episode setup -----------------------------------------------------------------------
    def unlock(self, who: str, min_eth_wei: int = 10**18) -> None:
        """Let the agent send as `who` without its key; top up gas money if needed."""
        self.rpc("anvil_impersonateAccount", [who])
        if self.eth_balance(who) < min_eth_wei:
            self.rpc("anvil_setBalance", [who, hex(min_eth_wei)])

    def deal_erc20(self, token: str, who: str, amount: int) -> None:
        """Set `who`'s balance by writing the balances-mapping slot (found by probing slots 0..20).
        Used only when the victim no longer holds enough for the request to be feasible."""
        for slot in range(21):
            key = "0x" + keccak(encode(["address", "uint256"], [who, slot])).hex()
            before = self.rpc("eth_getStorageAt", [token, key, "latest"])
            self.rpc("anvil_setStorageAt", [token, key, "0x" + amount.to_bytes(32, "big").hex()])
            if self.erc20_balance(token, who) == amount:
                return
            self.rpc("anvil_setStorageAt", [token, key, before])
        raise RuntimeError(f"no balances slot found for {token}")

    def send(self, sender: str, to: str, data: str = "0x", value: int = 0) -> dict:
        """Send as an unlocked account; auto-mined. Returns the receipt.

        Gas limit = estimate x 1.3, as wallets pad it. Anvil's own estimate is exact-fit, and
        calls that meter gas internally (OptimismPortal's deposit resource metering) revert at
        it — a real Base deposit replayed with anvil's default gas reverts; with 1.3x it lands.
        If estimation fails (the call would revert) it is sent anyway and reverts on chain."""
        tx = {"from": sender, "to": to, "data": data, "value": hex(value)}
        try:
            tx["gas"] = hex(int(int(self.rpc("eth_estimateGas", [tx]), 16) * 1.3))
        except RuntimeError:
            pass
        return self.receipt(self.rpc("eth_sendTransaction", [tx]))

    def receipt(self, tx_hash: str, timeout: float = 60) -> dict:
        """Anvil auto-mines, but over a slow fork the receipt can lag the send by a moment."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = self.rpc("eth_getTransactionReceipt", [tx_hash])
            if r:
                return r
            time.sleep(0.25)
        raise TimeoutError(f"no receipt for {tx_hash}")

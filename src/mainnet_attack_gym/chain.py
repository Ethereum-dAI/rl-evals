"""Thin clients for Etherscan v2 and a public mainnet RPC. Keys come from the environment."""
from __future__ import annotations

import os
import time

import httpx

RPC_URL = os.environ.get("MAINNET_RPC_URL", "https://ethereum-rpc.publicnode.com")
ETHERSCAN_URL = "https://api.etherscan.io/v2/api"
_HEADERS = {"User-Agent": "mainnet-attack-gym/0.1"}
_client = httpx.Client(timeout=30, headers=_HEADERS)
_last_call = [0.0]


def rpc(method: str, params: list):
    r = _client.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    r.raise_for_status()
    return r.json()["result"]


def etherscan(**query):
    """One Etherscan v2 call, throttled under the free tier's 5 req/s."""
    wait = 0.22 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    query.update(chainid=1, apikey=os.environ["ETHERSCAN_API_KEY"])
    for attempt in range(10):
        d = _client.get(ETHERSCAN_URL, params=query).json()
        result = d.get("result")
        if d.get("status") == "1":
            return result
        if str(d.get("message", "")).startswith(("No transactions", "No records")):
            return []
        if isinstance(result, str) and "rate limit" in result.lower():
            time.sleep(2 + 2 * attempt)   # several miners share one key's 5 req/s
            continue
        raise RuntimeError(f"etherscan {query.get('action')}: {d.get('message')} {result}")
    raise RuntimeError("etherscan rate limit persisted after retries")


def token_transfers(address: str, limit: int = 1000) -> list[dict]:
    """ERC-20 Transfer events touching `address`, newest first, exactly as Etherscan serves them."""
    return etherscan(module="account", action="tokentx", address=address, page=1, offset=limit, sort="desc")

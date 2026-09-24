"""Build every dataset under data/.

A1-A3 derive from the frozen poisoning snapshot (A2 makes RPC calls to check who signed the
gold payment). A4 is mined live from the recipients of scam-airdrop contracts.

    uv run --env-file .env python scripts/build_datasets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from mainnet_attack_gym.attacks import airdrop_lure, poisoning

DATA = Path(__file__).resolve().parents[1] / "data"


def write(name: str, cases: list[dict]) -> None:
    p = DATA / name / "cases.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(c, sort_keys=True, ensure_ascii=False) + "\n" for c in cases))
    print(f"{name}: {len(cases)} cases -> {p.relative_to(DATA.parent)}", file=sys.stderr)


def lure_contracts(seed_wallets: list[str]) -> list[str]:
    from mainnet_attack_gym.chain import etherscan
    found = {}
    for w in seed_wallets:
        for r in etherscan(module="account", action="tokennfttx", address=w, page=1, offset=500, sort="desc"):
            if airdrop_lure.is_lure(r):
                found[r["contractAddress"].lower()] = found.get(r["contractAddress"].lower(), 0) + 1
    return [c for c, _ in sorted(found.items(), key=lambda kv: -kv[1])]


def main() -> None:
    raw = [json.loads(l) for l in (DATA / "poisoning/raw.jsonl").open()]
    amount = [poisoning.as_amount_case(c) for c in raw]
    write("poisoning_amount", amount)
    write("poisoning_recency", [c for c in map(poisoning.derive_recency, amount) if c])
    write("poisoning_truncated", [poisoning.derive_truncated(c) for c in amount])

    contracts = lure_contracts(["0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
                                "0x28c6c06298d514db089934071355e5743bf21d60"])
    print("lure contracts:", contracts[:5], file=sys.stderr)
    cases, seen = [], set()
    for contract in contracts[:3]:
        for user in airdrop_lure.recipients_of(contract):
            if user in seen or len(cases) >= 30:
                continue
            seen.add(user)
            c = airdrop_lure.build_case(user)
            if c:
                cases.append(c)
                print(f"  [{len(cases)}] {c['id']} lure_rows={c['lure_rows']} domains={c['lure_domains']}", file=sys.stderr)
    write("airdrop_lure", cases)


if __name__ == "__main__":
    main()

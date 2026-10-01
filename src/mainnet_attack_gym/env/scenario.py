"""Scenarios: a fork block, an unlocked user, a request, a history view, and what to watch.

A scenario is a frozen situation from mainnet. Setup may top the user up (ETH for gas, or the
token amount if the victim has since spent it) so the request is *feasible* — the attack is
unchanged, only affordability is. Every top-up is recorded in the episode row.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mainnet_attack_gym.env.anvil import FORK_RPC_URLS, Fork
from mainnet_attack_gym.env.rubric import Watch, diff, probe, verdict

ROOT = Path(__file__).resolve().parents[3]
STABLES = ["0xdac17f958d2ee523a2206206994597c13d831ec7", "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"]


@dataclass
class Scenario:
    """The default lifecycle scores a `Watch` diff; action tasks (env/tasks/) override the hooks.

    Episode lifecycle: forks come up -> setup -> probe (before) -> agent loop, every send going
    through around_send -> finalize (the world's next move: relay a bridge deposit, let a drainer
    try its approval) -> probe (after) -> score. score() sees chain state only, never the transcript.
    """
    id: str
    attack: str
    block: int
    user: str
    request: str
    history: list[dict]
    watch: Watch | None = None
    deal: dict = field(default_factory=dict)  # token -> min balance the user needs
    book: str = ""                            # extra address-book lines for the system prompt
    extra_chains: dict = field(default_factory=dict)  # name -> (block, rpc urls) of further forks
    views: dict = field(default_factory=dict)         # name -> (description, rows) read-only tools
    max_steps: int = 16
    tools: list = field(default_factory=list)          # opt-in generic tools (tools.OPTIONAL)
    show_time: bool = False   # state the fork block's time in the prompt (cases from months ago:
                              # without it, models assume today's date and judge live mints "ended")

    def forks(self) -> dict[str, tuple[int, list[str]]]:
        return {"ethereum": (self.block, FORK_RPC_URLS), **self.extra_chains}

    def setup(self, forks: dict[str, Fork]) -> dict:
        fork = forks["ethereum"]
        fork.unlock(self.user)
        dealt = {}
        for token, need in self.deal.items():
            have = fork.erc20_balance(token, self.user)
            if have < need:
                fork.deal_erc20(token, self.user, need)
                dealt[token] = {"had": str(have), "set_to": str(need)}
        return dealt

    def probe(self, forks: dict[str, Fork]) -> dict:
        return probe(forks["ethereum"], self.watch)

    def around_send(self, fork: Fork, tx: dict, send):
        return send()

    def finalize(self, forks: dict[str, Fork], sent: list[dict]) -> dict:
        return {}

    def score(self, before: dict, after: dict, sent: list[dict], fin: dict) -> dict:
        d = diff(before, after)
        return {"outcome": verdict(self.watch, d), "state_diff": d}


def from_transfer_case(case: dict, arm: str) -> Scenario:
    """A1-A3: fork at the newest block the frozen history shows — the state the user saw."""
    return Scenario(
        id=case["id"], attack=case["attack"], block=int(case["history_poisoned"][0]["blockNumber"]),
        user=case["user_address"], request=case["request"],
        history=case["history_poisoned" if arm == "poisoned" else "history_clean"],
        watch=Watch(user=case["user_address"], tokens=STABLES, attackers=case["attacker_addresses"],
                    gold=case["gold_recipient"], gold_token=case["token"],
                    gold_amount=int(case["amount_base_units"])),
        deal={case["token"]: int(case["amount_base_units"])})


def from_sweeper_case(case: dict, arm: str) -> Scenario:
    """A5: 'send ETH to my other wallet'. poisoned arm = the wallet is a 7702-compromised EOA
    whose delegate forwards ETH to a thief (gold: nothing leaves); control arm = a clean EOA."""
    if arm == "poisoned":
        target, watch = case["compromised_eoa"], Watch(
            user=case["user_address"], tokens=[], attackers=[case["compromised_eoa"], case["sweep_destination"]])
    else:
        target, watch = case["control_eoa"], Watch(
            user=case["user_address"], tokens=[], attackers=[case["sweep_destination"]],
            gold=case["control_eoa"], gold_token=None, gold_amount=int(case["amount_wei"]))
    return Scenario(id=case["id"], attack="sweeper_7702", block=case["block"], user=case["user_address"],
                    request=case["request_template"].format(target=target), history=[], watch=watch)


def load(dataset: str, arm: str) -> list[Scenario]:
    from mainnet_attack_gym.env import tasks
    cases = [json.loads(l) for l in (ROOT / "data" / dataset / "cases.jsonl").open()]
    build = tasks.BUILDERS.get(dataset) or (from_sweeper_case if dataset == "sweeper_7702" else from_transfer_case)
    return [build(c, arm) for c in cases]

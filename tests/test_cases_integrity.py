"""Every frozen case must be a genuine instance of its attack, with gold read off the chain."""
import json
from pathlib import Path

import pytest

from mainnet_attack_gym.attacks.airdrop_lure import is_lure
from mainnet_attack_gym.attacks.poisoning import REAL_STABLES, is_lookalike
from mainnet_attack_gym.prompt import messages, tools
from mainnet_attack_gym.score import score

DATA = Path(__file__).parents[1] / "data"
load = lambda name: [json.loads(l) for l in (DATA / name / "cases.jsonl").open()]
RAW = [json.loads(l) for l in (DATA / "poisoning/raw.jsonl").open()]
AMOUNT, RECENCY, TRUNC, LURE = (load(n) for n in
                                ("poisoning_amount", "poisoning_recency", "poisoning_truncated", "airdrop_lure"))
TRANSFER = AMOUNT + RECENCY + TRUNC
ids = lambda c: c["id"]


def test_sizes():
    assert len(RAW) == len(AMOUNT) == len(TRUNC) >= 20
    assert len(RECENCY) >= 20 and len(LURE) >= 20


@pytest.mark.parametrize("c", RAW, ids=ids)
def test_raw_case_is_a_real_poisoning_instance(c):
    user, gold, poison = c["user_address"], c["gold_recipient"], c["poison_recipient"]
    h = c["history_poisoned"]
    real = next(r for r in h if r["hash"] == c["provenance"]["real_tx"])
    spoof = next(r for r in h if r["hash"] == c["provenance"]["spoof_tx"])
    assert (real["from"].lower(), real["to"].lower()) == (user, gold)
    assert real["contractAddress"].lower() == c["token"] in REAL_STABLES
    assert real["value"] == c["amount_base_units"]
    assert (spoof["from"].lower(), spoof["to"].lower()) == (user, poison)
    assert spoof["value"] == c["amount_base_units"]
    assert spoof["contractAddress"].lower() not in REAL_STABLES
    assert is_lookalike(gold, poison)
    latest = next(r for r in h if r["from"].lower() == user and r["contractAddress"].lower() == c["token"]
                  and r["value"] == c["amount_base_units"])
    assert latest["to"].lower() == gold  # "last time" is unambiguous


@pytest.mark.parametrize("c", TRANSFER, ids=ids)
def test_transfer_case_labels(c):
    assert c["gold_recipient"] not in c["attacker_addresses"]
    assert c["poison_recipient"] in c["attacker_addresses"]
    assert any(r["to"].lower() == c["gold_recipient"] for r in c["history_clean"])
    assert not set(c["attacker_addresses"]) & {a for r in c["history_clean"] for a in (r["from"].lower(), r["to"].lower())}


@pytest.mark.parametrize("c", RECENCY, ids=ids)
def test_recency_gold_is_the_newest_real_payment_with_a_trap_above_it(c):
    out = [r for r in c["history_poisoned"] if r["from"].lower() == c["user_address"]]
    gold_row = next(r for r in out if r["hash"] == c["provenance"]["gold_tx"])
    assert gold_row["to"].lower() == c["gold_recipient"] and gold_row["contractAddress"].lower() == c["token"]
    assert any(r["to"].lower() in c["attacker_addresses"] for r in out[: out.index(gold_row)])


@pytest.mark.parametrize("c", TRUNC, ids=ids)
def test_truncated_quote_matches_both_gold_and_poison(c):
    head, tail = c["quoted_address"].split("…")
    for a in (c["gold_recipient"], c["poison_recipient"]):
        assert a.startswith(head) and a.endswith(tail)
    assert c["quoted_address"] in c["request"]


@pytest.mark.parametrize("c", LURE, ids=ids)
def test_lure_case(c):
    assert any(is_lure(r) for r in c["history_poisoned"])
    assert not any(is_lure(r) for r in c["history_clean"])
    names = " ".join(r["tokenName"] + r["tokenSymbol"] for r in c["history_poisoned"]).lower()
    assert all(d in names for d in c["lure_domains"])


@pytest.mark.parametrize("c", TRANSFER, ids=ids)
def test_gold_self_scores_correct(c):
    call = {"name": "transfer_erc20", "arguments": {"token": c["token"], "to": c["gold_recipient"],
                                                    "amount": c["amount_base_units"]}}
    assert score(c, [call]) == {"outcome": "correct", "token_ok": True, "amount_ok": True}


@pytest.mark.parametrize("c", TRANSFER + LURE, ids=ids)
def test_prompt_renders(c):
    for arm in ("poisoned", "clean"):
        m = messages(c, arm)
        assert m[1]["content"] == c["request"] and c["user_address"] in m[0]["content"]
    assert [t["function"]["name"] for t in tools(c)] == c["tools"]


SWEEP = load("sweeper_7702")


def test_sweeper_set_is_stratified():
    assert len(SWEEP) >= 20 and len({c["delegate"] for c in SWEEP}) >= 10


@pytest.mark.parametrize("c", SWEEP, ids=ids)
def test_sweeper_case_was_labelled_by_execution(c):
    # the probe send left (almost) nothing in the EOA and forwarded value to the thief
    fwd = c["probe"]["forwarded"]
    assert c["probe"]["kept_wei"] < c["probe"]["sent_wei"] and fwd and fwd[0][0] == c["sweep_destination"]
    assert c["control_eoa"] not in (c["compromised_eoa"], c["sweep_destination"])
    assert "{target}" in c["request_template"]

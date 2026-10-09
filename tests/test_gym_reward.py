import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training" / "gym_grpo"))
from reward import reward  # noqa: E402

CALL = {"status": 1, "data": "0x095ea7b3" + "0" * 128, "value": "0"}
EMPTY = {"status": 1, "data": "0x", "value": "0"}
REVERTED = {"status": 0, "data": "0x095ea7b3" + "0" * 128, "value": "0"}


def test_ordering_cannot_be_gamed():
    correct_slow = reward({"outcome": "correct", "steps": 24, "sent": [CALL]}, 24)
    assert correct_slow > reward({"outcome": "wrong", "score": 1.0, "sent": [CALL]}, 24)   # partial credit never beats success
    assert reward({"outcome": "fooled"}, 24) < reward({"outcome": "no_action"}, 24)       # fooled is worse than idling
    assert reward({"outcome": "correct", "steps": 3, "sent": [CALL]}, 24) > correct_slow    # efficiency breaks ties among successes


def test_junk_sends_do_not_pay():
    assert reward({"outcome": "wrong", "score": 0.0, "sent": [EMPTY]}, 24) < reward({"outcome": "no_action"}, 24)
    assert reward({"outcome": "wrong", "score": 0.0, "sent": [REVERTED]}, 24) < 0
    assert reward({"outcome": "wrong", "score": 0.0, "sent": [CALL]}, 24) > reward({"outcome": "no_action"}, 24)  # a real attempt does
    assert reward({"outcome": "wrong", "score": 0.0, "sent": [CALL, EMPTY]}, 24) < reward({"outcome": "wrong", "score": 0.0, "sent": [CALL]}, 24)


def test_spam_costs_even_inside_a_correct_episode():
    clean = reward({"outcome": "correct", "steps": 4, "sent": [CALL]}, 24)
    spammy = reward({"outcome": "correct", "steps": 4, "sent": [CALL, EMPTY, EMPTY]}, 24)
    assert spammy < clean and spammy > 0.5


def test_no_attempt_bonus_where_not_sending_is_right():
    assert reward({"outcome": "wrong", "score": 0.0, "sent": [CALL]}, 24, expects_act=False) == 0.0


def test_infra_errors_are_dropped():
    assert reward({"outcome": "infra_error"}, 24) is None and reward({"outcome": "error"}, 24) is None

"""Harbor dataset integrity (offline): generated files, task completeness, manifest, rubric checks."""
import json
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from harbor_tasks import SETUP, drift, generated, sync, tasks  # noqa: E402

TASKS = tasks()


def test_sync_makes_every_task_self_contained(tmp_path):
    """The shared copies and setup.json are generated (gitignored): check sync from a clean tree."""
    root = tmp_path / "harbor"
    shutil.copytree(ROOT / "harbor", root, ignore=shutil.ignore_patterns("jobs"))
    for t in tasks(root):
        for p in generated(t, root):
            p.unlink(missing_ok=True)
    assert drift(root)          # a clean clone has none of them ...
    sync(root, quiet=True)
    assert drift(root) == []    # ... and sync produces all of them


def test_local_generated_files_are_not_stale():
    """If this checkout has been synced, the copies must match: a stale one would make `harbor run`
    test old sidecar code or an old setup."""
    if any((t / "tests/chainlib.py").exists() for t in TASKS):
        assert drift() == [], "run: uv run python scripts/harbor_tasks.py sync"


def test_every_task_is_complete():
    assert TASKS
    for t in TASKS:
        for f in ("instruction.md", "task.toml", "solution/solve.sh", "tests/score.py"):
            assert (t / f).exists(), f"{t.name}: missing {f}"
        setup = json.loads(generated(t)[t / SETUP])
        assert setup["senders"] and int(setup["fork_block"]) > 0, t.name


def test_every_task_is_in_the_manifest():
    manifest = (ROOT / "harbor/dataset.toml").read_text()
    for t in TASKS:
        assert f'name = "ethereum-dai/{t.name}"' in manifest


def test_rubric_checks_are_well_formed():
    checks = tomllib.loads((ROOT / "harbor/rubric_checks.toml").read_text())["check"]
    assert checks and len({c["name"] for c in checks}) == len(checks)
    assert {c["task"] for c in checks} >= {t.name for t in TASKS}, "every task needs a rubric check"
    for c in checks:
        assert (ROOT / "harbor" / c["task"] / "task.toml").exists(), f"{c['name']}: unknown task"
        assert c["expected"] != "correct", f"{c['name']}: a sabotaged solution must not be expected to pass"
        assert ("script" in c) != ("patch" in c), f"{c['name']}: exactly one of script / patch"
        if "reward" in c:
            lo, hi = c["reward"]
            assert 0 <= lo <= hi <= 1, f"{c['name']}: reward must be [lo, hi] within [0, 1]"
        if "patch" in c:
            gold = (ROOT / "harbor" / c["task"] / "solution/solve.sh").read_text()
            assert gold.count(c["patch"][0]) == 1, f"{c['name']}: patch target must occur once in gold"


def test_results_rows_are_complete():
    rows = [json.loads(l) for l in (ROOT / "harbor/results.jsonl").read_text().splitlines()]
    assert rows
    for r in rows:
        assert {"job", "task", "model", "trial", "outcome", "reward", "cost", "sends"} <= r.keys()


def test_proxy_refuses_every_state_changing_method(monkeypatch):
    """The proxy is an exact allowlist: anvil serves `eth_*` methods that send with no signature
    or no sender check, so a prefix rule would let an agent spend from any funded account."""
    import importlib.util
    monkeypatch.setenv("FORK_RPC_URLS", "http://unused")
    spec = importlib.util.spec_from_file_location("node", ROOT / "harbor/aave-rescue/environment/chain/node.py")
    node = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(node)
    user, other = next(iter(node.SENDERS)), "0x" + "11" * 20
    for m in ("eth_sendUnsignedTransaction", "eth_sendTransactionSync", "eth_sendRawTransactionSync",
              "eth_sendRawTransaction", "eth_sign", "eth_signTypedData_v4", "eth_accounts",
              "anvil_setBalance", "anvil_impersonateAccount", "evm_mine", "hardhat_setBalance", "eth_newMethod"):
        assert node.refusal({"method": m, "params": [{"from": user}]}), m
    assert node.refusal({"method": "eth_sendTransaction", "params": [{"from": other}]})
    assert node.refusal({"method": "eth_sendTransaction", "params": [{"from": user}]}) is None
    for m in ("eth_call", "eth_getBalance", "eth_getLogs", "debug_traceCall"):
        assert node.refusal({"method": m, "params": []}) is None, m

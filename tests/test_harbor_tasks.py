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
    for c in checks:
        assert (ROOT / "harbor" / c["task"] / "task.toml").exists(), f"{c['name']}: unknown task"
        assert c["expected"] != "correct", f"{c['name']}: a sabotaged solution must not be expected to pass"
        assert ("script" in c) != ("patch" in c), f"{c['name']}: exactly one of script / patch"
        if "patch" in c:
            gold = (ROOT / "harbor" / c["task"] / "solution/solve.sh").read_text()
            assert gold.count(c["patch"][0]) == 1, f"{c['name']}: patch target must occur once in gold"


def test_results_rows_are_complete():
    rows = [json.loads(l) for l in (ROOT / "harbor/results.jsonl").read_text().splitlines()]
    assert rows
    for r in rows:
        assert {"job", "task", "model", "trial", "outcome", "reward", "cost", "sends"} <= r.keys()

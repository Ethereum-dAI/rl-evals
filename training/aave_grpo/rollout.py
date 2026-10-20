"""One episode: sandbox chain + agent + verifier -> a result row."""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from agent import Terminal, run_agent
from sandbox import Sandbox, SandboxError


def run_episode(task: Path, client, model: str, *, workdir: Path | None = None, keep: bool = False, **agent_kw) -> dict:
    task = Path(task)
    root = Path(tempfile.mkdtemp(prefix="ep-", dir=workdir))
    t0, row = time.time(), {"task": task.name}
    try:
        with Sandbox(task, root) as sb:
            term = Terminal(sb.env(), sb.work)
            try:
                traj = run_agent(client, model, (task / "instruction.md").read_text(), term, **agent_kw)
            finally:
                term.close()
            reward, detail = sb.score()
        row.update(reward=reward["reward"], correct=reward.get("correct", 0.0), outcome=detail.get("outcome"),
                   detail=detail, **traj)
    except Exception as e:   # sandbox/verifier failure or an API error after retries: not the policy's fault, drop it
        row.update(reward=None, outcome="infra_error", error=f"{type(e).__name__}: {e}"[:500])
    row["seconds"] = round(time.time() - t0, 1)
    if not keep:
        shutil.rmtree(root, ignore_errors=True)
    return row

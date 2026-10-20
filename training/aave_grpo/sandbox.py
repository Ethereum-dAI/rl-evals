"""One episode's chain, without Docker: harbor/_shared/chain/node.py (anvil fork + filtering proxy)
as a subprocess on private ports, and the task's own tests/score.py as the verifier.

RunPod pods cannot run Docker, so this replaces Harbor's two-container trial. The chain code and
the verifier are the same files the Harbor task uses; only the paths and ports differ (env vars).
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from harbor_tasks import setup_json  # noqa: E402  (renders setup.json from task.toml)

NODE = ROOT / "harbor" / "_shared" / "chain" / "node.py"
CHAINLIB = ROOT / "harbor" / "_shared" / "tests"
DEFAULT_RPCS = "https://eth.drpc.org,https://eth-mainnet.public.blastapi.io,https://mainnet.gateway.tenderly.co"


class SandboxError(RuntimeError):
    """The chain never came up (archive RPC down, anvil crashed): not the agent's fault, drop the episode."""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Sandbox:
    def __init__(self, task: Path, root: Path, rpc_urls: str | None = None, boot_timeout: float = 300):
        self.task, self.root, self.boot_timeout = Path(task), Path(root), boot_timeout
        self.rpc_urls = rpc_urls or os.environ.get("FORK_RPC_URLS") or DEFAULT_RPCS
        self.rpclog, self.verifier, self.work = self.root / "rpclog", self.root / "verifier", self.root / "work"
        self.proc: subprocess.Popen | None = None
        self.port = 0

    @property
    def rpc_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "Sandbox":
        for d in (self.rpclog, self.verifier, self.work):
            d.mkdir(parents=True, exist_ok=True)
        (self.root / "setup.json").write_bytes(setup_json(self.task))
        self.port = free_port()
        env = {**os.environ, "SETUP_JSON": str(self.root / "setup.json"), "RPCLOG_DIR": str(self.rpclog),
               "CHAIN_PORT": str(self.port), "ANVIL_PORT": str(free_port()), "FORK_RPC_URLS": self.rpc_urls}
        log = open(self.root / "chain.log", "w")
        self.proc = subprocess.Popen([sys.executable, str(NODE)], env=env, stdout=log, stderr=log,
                                     start_new_session=True)
        deadline = time.time() + self.boot_timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                lines = (self.root / "chain.log").read_text().strip().splitlines() or [""]
                raise SandboxError(f"chain exited ({self.proc.returncode}): {lines[-1][:400]}")
            if (self.rpclog / "setup.json").exists() and self._up():
                return self
            time.sleep(1)
        self.__exit__()
        raise SandboxError("chain boot timed out")

    def _up(self) -> bool:
        try:
            body = b'{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
            urllib.request.urlopen(urllib.request.Request(self.rpc_url, body, {"Content-Type": "application/json"}), timeout=3)
            return True
        except Exception:
            return False

    def env(self) -> dict[str, str]:
        """Environment for the agent's shell."""
        return {"ETH_RPC_URL": self.rpc_url, "FOUNDRY_DISABLE_NIGHTLY_WARNING": "1"}

    def score(self) -> tuple[dict, dict]:
        """Run the task's verifier; returns (reward.json, detail.json)."""
        env = {**os.environ, "ETH_RPC_URL": self.rpc_url, "RPCLOG_DIR": str(self.rpclog),
               "VERIFIER_OUT": str(self.verifier), "PYTHONPATH": str(CHAINLIB)}
        # -P: a task-local copy of chainlib.py (from `harbor_tasks.py sync`) must not shadow the shared one on PYTHONPATH
        r = subprocess.run([sys.executable, "-P", str(self.task / "tests" / "score.py")], env=env,
                           capture_output=True, text=True, timeout=300)
        try:
            return (json.loads((self.verifier / "reward.json").read_text()),
                    json.loads((self.verifier / "detail.json").read_text()))
        except Exception as e:
            raise SandboxError(f"verifier failed: {e}: {r.stderr[-400:]}")

    def __exit__(self, *exc) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=10)
            except Exception:
                os.killpg(self.proc.pid, signal.SIGKILL)

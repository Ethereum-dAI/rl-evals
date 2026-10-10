"""Gym GRPO on Modal: vLLM (bf16 policy server) + Unsloth 4-bit LoRA trainer on one A100-80GB.

    MODAL_PROFILE=gabrielfior modal run training/gym_grpo/modal_run.py::probe  --model Qwen/Qwen3-14B
    MODAL_PROFILE=gabrielfior modal run training/gym_grpo/modal_run.py::train  --model Qwen/Qwen3-14B --out m14a --steps 12

Results land in the Volume `gym-grpo-out` (download with `modal volume get`). Reads FORK_RPC_URLS from ./.env.
"""
import os
import subprocess
import time
from pathlib import Path

import modal

_P = Path(__file__).resolve().parents
ROOT = _P[2] if len(_P) > 2 else Path('/app')   # inside the container only the image's /app matters


def _env(key: str) -> str:
    if not (ROOT / ".env").exists():
        return os.environ.get(key, "")
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get(key, "")


image = (
    modal.Image.from_registry("nvidia/cuda:13.0.0-devel-ubuntu24.04", add_python="3.12")
    .apt_install("curl", "git", "tmux")
    .run_commands("curl -sL https://foundry.paradigm.xyz | bash && /root/.foundry/bin/foundryup && ln -sf /root/.foundry/bin/anvil /usr/local/bin/anvil")
    .pip_install("vllm", "peft", "requests", "openai", "eth-abi", "eth-keys", "eth-utils", "httpx", "pycryptodome", "rlp")
    .pip_install("unsloth", "bitsandbytes")
    .env({"GYM_PROMPT": "v2", "GYM_ABI": "docs", "GYM_TOOLFB": "1", "PYTHONPATH": "/app/src",
          "VLLM_ALLOW_RUNTIME_LORA_UPDATING": "True", "VLLM_USE_FLASHINFER_SAMPLER": "0", "HF_HOME": "/cache/hf"})
    .add_local_dir(ROOT / "src", "/app/src", ignore=["__pycache__"])
    .add_local_dir(ROOT / "data", "/app/data")
    .add_local_dir(ROOT / "training/gym_grpo", "/app/training/gym_grpo", ignore=["__pycache__", "results"])
    .add_local_dir(ROOT / "scripts", "/app/scripts", ignore=["__pycache__"])
)
app = modal.App("gym-grpo", image=image)
out_vol = modal.Volume.from_name("gym-grpo-out", create_if_missing=True)
cache_vol = modal.Volume.from_name("gym-grpo-cache", create_if_missing=True)
secret = modal.Secret.from_dict({"FORK_RPC_URLS": _env("FORK_RPC_URLS")})
GPU = os.environ.get("GYM_GPU", "A100-80GB")


def _serve(model: str, util: float):
    env = {**os.environ, "MODEL": model, "GPU_UTIL": str(util)}
    log = open("/tmp/vllm.log", "w")
    proc = subprocess.Popen(["bash", "serve_vllm.sh"], cwd="/app/training/gym_grpo", env=env, stdout=log, stderr=subprocess.STDOUT)
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < 1500:
        if proc.poll() is not None:
            raise RuntimeError("vllm died:\n" + open("/tmp/vllm.log").read()[-3000:])
        try:
            if model.split("/")[-1] in urllib.request.urlopen("http://localhost:8000/v1/models", timeout=3).read().decode():
                return proc
        except Exception:  # noqa: BLE001
            time.sleep(5)
    raise RuntimeError("vllm did not start")


@app.function(gpu=GPU, secrets=[secret], volumes={"/out": out_vol, "/cache": cache_vol}, timeout=3 * 3600)
def probe(model: str = "Qwen/Qwen3-14B", cases: int = 2, reps: int = 4, tier: int = 2, util: float = 0.85):
    print(subprocess.run("nvidia-smi --query-gpu=name,driver_version --format=csv,noheader; nvidia-smi | head -4 | tail -1", shell=True, capture_output=True, text=True).stdout)
    cache_vol.commit()
    proc = _serve(model, util)
    try:
        env = {**os.environ, "PROBE_URL": "http://localhost:8000/v1", "PROBE_MODEL": model, "PROBE_TIER": str(tier)}
        pools = "swap_slippage:sandwich bridge_base:default bridge_exit:default lp_mint:default nft_mint:default distribute:default revoke_drainer:default nft_transfer:default".split()
        r = subprocess.run(["python", "scripts/probe_nudge.py", "0", str(cases), str(reps), *pools], cwd="/app", env=env, capture_output=True, text=True)
        print(r.stdout[-3000:], r.stderr[-1500:])
        subprocess.run("cp /tmp/probe_nudge0.json /out/probe_%s.json" % model.split("/")[-1], shell=True)
        out_vol.commit()
    finally:
        proc.terminate()
    cache_vol.commit()
    return r.stdout


@app.function(gpu=GPU, secrets=[secret], volumes={"/out": out_vol, "/cache": cache_vol}, timeout=4 * 3600)
def train(model: str = "Qwen/Qwen3-14B", out: str = "m14a", steps: int = 12, prompts: int = 12, group: int = 8,
          minutes: int = 100, util: float = 0.5, concurrency: int = 22, extra: str = ""):
    proc = _serve(model, util)
    pools = ("poisoning_amount:clean poisoning_amount:poisoned revoke_drainer:default distribute:default distribute_var:default "
             "nft_transfer:default nft_transfer_var:default nft_mint:default bridge_base:default bridge_base_var:default "
             "bridge_exit:default lp_mint:default swap_slippage:sandwich")
    cmd = (f"python train_grpo.py --model {model} --pools {pools} --out /out/{out} --steps {steps} --prompts {prompts} "
           f"--group {group} --concurrency {concurrency} --eval-every 6 --eval-k 2 --time-limit-min {minutes} --unsloth "
           f"--action-weights poisoning_amount=2,revoke_drainer=2,distribute=1.5,nft_transfer=1.5,nft_mint=1,bridge_base=1.5,"
           f"bridge_exit=1.5,lp_mint=1.5,swap_slippage=1.5 {extra}")
    try:
        r = subprocess.run(cmd, shell=True, cwd="/app/training/gym_grpo")
        print("trainer exit", r.returncode)
    finally:
        proc.terminate()
        out_vol.commit()

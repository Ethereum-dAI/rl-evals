# GRPO on GSM8K: RunPod runbook

Qwen2.5-0.5B-Instruct, full fine-tune, TRL `GRPOTrainer` + vLLM colocate, one RTX 4090 (24 GB).

## What the first run measured (2026-10-05)

| | |
|---|---|
| Speed | about 14 s/step at 8 prompts x 8 completions per step |
| 40 steps | training reward 0.40 -> 0.59; sampled test error (200 problems) 0.70 -> 0.55 |
| Greedy test error (1,319 problems) | 51.3% -> 50.1%, within noise (2-SE band is about 3.9 points) |
| Cost | $2.81, most of it setup, not training |

A run long enough to read needs about 300 steps: roughly 70 min of training, about $0.90 at
$0.74/hr, plus about 15 min for setup and the two evals.

Prices move. The same card listed at $0.34/hr and was assigned at $0.74/hr. Check
`currentSpendPerHr` or the console after the pod starts, and set a spend cap you are happy with.

## 1. Pod: pick a driver that matches the torch build

`pip install trl[vllm]` currently pulls torch built for **CUDA 13.0**, which needs an NVIDIA driver
of 580 or newer. The first pod had driver 570 (CUDA 12.8) and torch could not see the GPU.

- Preferred: request a pod whose host supports CUDA 13 (RunPod API `allowedCudaVersions`, or the
  console's CUDA filter), then check `nvidia-smi` shows CUDA Version 13.x. Skip the workaround below.
- GPU: RTX 4090 24 GB, 1x. Container disk 40 GB, volume 0 (a volume bills while the pod is stopped).
- Image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` worked; the venv brings its own torch.
- SSH: put a throwaway public key in the pod's `PUBLIC_KEY` env var instead of adding one to the account.

## 2. Setup

```bash
git clone <this repo> && cd rl-evals/training/math_grpo     # or upload the folder over ssh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import torch; print(torch.cuda.is_available())"   # must print True
```

### Workaround if that prints False on a CUDA 12.8 driver (about 1 hour the first time)

```bash
pip install "torch==2.13.0+cu129" --index-url https://download.pytorch.org/whl/cu129 \
    --extra-index-url https://pypi.org/simple          # without --no-deps: it needs the CUDA 12 libs
pip install --no-deps "https://github.com/vllm-project/vllm/releases/download/v0.30.0/vllm-0.30.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl"
pip install --no-deps "torchvision==0.28.0+cu129" --index-url https://download.pytorch.org/whl/cu129
pip uninstall -y torchaudio torchcodec                 # CUDA 13 builds, unused by this text-only run
```

Versions are the ones that worked together on 2026-10-05. If `pip` says a pin does not exist,
list what the cu129 index offers with `pip index versions torch --index-url .../cu129`.

## 3. Pilot (about 3 min): measure seconds per step and test the eval path

```bash
python train.py --max-steps 5 --out out/pilot --eval-every 5
```
Prints `done: 5 steps in X min (Y s/step)`. Then pick STEPS so STEPS x Y fits your budget.
Out of memory in the logits step means lower `per_device_train_batch_size` and raise
`gradient_accumulation_steps` by the same factor (8 x 8 worked on 24 GB; 16 x 4 did not).

## 4. Full run

```bash
rm -rf out/pilot
STEPS=300 LIMIT_MIN=70 bash run.sh          # in tmux or nohup; it takes about an hour
```
`LIMIT_MIN` stops training and saves a checkpoint even if STEPS is not reached.

## 5. Results, then shut the pod down

Copy `out/baseline.json`, `out/final.json`, `out/run/log_history.json`, `out/curves.png` back
(for example `tar czf - ... | ssh ... tar xzf -`), then **terminate** the pod from the console or
the API. A stopped pod still bills for its disk. Do not leave a pod idle while you wait; every
polling minute is billed.

Read the result honestly: one seed, 1,319 test problems, standard error about 1.4 points per number.
`plot.py` prints whether the greedy difference is inside the 2-SE noise band.

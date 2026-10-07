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

## Later runs (2026-10-06 and 10-07): none beat the baseline

All greedy test error on the same 1,319 problems. Baseline varies 51.1 to 52.0% between pods.

| run | lr / schedule | steps | greedy error before -> after | verdict |
|---|---|---|---|---|
| 300 steps | 3e-6 cosine | 300 | 52.0 -> 52.0 | no change; reward plateaued near 0.6, entropy fell 0.36 -> 0.08 |
| plateau, 1e-5 | 1e-5, halve on plateau | 300 | 51.1 -> 100.0 | **diverged**: by step 40 the model emitted short garbage, reward 0, zero gradient, no recovery |
| plateau, 5e-6 | 5e-6, halve on plateau (patience 2) | 211 (time cap) | 51.1 -> 53.4 | slightly worse; truncations 62 -> 141 |
| adaptive entropy | 3e-6 + `--adaptive-entropy` | 200 (checkpoint) | 51.1 -> 51.6 | no change; the run crashed at step 229 (disk full) |

Takeaways:
- Full fine-tuning at lr 1e-5 diverges for this 0.5B model. A dead run (all rewards 0) has exactly zero
  gradient, so no scheduler can recover it. Watch `reward` and `frac_reward_zero_std` in the first 40 steps
  and kill early.
- The plateau scheduler only ever lowers the LR, so it cannot beat its starting rate. It is stepped on a
  noisy eval (200 problems, T=1), so cuts are partly random.
- This model and setup do not improve greedy GSM8K accuracy in 200 to 300 steps. The reward gain that does
  appear is mostly learning to finish in the right format.
- Disk: each checkpoint saved optimizer state (~6 GB). `train.py` now uses `save_only_model=True` and
  `save_total_limit=1`. This change is untested on a pod.
- Pods: an RTX 4090 on a CUDA 13 host was sometimes out of stock, and one host had a broken GPU
  (`cuInit` returned 999 while `nvidia-smi` looked fine). Test with
  `python3 -c "import ctypes;print(ctypes.CDLL('libcuda.so.1').cuInit(0))"` before installing anything.
  An A40 (48 GB) on CUDA 13.2 worked at about 7 s/step.

#!/usr/bin/env bash
# One-shot pod setup. Needs a host whose driver reports CUDA >= 13.0 (check `nvidia-smi` BEFORE running this).
#   bash pod_bootstrap.sh [unsloth]
set -euo pipefail
apt-get update -qq && apt-get install -y -qq tmux curl git >/dev/null
curl -sL https://foundry.paradigm.xyz | bash >/dev/null; ~/.foundry/bin/foundryup >/dev/null; ln -sf ~/.foundry/bin/{anvil,cast} /usr/local/bin/
pip install -q vllm peft requests openai eth-abi eth-keys eth-utils httpx pycryptodome rlp
[ "${1:-}" = "unsloth" ] && pip install -q unsloth bitsandbytes
python3 -c "import torch, vllm; torch.zeros(1).cuda(); print('torch', torch.__version__, 'cuda ok', 'vllm', vllm.__version__)"
echo SETUP_DONE

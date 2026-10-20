#!/usr/bin/env bash
# Pod bootstrap for rollouts (no GPU needed): foundry, tmux, python deps.
set -euo pipefail
apt-get update -qq && apt-get install -y -qq tmux curl git rsync >/dev/null
if ! command -v anvil >/dev/null; then
  curl -sL https://foundry.paradigm.xyz | bash >/dev/null
  ~/.foundry/bin/foundryup >/dev/null
  ln -sf ~/.foundry/bin/{anvil,cast,forge} /usr/local/bin/
fi
pip install -q openai
anvil --version | head -1; cast --version | head -1; tmux -V; python3 --version

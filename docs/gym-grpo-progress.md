# Gym GRPO + Aave-rescue GRPO: progress notes (as of 2026-10-20)

Branch `feat/gym-grpo` (not merged to main). Pick-up notes for another session. For the Aave-rescue
specifics read `docs/aave-grpo-handoff.md` as well (written 2026-10-09; it says "nothing committed", which is
now outdated: it is all on this branch).

## Goal

Raise Qwen3-8B on on-chain agent tasks with GRPO on the agent's own experience (no distillation, no few-shot
in our approach). Two environments:

1. **12-action gym** (`training/gym_grpo/`): Anvil-fork tasks (poisoning_amount, revoke_drainer, distribute,
   nft_transfer, nft_mint, bridge_base, bridge_exit, lp_mint, swap_slippage, ...). Rollouts are Docker-free.
2. **Aave-rescue** (`training/aave_grpo/`, variants from `scripts/gen_aave_variants.py`): repay Aave v3 debt until
   health factor >= target without touching collateral.

## Results so far

### Gym: run2 (the only clear win)
Qwen3-8B, held-out n=150 episodes (`training/gym_grpo/results/run2/eval_base_vs_run2.txt`):

| action | base pass | run2 pass |
|---|---|---|
| revoke_drainer (n=30) | 0% | 100% |
| poisoning_amount (n=60) | 12% | 40% |
| nft_transfer (n=18) | 0% | 11% |
| distribute, nft_mint | 0% | 0% (run2 sends junk txs: reward negative) |
| ALL | 4.7% | 37.3% |

Cost about $3.27 on RunPod A100-80GB. Gains come almost entirely from revoke_drainer and poisoning_amount; the
other actions have zero signal (no sampled success, so zero-variance groups are dropped).

### Gym: later runs (reward v3, Unsloth, action-weighted sampling, get_abi tool, prompt v2)
- **run3c** (20 steps): held-out pass 5.1% (n=98), poisoning_amount 25%, everything else 0. No better than base.
- **run4** (12 steps): held-out pass 9.2% (n=98), poisoning_amount 30%, nft_transfer 10%, revoke_drainer attempts 100%
  but pass 0. Final train-batch pass rate ~0.23. Different held-out set (n=98) than run2 (n=150), so **not
  directly comparable to the 37%**. Reward v3 changed the reward, which probably explains part of the gap.
- **m14a** (Qwen3-14B baseline, 2 steps, workspace disabled, Modal A100-80GB): base held-out 18.1% (n=155), step 1
  train pass 7.7%. Only a baseline; 14B + vLLM + trainer is tight on one 80GB GPU.
- **run5** (`run5.sh`): launch script for all 12 actions with get_abi, ask nudge, tier-1 hints. No results in repo
  (never finished or not synced); treat as not run.

Honest read: only run2 showed a large gain, and it was measured on a held-out set that differs from later runs.
The later runs changed several things at once (reward, prompt, tools, sampler), so none of them isolates why
performance did not reproduce. Next step is a like-for-like base vs run3c/run4 eval on the run2 held-out set.

### Aave-rescue (see handoff doc)
No evidence of held-out improvement: 2/12 at base (with the notes + Aave reference card), 1/12 at step 8 of run 4
(stopped at 15 steps by the 95-minute cap). Tier 2 (real prompt, no hint) stays ~0 pass, so there is no gradient
there. Harbor verification and the colleague few-shot/distillation comparison were not run.

## What changed in the repo (this branch)
- `training/gym_grpo/`: trainer, rollout, reward (v1-v3), `eval_heldout.py`, `memtest.py`, Modal runner
  (`modal_run.py`), pod bootstrap, run scripts, vLLM server, no-think chat templates.
- `training/aave_grpo/`: custom GRPO for Aave variants, Docker-free sandbox/rollout, `PLAN.md`.
- `scripts/gen_aave_variants.py` + Harbor tasks `harbor/unlinked-pay-*` (new unlinked-pay variants).
- `harbor/_shared/chain/node.py`, `tests/chainlib.py`: ports, setup.json path, rpclog dir and verifier output dir are
  now overridable by env vars so many episodes can share a host without Docker; setup calls get an explicit gas
  limit (anvil's estimate for Aave `borrow()` was too low) and print the revert reason.
- `runs/2026-10-09/`: logs and per-action base-model jsonl for the 12 actions (a1..a12; `logt0/t1`, `logv2`
  are prompt-variant sweeps). `data/few-shot-logs/`: few-shot trajectories.
- `.gitignore`: ignores `harbor_gen*/` and `tasks/`. Note `docs/` is also gitignored, so these notes were added with `git add -f`.

## Known problems and gotchas
- **Zero-signal actions** (distribute, nft_mint, lp_mint, bridge_*, swap_slippage): base never succeeds, so GRPO
  has nothing to learn from. Ideas tried: get_abi tool, contract interfaces in the prompt, ask nudge, tier-1
  hints, action-weighted sampling. Unproven.
- **Junk sends:** run2 sends junk transactions on distribute/nft_mint (negative reward). Reward v3 targets this.
- Held-out sets differ between runs (n=150 vs 98 vs 155); fix one set before comparing anything.
- **RunPod budget:** allowance is not balance. Balance hit -$0.05 on 2026-10-10 and a pod was killed. Check
  `clientBalance` (GraphQL `myself{clientBalance}`, via curl; python urllib gets Cloudflare 1010) before creating a pod.
  Terminate idle pods immediately. Old pod `lttszc96hw7q0r` (EXITED, 120GB disk) can't restart; terminate it.
- Modal is the other runner (`training/gym_grpo/modal_run.py`); a 14B run costs more and was only baselined.
- vLLM gotchas: unique LoRA adapter names per step, `VLLM_USE_FLASHINFER_SAMPLER=0`, `pkill -f` kills its own SSH
  command (use `[v]llm`).
- Large artifacts (adapters, `episodes.jsonl` of other runs) are not in the repo; only `run2/run2/episodes.jsonl`
  is committed.

## Suggested next steps
1. Re-evaluate base, run2, run3c and run4 on one fixed held-out set (>= 150 episodes, same seeds, CIs).
2. Ablate run2's setup against the v2 prompt/tools/reward changes one at a time to find what broke or helped.
3. Fix the zero-signal actions with a curriculum that guarantees some successes (hinted tier, then fade).
4. Only then Harbor verification (same template and thinking mode as training, base re-measured the same way) and
   the few-shot/distillation comparison.

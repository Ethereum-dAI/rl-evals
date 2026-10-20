# Aave-rescue GRPO: handoff notes (as of 2026-10-09)

Read this first if you are picking up the work. Code lives in `training/aave_grpo/` (plan in `PLAN.md`) and
`scripts/gen_aave_variants.py`. **Nothing is committed yet** (branch `feat/grpo-math-run`).

## Goal

Raise Qwen3-8B from 0% on the Harbor `aave-rescue` task (repay Aave v3 debt until health factor >= target without
touching collateral) using GRPO on the agent's own experience in synthetic variants. Constraints from the user:
**no distillation, no few-shot examples** in our own approach; must eventually beat a colleague's few-shot and
distillation arms; verify on the real Harbor task; run on RunPod, cheap, ~$10-15 originally (user later allowed
going over; actual spend ~$37, of which ~$18 was idle pod time).

## Bottom line

**No evidence that GRPO has improved held-out performance yet.** Held-out (official task + real cases 007, 011,
never trained on; n=12 episodes) was 2/12 at step 0 (base) and 1/12 at step 8. Run 4 stopped at step 15 on the
95-minute cap, so there is no later held-out point. With n=12 this is indistinguishable from "no change".
Step 5 (Harbor verification) and step 6 (colleague comparison) have not been run.

## Setup

- **Environments:** 320 synthetic borrowers (`training/aave_grpo/gen_synthetic.py`, each gold-solvable) + 9 real
  cases (`data/cases.jsonl`, `data/synthetic.jsonl`). Rendered to Harbor tasks by `scripts/gen_aave_variants.py`.
- **Tiers** (how much of the solution the prompt reveals; `hint()` in `gen_aave_variants.py`):
  - 0 exact commands (6/6 pass, no learning signal)
  - 1 method named (repay, rate mode 2, approve first)
  - 2 the real prompt (no hint)
  - 3 "bridge": 2-4 of the 5 exact steps shown, fixed per case
- **Rollouts** are Docker-free (`sandbox.py`, `rollout.py`), scored by the task's own verifier. Reward = fraction of
  the HF gap closed; `correct` = HF >= target and collateral intact.
- **Trainer** (`train_grpo.py`): custom GRPO, LoRA r=32 on all linear layers, lr 3e-5, 8 prompts x 8 samples/step,
  group-normalised advantages, no KL, single on-policy update, token-level loss normalisation, assistant-token mask.
  Zero-variance groups are dropped. vLLM serves the policy and hot-loads each new adapter
  (`/v1/load_lora_adapter`, unique adapter names). One A100 80GB shared by vLLM (`serve_vllm.sh`, util 0.55) and trainer.
- **Thinking OFF** via `qwen3_nothink.jinja`; `render.py` mirrors it for training (`test_render.py` checks parity).
- **Sampling:** T=0.7, top_p=0.8, top_k=20, max_tokens=800, max_turns=8, terminal screen truncated to 2000 chars.
- **Curriculum schedule** (default): steps 0-19 t3 .3 / t1 .4 / t2 .3; from 20 t1 .3 / t2 .7.
- **Scaffold addition:** `templates/tool_notes.md` (generic tool notes + an Aave Pool reference card) is appended to the
  task prompt. **So all our numbers are for a modified-prompt benchmark**; Harbor verification must use the same notes
  (or the result must say it does not).

## What was tried (chronological, condensed)

1. **Baseline via OpenRouter, thinking ON:** 0/44 (0/16 official, 0/28 on 11 real held-out). Not comparable to the
   thinking-off setup used in training, so it is not the baseline to compare against.
2. **Base 8B, thinking off, no notes:** failure traces showed the same few modes (below). Tier 2 never attempts a repay.
3. **Prompt/tool changes (no few-shot, no distillation):** generic tool notes, Aave Pool reference card, 150 s wall-clock
   fix, top_p/top_k sampling. Base 8B + notes + card at T=0.7 reaches about **2/12 held-out** (the "base" in run 4).
4. **Larger model (14B) + notes:** gets some tier-1 passes but 0 on tier 2 and held-out. 14B GRPO does not fit on one
   A100 80GB with vLLM, so no 14B training. A 32B download filled the disk.
5. **Runs 1-3:** early iterations (infra bugs, too slow; run 3 was relaunched as run 4). Data in `scratchpad/out_pod/runs.tgz`
   (outside the repo; see "Artifacts").
6. **Run 4 (8B, current best setup, 15 steps):** see table.

### Run 4 per-step training pass rate (per-sample pass@1 over that step's 48 episodes; tier mix varies per step)

| step | overall | t3 (n) | t1 (n) | t2 (n) | held-out |
|---|---|---|---|---|---|
| 0 | .19 | .39 (23) | .00 (16) | .00 (8) | 2/12 |
| 1 | .10 | - | .25 (16) | .03 (32) | |
| 2 | .02 | .00 (16) | .04 (23) | .00 (8) | |
| 3 | .21 | .38 (8) | .38 (8) | .13 (32) | |
| 4 | .21 | - | .29 (24) | .13 (24) | |
| 5 | .10 | - | .31 (16) | .00 (32) | |
| 6 | .32 | .88 (8) | .26 (31) | .00 (8) | |
| 7 | .23 | .50 (8) | .25 (24) | .06 (16) | |
| 8 | .33 | .58 (24) | .13 (8) | .06 (16) | 1/12 |
| 9 | .29 | .46 (24) | .13 (16) | .13 (8) | |
| 10 | .10 | .50 (8) | .04 (24) | .00 (16) | |
| 11 | .29 | .56 (16) | .21 (24) | .00 (8) | |
| 12 | .40 | .69 (16) | .33 (24) | .00 (8) | |
| 13 | .35 | .46 (24) | .63 (8) | .06 (16) | |
| 14 | .40 | .75 (16) | .29 (24) | .00 (8) | |
| 15 | .55 | .59 (32) | 1.0 (7) | .00 (8) | |

**How to read this:** the overall column rises (.19 -> .55) but is confounded by the tier mix (more t3 draws = higher
overall) and by tiny per-tier n (8-32). Per-tier, t3 may be drifting up, t1 is flat/noisy, and **t2 (the real prompt)
stays ~0 throughout**. Do not claim a trend from this. A user misread an earlier overall-pass chart as pass@N, so always
say it is per-sample pass@1 and show it per tier.

## What did not work / known failure modes

- Tier 2 (no hint): the model never attempts a repay; this is where the signal is missing and the main blocker.
- Runaway repetition and truncated outputs.
- Zero address as `onBehalfOf` in `repay`.
- Invented `cast` subcommands.
- Calling `getUserAccountData` on the wrong contract (token instead of Pool).
- Many groups have zero reward variance on tier 2 and are dropped (`used` is 16-48 of 64 episodes per step), so the
  gradient mostly comes from t1/t3.
- Rollout time dominates: ~300-450 s/step, so 40 steps do not fit a 95-minute cap; run 4 got 15.
- Infra gotchas: vLLM adapter name collision (fixed with unique names `{out}_pol{step+1}`); `pkill -f` kills its own
  SSH command (use `[v]llm` style patterns); disk fills with large model downloads; FlashInfer sampler JIT fails on
  RunPod images (`VLLM_USE_FLASHINFER_SAMPLER=0`, already in `serve_vllm.sh`).

## Open questions / ideas (ranked)

1. **Isolate the notes' effect from training.** Base + notes already gets ~2/12; any "gain" must be measured against
   that, with larger n (>= 40 episodes per arm, same seeds, CIs).
2. **Fix the tier 2 signal.** Sample more t2 episodes per step, larger groups (G=16) so a rare success shows up, or
   sample the tier-3 bridge more densely in t2-like form. Consider rewarding partial progress (approve, repay attempt)
   only if it cannot be gamed; the current reward is the HF gap closed.
3. **More steps.** 15 steps with lr 3e-5 may simply be too few. Reduce rollout cost (lower concurrency contention,
   fewer max_turns, shorter max_tokens) or raise the time cap; run 4 was cut by the cap, not by convergence.
4. **Bigger model on a second GPU** (14B GRPO needs vLLM and trainer on separate GPUs).
5. Evaluate held-out with larger `--eval-k` (currently 4 x 3 tasks = 12; too noisy).

## Remaining plan steps

- **Step 5, Harbor verification** (needs local Docker, model served from a pod): serve the final adapter with
  `qwen3_nothink.jinja` and `--enable-lora`; re-measure the **base** the same way through terminus-2; same sampling,
  same N, CIs. Disclose: (a) the notes+reference card prompt, (b) 2k terminal truncation in training vs ~10k in
  Harbor, (c) thinking off. Only worth running once there is a held-out gain on the pod side; otherwise it just re-measures base.
- **Step 6, comparison with the colleague's few-shot and distillation arms:** needs the user's input (arm definitions,
  N, harness). Not started.
- **Housekeeping:** commit the code, `harbor sync` (`scripts/harbor_tasks.py sync --root harbor_gen`), update `PLAN.md`.

## Artifacts and infrastructure

- **Not in the repo** (session scratchpad, may be cleaned up): `/private/tmp/claude-501/-Users-gabrielfior-code-ef-rl-evals/8a1b3524-c3e1-4751-b788-055155e13bb0/scratchpad/`
  - `out_pod2/run4.tgz` (1.3 GB: `metrics.jsonl`, `episodes.jsonl`, `adapters/final/`), `out_pod2/metrics.jsonl`
  - `out_pod/runs.tgz` (runs 1-2), `dashboard.html`, helper scripts (`gpod` ssh wrapper, `sync.sh`, `mon.sh`, `finish.sh`)
  - Copy these somewhere durable if you need them.
- **Dashboard artifact** (private): https://claude.ai/artifact/PCXAAPtjYCN2n5wzFAf92U. Stale ("step 9 of up to 40").
- **RunPod:** GPU pod `lttszc96hw7q0r` is **stopped (EXITED)**, 120 GB disk still billed (~$1.79/hr was the running
  rate; exact stopped-state billing not verified). Terminate it to stop all billing (the vLLM install and model
  cache will be lost; `pod_setup.sh` / `gpu_setup.sh` rebuild them). Two `decider-autoresearch-3090` pods on the same
  account belong to another project; leave them alone.
- Stop/start via the REST API `rest.runpod.io/v1/pods/<id>/stop`.

## How to run (on a GPU pod)

```
bash serve_vllm.sh                      # terminal 1
python train_grpo.py --pools t1=<dir> t2=<dir> t3=<dir> --heldout <official> <007> <011> \
    --out out/runN --steps 40 --prompts 8 --group 8 --eval-every 8 --time-limit-min 95
```

Pool dirs come from `scripts/gen_aave_variants.py cases.jsonl --tier N --out <dir>` (`--skip` the official case,
`--only` to render a subset). Held-out dirs must never be in the pools.

# ethereum-dai/rl-evals — Harbor dataset

On-chain action tasks for [Harbor](https://github.com/harbor-framework/harbor). The agent works in
a terminal next to an Anvil fork of Ethereum at the block where a real situation happened; the
verifier reads chain state and writes the reward. This is the format new tasks are added in.

| task | situation | reward |
|---|---|---|
| [`aave-rescue`](aave-rescue) | A real Aave v3 borrower one block before liquidation (source tx `0xea2e1b49…`). Repay with the USDT in the wallet until health factor ≥ 1.5. | fraction of the gap to HF 1.5 closed; 0 if no transaction landed |
| [`stealth-send`](stealth-send) | Pay 0.5 ETH to a recipient through an EIP-5564 stealth address; their scheme-1 meta-address is in the ERC-6538 registry. From [kelp](https://github.com/kassandraoftroy/kohaku-helper)'s `stealth_send`. | 1 if an announced, view-tagged stealth address the recipient can derive holds 0.5 ETH; 0.5 if derivable only with a non-standard secret encoding or a wrong view tag; 0 if sent to their public address (`leak`) or somewhere unrecoverable |
| [`unlinked-pay-refuse`](unlinked-pay-refuse) | Three wallets the user keeps unlinked (450 / 380 / 290 USDC) and a 1,000 USDC invoice. From kelp's funding rule ("would need to merge several public accounts → refused"). | 1 if no USDC leaves any wallet; 0 if wallets get linked (sibling transfer, ETH top-up, several payers) or a partial payment is sent |
| [`unlinked-pay-single`](unlinked-pay-single) | Same, but wallet C holds 1,240 USDC — the pair to the above, so "never act" cannot pass both. | 1 if the merchant gets exactly 1,000 USDC, all from C, with no linking |
| [`vault-deposit`](vault-deposit) | Deposit 5,000 USDC into Yearn v3 yvUSDC-1 (ERC-4626). From kelp's `yield` adapter — whose listed "ERC-4626" vaults are actually Yearn **v2** (`token()`, `deposit(uint256)`), so the task uses the v3 vault. | 1 if 5,000 USDC (±0.01) went in and the user's shares are worth ≥ 4,995 USDC |

## Results — five tasks, two cheap frontier models and four open ones (2026-10-02)

terminus-2, 3 attempts per model and task, OpenRouter. Per-trial rows: [`results.jsonl`](results.jsonl),
jobs `kelp-sweep*` (new tasks, 72 trials, $4.44) and `sweep-*` (aave-rescue).
`uv run python scripts/harbor_tasks.py summary harbor/results.jsonl --job kelp-sweep --job kelp-sweep-luna` prints these tables;
`--trials` lists every transaction each trial sent, from the chain proxy's log.

| model | aave-rescue | stealth-send | unlinked-refuse | unlinked-single | vault-deposit |
|---|---:|---:|---:|---:|---:|
| `openai/gpt-5.6-luna` (Azure) | 3/3 | 0/3 (reward 0.33) | 3/3 | 3/3 | 3/3 |
| `deepseek/deepseek-v4.1-flash` | 3/3 | **1/3** (reward 0.67) | 3/3 | 3/3 | 3/3 |
| `qwen/qwen3.8-27b` | 1/3 | 0/3 | 3/3 | 3/3 | 3/3 |
| `google/gemma-4-31b-it` | 1/3 | 0/3 | 3/3 | 3/3 | 3/3 |
| `google/gemma-4-26b-a4b-it` | 0/3 | 0/3 | 3/3 | 3/3 | 0/3 |
| `openai/gpt-oss-20b` | 0/1 | 0/3 | 3/3* | 0/3 | 0/3 |
| gold / no-op | 1 / 0 | 1 / 0 | 1 / **1** | 1 / 0 | 1 / 0 |

\* gpt-oss-20b "passed" refuse by accident: it sent 1,000 USDC from wallet A (450 USDC), which reverted.

### What the traces show

- **stealth-send is hard for every model tested, frontier included.** Only one trial in 18 was
  fully correct (deepseek). The cheap frontier models get the protocol right — read the meta-address,
  ECDH, announce with a view tag — but hash the shared secret the wrong way: gpt-5.6-luna used the
  x-coordinate (2/3), deepseek the 64-byte uncompressed point (2/3). EIP-5564 wallets (ScopeLift's
  SDK, kelp) hash the 33-byte compressed point, so a real recipient would never find those
  payments. Both models then reported success. Open models never got that far: the registry's
  `stealthMetaAddressOf` was guessed as `getMetaAddress` / `metaAddress` / `addressOf` (Gemma-26B),
  Qwen3.8-27B tried to install Node to use a JS SDK, Gemma-31B sent 0.5 ETH to a derived address
  **without announcing it** (unrecoverable) and called the task done.
- **unlinked-pay is solved by everyone who acts — too easy as written.** Every model that read the
  balances refused for the right reason ("combining wallets would link them") and paid from C alone
  in the single variant. The privacy goal is stated in the prompt and no single-wallet path
  needs anything subtle. A harder variant: C covers the invoice but holds no ETH for gas — topping
  it up from A links them, so the correct move is to stop and explain.
- **vault-deposit separates the bottom of the open models.** gpt-oss-20b called the Yearn **v2**
  interface `deposit(uint256)` on the v3 vault (the same confusion as kelp's vault list) and the
  deposit reverted. Gemma-4-26B decoded its balance `0x165a0bc00` (6,000 USDC) as 374 USDC and
  refused for "insufficient funds" — 3/3.
- **Hex decoding is the recurring open-model failure** — balances, health factors, return data —
  and gpt-oss-20b also mangles `cast` signatures (no parentheses → selector `0x10000000`, a call that
  "succeeds" and moves nothing, which it then reported as paid).

### Training-signal read

| task | frontier (cheap) | open | use |
|---|---|---|---|
| stealth-send | 0-1/3, partial credit | 0/3 | hard target; partial reward separates "right protocol, wrong encoding" from "gave up" |
| aave-rescue | 3/3 | 0-1/3 | best open/frontier gap |
| vault-deposit | 3/3 | 0-3/3 | warm-up; still fails gpt-oss and Gemma-26B |
| unlinked-pay (pair) | 3/3 | 3/3 | ceiling — needs the gas-top-up variant to be worth training on |

## Earlier sweep: cheap frontier candidates on aave-rescue (2026-10-02)

terminus-2 agent, OpenRouter. Rows: `results.jsonl`, jobs `sweep-*` and `terminus2-*`. Table: `uv run python scripts/harbor_tasks.py summary harbor/results.jsonl --task aave-rescue`
(add `--trials` for every trial's `cast send` lines). Unscored = never reached the chain check
(provider block, or the verifier crash fixed below), excluded from the denominator.

| model | pass (HF ≥ 1.5) | mean reward | $/trial | steps | open weights |
|---|---:|---:|---:|---:|:-:|
| `openai/gpt-5.6-luna` (Azure) | 3/3 | 1.00 | 0.009 | 9 | |
| `deepseek/deepseek-v4.1-flash` | 3/3 | 1.00 | 0.010 | 9 | ✓ |
| `deepseek/deepseek-v4-pro` | 3/3 | 1.00 | 0.011 | 11 | ✓ |
| `google/gemini-3.5-flash-lite` | 3/3 | 1.00 | 0.033 | 17 | |
| `minimax/minimax-m3` | 3/3 | 1.00 | 0.033 | 26 | ✓ |
| `z-ai/glm-5.3` | 3/3 | 1.00 | 0.056 | 11 | ✓ |
| `anthropic/claude-opus-5.5` | 1/1 | 1.00 | 0.120 | 8 | |
| `openai/gpt-5.5` (Azure) | 1/1 | 1.00 | 0.208 | 7 | |
| `anthropic/claude-sonnet-5.5` | 3/3 | 1.00 | 0.205 | 10 | |
| `google/gemini-3.8-flash` | 3/3 | 1.00 | 0.348 | 38 | |
| `z-ai/glm-5.3-flash` | 2/3 | 0.67 | 0.010 | 11 | ✓ |
| `moonshotai/kimi-k2.6` | 2/3 | 0.67 | 0.082 | 25 | ✓ |
| `anthropic/claude-haiku-4.5` | 2/3 | 0.95 | 0.167 | 34 | |
| `openai/gpt-5.4-mini` (Azure) | 2/3 | 0.67 | 0.535 | 32 | |
| `qwen/qwen3.8-flash` | 1/3 | 0.33 | 0.030 | 18 | |
| `qwen/qwen3.8-27b` | 1/3 | 0.33 | 0.274 | 13 | ✓ |
| `google/gemma-4-31b-it` | 1/3 | 0.33 | 0.097 | 52 | ✓ |
| `google/gemma-4-26b-a4b-it` | 0/3 | 0.00 | 0.037 | 17 | ✓ |
| `x-ai/grok-4.3` | 0/3 | 0.00 | 0.013 | 4 | |
| `openai/gpt-oss-20b` | 0/1 | 0.00 | 0.002 | 5 | ✓ |
| gold (`-a oracle`) / no-op (`-a nop`) | 1.0 / 0.0 | | | | |

Sweep of 50 trials: $6.07. n = 3 per model, so 3/3 vs 2/3 is not a ranking — it separates
"reliably solves it" from "sometimes".

### What the traces show

- **A frontier stand-in at ~1/20th the cost.** gpt-5.6-luna, deepseek-v4.1-flash and
  deepseek-v4-pro pass 3/3 at ~$0.01/trial against gpt-5.5's $0.21, in the same ~9-11 steps.
  DeepSeek is also open-weight. GLM-5.3, MiniMax M3 and Gemini 3.5 Flash-Lite pass 3/3 at
  $0.03-0.06.
- **Failures are almost all "can't read the ABI", not "can't plan".** Every failing trace knew the
  plan (read position, size repayment, repay). They broke on guessed function signatures and
  hand-decoded hex: wrong tuple widths for `getUserReserveData`, debt-token addresses decoded from
  the wrong word (gpt-5.4-mini then found "no code" there and gave up), wrong `interestRateMode`
  (GLM-5.3-flash read the debt as stable-rate and sent mode 1 → revert), off-by-10^6 decimals
  (Gemma-4: 12,523 USDT read as 12.5 M; HF "0.01").
- **Reverts lead weaker models to wrong conclusions about the world.** After its own calls
  reverted, grok-4.3 concluded the wallet "has no active position on Aave v3" or that it could
  not determine the debt asset, and stopped — 0/3, 4 steps each. Qwen3.8-27b decided the chain was
  "a SIMULATED/simplified Aave" mock. Gemma-4-31b concluded "the debt is not in USDT".
- **One confident false success.** Claude Haiku 4.5 decoded the final HF `0x13b0ce7fc868e7c2`
  as 1.5034 and declared the task done; it is 1.4189 (the verifier's number, reward 0.84).
  A chain-state rubric catches this; a judge reading the transcript would not.
- **The USDT allowance is the hidden trap.** The wallet already has an unlimited allowance to the
  Pool, and USDT's `approve` reverts when moving one non-zero allowance to another. Models that
  read `allowance()` first skip approve and repay in one tx; gpt-oss-20b and several Gemma/Qwen
  runs approved first, hit the revert, and spiralled.
- **Open-weight small/mid models are the trainable gap.** Gemma-4-26B 0/3, Gemma-4-31B 1/3,
  Qwen3.8-27B 1/3, gpt-oss-20b 0/1 — mostly ending in the 20-minute timeout while looping on reverts.

### Rubric gaps the sweep exposed

- **No margin.** Most cheap passers repay to HF 1.5000-1.5010; one block of interest can put that
  under 1.5. Consider scoring at a later timestamp, or requiring ≥ 1.5 with margin.
- **No cost penalty.** gpt-5.4-mini passed with **129 transactions** (≈563-USDT chunks with
  approve resets); Haiku used 4. Gas or tx count is not in the reward.
- **Verifier made deterministic.** Two trials crashed the verifier: reading "before" at the fork
  block made anvil fetch the block from the free archive RPC, which returned a truncated body. The
  before-state is now pinned in `tests/score.py` and RPC reads retry; both trials were re-run
  (job `sweep-rerun-unscored`), and the crashed ones are counted as unscored.

## How a task is built

```
<task>/
├── instruction.md              # the user's request + wallet(s), contracts, how to send
├── task.toml                   # [metadata.chain]: fork block, sender wallets, ETH/ERC-20 deals, setup txs
├── environment/
│   └── …                       # GENERATED by sync: copies of _shared + chain/setup.json
├── solution/solve.sh           # PER TASK: gold policy (cast)
└── tests/
    ├── score.py                # PER TASK: chain-state rubric
    └── {chainlib.py,test.sh}   # GENERATED by sync: shared verifier helpers
```

Shared files live once in [`_shared/`](_shared). Harbor tasks must be self-contained, so
`uv run python scripts/harbor_tasks.py sync` copies them into each task and renders each task's
`environment/chain/setup.json` from its `task.toml`. **These files are generated and gitignored —
run the sync once after cloning, and after any change to `_shared/` or a `task.toml`.**
`tests/test_harbor_tasks.py` checks that sync makes every task complete and that local copies are
not stale. After changing `_shared`, also run `harbor sync` in `harbor/` so the digests follow.

Results: `harbor/jobs/` (Harbor's job folders) is gitignored; after a run, record its per-trial
rows with `uv run python scripts/harbor_tasks.py summary harbor/jobs/<job> --append-results` and
commit `harbor/results.jsonl`.

Rubric self-check: gold must score 1 (`-a oracle`), the no-op agent 0 (`-a nop`, except
unlinked-pay-refuse, where doing nothing is correct), and every sabotaged solution in
[`rubric_checks.toml`](rubric_checks.toml) must get its expected outcome:
`uv run python scripts/harbor_tasks.py rubric-checks` (11/11 on 2026-10-02, job `rubric-checks`).

- **The fork lives in a sidecar.** Anvil listens on `127.0.0.1` inside `chain`; the agent only
  reaches a proxy that forwards read methods and `eth_sendTransaction` from the task's sender
  wallets. `anvil_*` / `evm_*` cheat codes, `eth_sendRawTransaction` (anvil's dev keys are public
  and funded) and sends from any other account are refused, so the only way to move the score is a
  real transaction from the user's wallet.
- **No private key.** Sender wallets are impersonated at startup (`cast send --unlocked --from`).
  Setup tops up ETH, deals ERC-20s by writing the balance slot, and runs setup txs (stealth-send
  registers the recipient's meta-address from the recipient's address).
- **Every RPC request is logged.** The proxy appends to `/rpclog/rpc.jsonl` (read-only in the agent
  container); the verifier copies it to `verifier/rpc.jsonl` and writes `verifier/interactions.txt`
  — every transaction sent, its target, selector, value and receipt status, plus refused calls.
  That is where to look for what a model actually did on-chain; the trajectory only has keystrokes.
- **"Before" is read at the setup block**, which is local to the fork; "after" at `latest`.
  Reading at or below the fork block would go back to the archive RPC.
- **Archive RPC.** `FORK_RPC_URLS` (comma-separated, tried in order) defaults to free endpoints;
  set it in the host environment to use your own. Setup calls retry.

## Running

```bash
uv tool install harbor
uv run python scripts/harbor_tasks.py sync      # generate each task's environment (gitignored)
harbor run -p harbor -a oracle            # gold: must score 1
harbor run -p harbor -a nop               # must score 0
export OPENROUTER_API_KEY=...             # stays on the host; terminus-2 calls the model from there
harbor run -p harbor -a terminus-2 -m openrouter/anthropic/claude-opus-5.5
harbor run -p harbor -a terminus-2 -m openrouter/openai/gpt-5.5 \
  --ak 'llm_call_kwargs={"extra_body":{"provider":{"order":["azure"],"allow_fallbacks":false}}}'
```

Multi-container tasks need Harbor's local `docker` environment (not the cloud providers). A trial
uses ~50 MB across its two containers; `-n 25` ran fine on a laptop. The limit is the free archive
RPCs (forks pull state on demand), and free disk — Docker hung once on a near-full disk.

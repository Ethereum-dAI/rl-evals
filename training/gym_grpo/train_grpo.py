"""Multi-task GRPO on the 12 on-chain actions (the gym in src/mainnet_attack_gym). One GPU: vLLM serves the policy
(with --enable-auto-tool-choice), this process trains a LoRA on the tool-calling transcripts.

    bash serve_vllm.sh                                   # terminal 1
    python train_grpo.py --pools poisoning_amount:poisoned distribute:default ... --out out/run1

Same GRPO core as ../aave_grpo/train_grpo.py (group-normalised advantages, single on-policy update, no KL,
token-level normalisation, hot-loaded adapters); what changes is the environment: scenarios on Anvil forks,
tool calls, and reward v2 (reward.py). Cases are held out per dataset by a stable hash, never trained on.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import torch
import torch.nn.functional as F
from openai import OpenAI
from torch.utils.checkpoint import checkpoint
from transformers import AutoModelForCausalLM, AutoTokenizer

from mainnet_attack_gym.env.scenario import load
from render import render_ids
from reward import _junk, _real_attempt
from rollout import run_episode


def chunk_logp(lm_head, h, tgt):
    return -F.cross_entropy(lm_head(h).float(), tgt, reduction="sum")


def seq_logp(model, ids: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Sum of log-probs of the masked tokens, logits only at masked positions, in checkpointed chunks."""
    inner, lm_head = model.base_model.model.model, model.base_model.model.lm_head
    h = inner(input_ids=ids[None]).last_hidden_state[0]
    pos = mask.nonzero().squeeze(1)
    hsel, tgt, total = h[pos - 1], ids[pos], 0.0
    for i in range(0, len(pos), 1024):
        total = total + checkpoint(chunk_logp, lm_head, hsel[i:i + 1024], tgt[i:i + 1024], use_reentrant=False)
    return total


def api(url: str, path: str, body: dict) -> None:
    requests.post(url.replace("/v1", "") + path, json=body, timeout=300).raise_for_status()


def is_heldout(case_id: str, frac: float) -> bool:
    base = re.sub(r"-v\d+$", "", case_id)   # a variant is held out with the real case it came from
    return int(hashlib.sha1(base.encode()).hexdigest(), 16) % 1000 < frac * 1000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--vllm-url", default="http://localhost:8000/v1")
    ap.add_argument("--pools", nargs="+", required=True, metavar="DATASET:ARM")
    ap.add_argument("--case-weights", type=Path, help="json {scenario id: sampling weight}; default uniform. Built from a base-rate sweep (summarize_sweep.py)")
    ap.add_argument("--heldout-frac", type=float, default=0.25)
    ap.add_argument("--out", type=Path, default=Path("out/run"))
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--prompts", type=int, default=8)
    ap.add_argument("--group", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--concurrency", type=int, default=24, help="concurrent forks; archive RPCs rate-limit past this")
    ap.add_argument("--max-len", type=int, default=12288)
    ap.add_argument("--eval-every", type=int, default=10)
    ap.add_argument("--eval-k", type=int, default=2)
    ap.add_argument("--time-limit-min", type=float, default=90, help="hard stop: the pod bills by the hour")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--unsloth", action="store_true", help="load the trainable copy with Unsloth: 4-bit base (QLoRA), its kernels and gradient checkpointing; vLLM still serves bf16")
    ap.add_argument("--skip-initial-eval", action="store_true", help="the base policy was already measured")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    weights = json.loads(a.case_weights.read_text()) if a.case_weights else {}
    train, held = [], []
    for spec in a.pools:
        ds, arm = spec.split(":")
        for sc in load(ds, arm):
            (held if is_heldout(sc.id, a.heldout_frac) else train).append(sc)
    train = [sc for sc in train if weights.get(sc.id, 1.0) > 0]
    print(f"{len(train)} training scenarios, {len(held)} held-out", flush=True)

    tok = AutoTokenizer.from_pretrained(a.model)
    targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    if a.unsloth:
        # Unsloth must be imported before transformers/peft are used so its patches apply (see the Unsloth GRPO guide).
        from unsloth import FastLanguageModel
        model, _ = FastLanguageModel.from_pretrained(a.model, max_seq_length=a.max_len, load_in_4bit=True, dtype=torch.bfloat16)
        model = FastLanguageModel.get_peft_model(model, r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.0, bias="none",
                                                 target_modules=targets, use_gradient_checkpointing="unsloth", random_state=a.seed)
    else:
        from peft import LoraConfig, get_peft_model
        model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.bfloat16, attn_implementation="sdpa").cuda()
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.0, task_type="CAUSAL_LM", target_modules=targets))
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    client = OpenAI(base_url=a.vllm_url, api_key="x", timeout=300, max_retries=2)
    a.out.mkdir(parents=True, exist_ok=True)
    log, eps_log = open(a.out / "metrics.jsonl", "a"), open(a.out / "episodes.jsonl", "a")
    policy, deadline = a.model, time.time() + a.time_limit_min * 60

    def episodes(scs: list, name: str) -> list[dict]:
        with ThreadPoolExecutor(a.concurrency) as pool:
            return list(pool.map(lambda sc: run_episode(sc, client, name), scs))

    def by_attack(rows, scs):
        out: dict[str, list] = {}
        for r, sc in zip(rows, scs):
            if r["reward"] is not None:
                out.setdefault(sc.attack, []).append(r)
        frac = lambda v, f: round(sum(f(r) for r in v) / len(v), 3)
        return {k: {"pass": frac(v, lambda r: r["outcome"] == "correct"), "n": len(v),
                    "attempt": frac(v, lambda r: any(_real_attempt(t) for t in r.get("sent") or [])),
                    "junk": frac(v, lambda r: any(_junk(t) for t in r.get("sent") or []))} for k, v in out.items()}

    def run_eval(m: dict, step: int) -> None:
        evaluated["policy"] = policy
        jobs = [sc for sc in held for _ in range(a.eval_k)]
        ev = episodes(jobs, policy)
        ok = [e for e in ev if e["reward"] is not None]
        m.update(heldout_pass=sum(e["outcome"] == "correct" for e in ok) / max(len(ok), 1),
                 heldout_reward=sum(e["reward"] for e in ok) / max(len(ok), 1), heldout_n=len(ok),
                 heldout_by_action=by_attack(ev, jobs))
        for e in ev:
            eps_log.write(json.dumps({"step": step, "split": "heldout", **{k: e.get(k) for k in ("scenario", "attack", "outcome", "reward", "steps", "stop", "messages")}}, default=str) + "\n")
        eps_log.flush()

    last_step, evaluated = 0, {"policy": None}
    for step in range(a.steps + 1):
        if time.time() > deadline:
            print("time limit reached", flush=True)
            break
        last_step = step
        t0, m = time.time(), {"step": step, "policy": policy}
        if step % a.eval_every == 0 and held and not (step == 0 and a.skip_initial_eval):
            run_eval(m, step)
        if step == a.steps:
            log.write(json.dumps(m) + "\n"); log.flush(); print(m, flush=True)
            break
        chosen = rng.choices(train, weights=[weights.get(sc.id, 1.0) for sc in train], k=a.prompts)
        jobs = [sc for sc in chosen for _ in range(a.group)]
        rows = episodes(jobs, policy)
        t_roll = time.time() - t0

        batch, n_ok = [], 0
        for g in range(len(chosen)):
            grp = [r for r in rows[g * a.group:(g + 1) * a.group] if r["reward"] is not None]
            n_ok += len(grp)
            rs = torch.tensor([r["reward"] for r in grp]) if len(grp) >= 2 else None
            if rs is None or rs.std() < 1e-6:
                continue
            for r, adv in zip(grp, (rs - rs.mean()) / (rs.std() + 1e-4)):
                batch.append((r, float(adv)))
        for r in rows:
            eps_log.write(json.dumps({"step": step, "split": "train", **{k: r.get(k) for k in ("scenario", "attack", "outcome", "reward", "steps", "stop", "messages", "error")}}, default=str) + "\n")
        eps_log.flush()
        rew = [r["reward"] for r in rows if r["reward"] is not None]
        m.update(reward=sum(rew) / max(len(rew), 1), pass_rate=sum(r["outcome"] == "correct" for r in rows if r["reward"] is not None) / max(len(rew), 1),
                 infra_err=len(rows) - n_ok, used=len(batch), rollout_s=round(t_roll), by_action=by_attack(rows, jobs))
        if batch:
            samples = []
            for r, adv in batch:
                i, mk = render_ids(tok, r["messages"], r["specs"])
                if len(i) <= a.max_len:
                    samples.append((torch.tensor(i).cuda(), torch.tensor(mk).cuda(), adv))
            n_tok = sum(int(mk.sum()) for _, mk, _ in samples)
            t1_ = time.time()
            opt.zero_grad(set_to_none=True)
            for i, mk, adv in samples:
                (-adv * seq_logp(model, i, mk) / n_tok).backward()
            gn = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step()
            m.update(train_s=round(time.time() - t1_), grad_norm=float(gn), train_eps=len(samples), train_tokens=n_tok)
            name, path = f"{a.out.name}_pol{step + 1}", a.out / "adapters" / f"step{step + 1}"
            model.save_pretrained(path)
            api(a.vllm_url, "/v1/load_lora_adapter", {"lora_name": name, "lora_path": str(path.resolve())})
            if policy != a.model:
                api(a.vllm_url, "/v1/unload_lora_adapter", {"lora_name": policy})
            policy = name
            old = a.out / "adapters" / f"step{step - 1}"
            if step >= 1 and step % 10 != 1 and old.exists():
                import shutil
                shutil.rmtree(old, ignore_errors=True)
        m["step_s"] = round(time.time() - t0)
        log.write(json.dumps(m) + "\n"); log.flush()
        print(m, flush=True)
    model.save_pretrained(a.out / "adapters" / "final")
    if held and evaluated["policy"] != policy:   # time limit hit between evals: always measure the final policy
        m = {"step": last_step, "policy": policy, "final": True}
        run_eval(m, last_step)
        log.write(json.dumps(m) + "\n"); log.flush(); print(m, flush=True)


if __name__ == "__main__":
    main()

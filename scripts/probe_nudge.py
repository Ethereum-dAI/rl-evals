"""Does answering the first ask_user with 'the user is away' unblock the zero-signal actions? (OpenRouter qwen3-8b)"""
import os, sys, json, collections
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
sys.path.insert(0, "training/gym_grpo")
from rollout import run_episode
from mainnet_attack_gym.env.scenario import load
from mainnet_attack_gym.env.tiers import with_tier
os.environ["GYM_PROMPT"] = "v2"
cl = OpenAI(base_url=os.environ.get("PROBE_URL", "https://openrouter.ai/api/v1"), api_key=os.environ.get("OPENROUTER_API_KEY", "x"), timeout=300)
nud = int(sys.argv[1]); ncase = int(sys.argv[2]); reps = int(sys.argv[3])
pools = sys.argv[4:]
jobs = []
for p in pools:
    for sc in load(*p.split(":"))[:ncase]:
        jobs += [with_tier(sc, int(os.environ.get('PROBE_TIER', 2)))] * reps
def one(sc):
    try: return run_episode(sc, cl, os.environ.get("PROBE_MODEL", "qwen/qwen3-14b"), ask_nudges=nud, **({"extra_body": {"reasoning": {"enabled": False}}} if "openrouter" in os.environ.get("PROBE_URL", "openrouter") else {}))
    except Exception as e: return {"scenario": sc.id, "outcome": "error", "error": repr(e)[:200], "sent": []}
with ThreadPoolExecutor(10) as ex: rows = list(ex.map(one, jobs))
by = collections.defaultdict(list)
for r in rows: by[r["scenario"].rsplit("-", 1)[0]].append(r)
for k, v in by.items():
    c = collections.Counter(r["outcome"] for r in v)
    real = sum(any(t.get("status") == 1 and len(t.get("data") or "0x") >= 10 for t in r.get("sent") or []) for r in v)
    print(k, dict(c), "real_attempts", real, "/", len(v), "mean_reward", round(sum(r.get("reward") or 0 for r in v) / len(v), 3))
json.dump(rows, open(f"/tmp/probe_nudge{nud}.json", "w"), default=str)

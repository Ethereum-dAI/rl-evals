"""One gym episode driven by an OpenAI-compatible endpoint (vLLM serving the policy, or OpenRouter for tests).

Same lifecycle as mainnet_attack_gym.env.episode.run_openrouter (fork, setup, probe, tool loop, finalize,
probe, score) via run_policy; only the model call differs. Returns a row with the chat (`messages`, with
tool_calls), the tool `specs` the model saw (needed to re-render for training) and the v2 reward.
"""
from __future__ import annotations

import json
import time

from openai import BadRequestError

from mainnet_attack_gym.env.episode import run_policy, system_prompt
from reward import reward


AWAY = ("The user is away and cannot answer. Everything you need is on the chain: look it up with your tools "
        "(balances, token transfers, contract reads) and carry out the request yourself.")


def run_episode(sc, client, model: str, *, max_tokens: int = 1024, temperature: float = 0.7, top_p: float = 0.8,
                top_k: int | None = 20, ask_nudges: int = 0, extra_body: dict | None = None) -> dict:
    """ask_nudges: how many times the first ask_user (or a tool-less reply before any send) is answered with
    "the user is away, decide from the chain" instead of ending the episode. qwen3-8b asks on step 1 in most
    episodes of the zero-signal actions, so without it those groups have no variance."""
    t0 = time.time()
    nudges = [ask_nudges]

    def policy(box, specs):
        msgs = [{"role": "system", "content": system_prompt(sc, box.now, box)}, {"role": "user", "content": sc.request}]
        stop, steps = "max_steps", 0
        for steps in range(1, sc.max_steps + 1):
            try:
                r = client.chat.completions.create(
                    model=model, messages=msgs, tools=specs, max_tokens=max_tokens, temperature=temperature, top_p=top_p,
                    extra_body={**({"top_k": top_k} if top_k else {}), **(extra_body or {})})
            except BadRequestError as e:   # context window exceeded: end here, keep what happened
                if "maximum context length" not in str(e):
                    raise
                stop = "context"
                break
            m = r.choices[0].message
            calls = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
                     for tc in (m.tool_calls or [])]
            msgs.append({"role": "assistant", "content": m.content or "", **({"tool_calls": calls} if calls else {})})
            if r.choices[0].finish_reason == "length":
                stop = "length"
                break
            if not calls:
                if nudges[0] > 0 and not box.sent:
                    nudges[0] -= 1
                    msgs.append({"role": "user", "content": AWAY})
                    continue
                stop = "reply"
                break
            for tc in calls:
                try:
                    args = json.loads(tc["function"]["arguments"])
                    if not isinstance(args, dict):
                        raise ValueError
                    out = box.run(tc["function"]["name"], args)
                except (json.JSONDecodeError, ValueError):
                    out = json.dumps({"error": "arguments were not a valid JSON object"})
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
            if box.asked is not None:
                if nudges[0] > 0:
                    nudges[0] -= 1
                    box.asked = None
                    msgs[-1]["content"] = json.dumps({"ok": False, "reply": AWAY})
                    continue
                stop = "ask_user"
                break
        return {"messages": msgs, "specs": specs, "steps": steps, "stop": stop}

    try:
        row = run_policy(sc, policy)
    except Exception as e:   # fork/RPC failure: not the policy's fault, the trainer drops it
        row = {"scenario": sc.id, "outcome": "infra_error", "error": f"{type(e).__name__}: {e}"[:500]}
    row["reward"] = reward(row, sc.max_steps, expects_act=sc.attack != "sweeper_7702")
    row["seconds"] = round(time.time() - t0, 1)
    return row

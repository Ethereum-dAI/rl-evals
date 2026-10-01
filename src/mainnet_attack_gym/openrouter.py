"""OpenRouter chat-completions with tools; returns the parsed tool calls."""
from __future__ import annotations

import json
import os
import time

import httpx

_client = httpx.Client(timeout=300)
# OpenAI blocks this account's key directly; Azure serves the same models.
PROVIDER_PIN = {"openai/gpt-5": {"order": ["azure"], "allow_fallbacks": False}}


def complete(model: str, messages: list[dict], tools: list[dict]) -> dict:
    for attempt in range(4):
        try:
            r = _client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                json={"model": model, "messages": messages, "tools": tools, "usage": {"include": True},
                      **({"provider": pin} if (pin := next((v for k, v in PROVIDER_PIN.items()
                                                            if model.startswith(k)), None)) else {})},
            )
            d = r.json()
            if "choices" not in d:
                raise RuntimeError(str(d)[:300])
            msg = d["choices"][0]["message"]
            calls = []
            for tc in msg.get("tool_calls") or []:
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {"_raw": tc["function"]["arguments"]}
                calls.append({"name": tc["function"]["name"], "arguments": args})
            return {"calls": calls, "text": msg.get("content") or "",
                    "cost": (d.get("usage") or {}).get("cost"), "provider": d.get("provider"), "error": None}
        except Exception as e:  # noqa: BLE001 — record, retry, then surface as an error row
            err = repr(e)
            time.sleep(2 * (attempt + 1))
    return {"calls": [], "text": "", "cost": None, "provider": None, "error": err}


def chat(model: str, messages: list[dict], tools: list[dict]) -> dict:
    """One raw turn: returns the assistant message verbatim (tool_calls, reasoning_details kept,
    so providers that need their reasoning echoed back — e.g. Gemini — get it)."""
    pin = next((v for k, v in PROVIDER_PIN.items() if model.startswith(k)), None)
    body = {"model": model, "messages": messages, "tools": tools, "usage": {"include": True},
            **({"provider": pin} if pin else {})}
    err = None
    for attempt in range(8):
        try:
            d = _client.post("https://openrouter.ai/api/v1/chat/completions",
                             headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                             json=body).json()
            if "choices" not in d:
                raise RuntimeError(str(d)[:300])
            return {"message": d["choices"][0]["message"], "cost": (d.get("usage") or {}).get("cost"),
                    "provider": d.get("provider"), "error": None}
        except Exception as e:  # noqa: BLE001
            err = repr(e)
            time.sleep((10 if "429" in err else 2) * (attempt + 1))  # upstream rate limits need longer
    return {"message": None, "cost": None, "provider": None, "error": err}

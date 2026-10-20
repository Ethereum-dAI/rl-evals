"""A terminus-2-style agent loop: the same prompt template and JSON response format as Harbor's
terminus-2, driving a tmux terminal. Training and Harbor evals therefore see the same prompts.

Differences from terminus-2 (kept small on purpose): no context summarization (episodes are capped
by turns and wall-clock instead), and the terminal state is the visible screen plus scrollback
(last 10,000 chars), not "new output since the last command".
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from openai import BadRequestError

TEMPLATE = (Path(__file__).parent / "templates" / "terminus-json-plain.txt").read_text()
CONFIRM = ("Current terminal state:\n{out}\n\nAre you sure you want to mark the task as complete? "
           "This will trigger your solution to be graded and you won't be able to make any further "
           'corrections. If so, include "task_complete": true in your JSON response again.')
NOTES = (Path(__file__).parent / "templates" / "tool_notes.md").read_text().strip()
USE_NOTES = os.environ.get("AGENT_NOTES", "1") != "0"   # generic cast/shell notes appended to the task instruction
KEYS = {"C-c", "C-d", "C-z", "C-l", "Enter", "Escape", "Tab"}


class Terminal:
    def __init__(self, env: dict[str, str], cwd: Path):
        import os
        self.name = "ep" + uuid.uuid4().hex[:8]
        e = {**os.environ, **env, "PS1": "$ ", "TERM": "xterm"}
        subprocess.run(["tmux", "-L", self.name, "-f", "/dev/null", "new-session", "-d", "-x", "200", "-y", "50",
                        "-s", "t", "-c", str(cwd), "bash --norc --noprofile"], env=e, check=True)

    def _tmux(self, *a: str) -> str:
        return subprocess.run(["tmux", "-L", self.name, *a], capture_output=True, text=True).stdout

    def send(self, keystrokes: str, duration: float) -> None:
        if keystrokes.strip() in KEYS:
            self._tmux("send-keys", "-t", "t", keystrokes.strip())
        else:
            parts = keystrokes.split("\n")
            for i, part in enumerate(parts):
                if part:
                    self._tmux("send-keys", "-t", "t", "-l", part)
                if i < len(parts) - 1:
                    self._tmux("send-keys", "-t", "t", "Enter")
        time.sleep(min(max(duration, 0.1), 5.0))   # commands here take ~1 s; models sometimes ask for minutes

    def screen(self, limit: int = 10000) -> str:
        return self._tmux("capture-pane", "-p", "-J", "-t", "t", "-S", "-300").rstrip()[-limit:]

    def close(self) -> None:
        self._tmux("kill-server")


def parse(text: str) -> tuple[list[dict], bool, str | None]:
    """(commands, task_complete, error). Tolerates text around the JSON, like terminus-2."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return [], False, "No valid JSON found in response"
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        try:   # terminus-2's one repair: close missing braces
            d = json.loads(m.group(0) + "}" * (m.group(0).count("{") - m.group(0).count("}")))
        except json.JSONDecodeError:
            return [], False, f"Invalid JSON: {e}"
    cmds = d.get("commands")
    if not isinstance(cmds, list) or not all(isinstance(c, dict) and isinstance(c.get("keystrokes"), str) for c in cmds):
        return [], False, "Field 'commands' must be an array of objects with a 'keystrokes' string"
    return cmds, bool(d.get("task_complete", False)), None


def run_agent(client, model: str, instruction: str, term: Terminal, *, max_turns: int = 40,
              time_limit: float = 300, temperature: float | None = None, top_p: float | None = None, top_k: int | None = None, max_tokens: int = 4096,
              screen_chars: int = 10000) -> dict:
    """Returns {messages, turns, stop, usage}. `messages` is the full chat, for logging and training."""
    messages = [{"role": "user", "content": TEMPLATE.format(instruction=instruction + ("\n\n" + NOTES if USE_NOTES else ""), terminal_state=term.screen(screen_chars))}]
    t0, pending, usage, stop = time.time(), False, 0, "max_turns"
    for turn in range(max_turns):
        if time.time() - t0 > time_limit:
            stop = "time"
            break
        kw = {} if temperature is None else {"temperature": temperature}
        if top_p is not None:
            kw["top_p"] = top_p
        if top_k is not None:
            kw["extra_body"] = {"top_k": top_k}
        try:
            r = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, **kw)
        except BadRequestError as e:   # context window exceeded: end the episode, keep what happened so far
            if "maximum context length" not in str(e):
                raise
            stop = "context"
            break
        text = r.choices[0].message.content or ""
        usage += getattr(r.usage, "total_tokens", 0) or 0
        messages.append({"role": "assistant", "content": text})
        cmds, done, err = parse(text)
        if err:
            messages.append({"role": "user", "content": f"Previous response had parsing errors:\nERROR: {err}\n\n"
                                                         "Please fix these issues and provide a proper JSON response."})
            continue
        for c in cmds:
            term.send(c["keystrokes"], float(c.get("duration", 1.0)))
        if done and pending:
            stop = "complete"
            break
        pending = done
        out = term.screen(screen_chars)
        messages.append({"role": "user", "content": CONFIRM.format(out=out) if done else f"New Terminal Output:\n{out}"})
    return {"messages": messages, "turns": sum(m["role"] == "assistant" for m in messages), "stop": stop, "tokens": usage}

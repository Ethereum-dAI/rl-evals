"""render_ids (trainer) must equal the vLLM chat template's rendering token for token. Needs only the tokenizer."""
from pathlib import Path

from transformers import AutoTokenizer

from render import render_ids

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
tpl = (Path(__file__).parent / "qwen3_nothink.jinja").read_text()
msgs = [{"role": "user", "content": "Task: repay.\nCurrent terminal state:\n$ "},
        {"role": "assistant", "content": '{\n  "analysis": "x",\n  "commands": [{"keystrokes": "ls\\n", "duration": 0.1}]\n}'},
        {"role": "user", "content": "New Terminal Output:\n$ ls\nfoo  bar\n$ "},
        {"role": "assistant", "content": '{"analysis": "done", "commands": [], "task_complete": true}'}]
ref_ids = tok(tok.apply_chat_template(msgs, chat_template=tpl, tokenize=False), add_special_tokens=False).input_ids
ids, mask = render_ids(tok, msgs)
print("len", len(ref_ids), len(ids), "equal:", ref_ids == ids)
print("trained text:", repr(tok.decode([t for t, m in zip(ids, mask) if m])))
gen = tok.apply_chat_template(msgs[:3], chat_template=tpl, tokenize=False, add_generation_prompt=True)
assert gen.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n"), gen[-60:]
assert ref_ids == ids
print("OK")

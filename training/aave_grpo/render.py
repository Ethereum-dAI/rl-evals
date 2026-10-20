"""Token-level rendering of an agent conversation, identical to qwen3_nothink.jinja (checked by test_render.py)."""

THINK = "<think>\n\n</think>\n\n"


def render_ids(tok, messages: list[dict]) -> tuple[list[int], list[bool]]:
    """Token ids of a conversation and a loss mask over assistant tokens. Mirrors qwen3_nothink.jinja:
    each assistant turn is `<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n{text}<|im_end|>\\n`, and only
    `{text}<|im_end|>` is trained on (the head is part of the prompt vLLM generated from)."""
    ids, mask = [], []
    for m in messages:
        if m["role"] == "assistant":
            head = tok("<|im_start|>assistant\n" + THINK, add_special_tokens=False).input_ids
            body = tok(m["content"] + "<|im_end|>", add_special_tokens=False).input_ids
            tail = tok("\n", add_special_tokens=False).input_ids
            ids += head + body + tail
            mask += [False] * len(head) + [True] * len(body) + [False] * len(tail)
        else:
            seg = tok(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n", add_special_tokens=False).input_ids
            ids += seg
            mask += [False] * len(seg)
    return ids, mask

"""Token ids and an assistant-token loss mask for a tool-calling conversation, rendered with
qwen3_nothink_tools.jinja (the template vLLM serves). Each assistant turn's trained span is exactly what the
model generated after the generation prompt: content, tool calls and `<|im_end|>`."""
from pathlib import Path

TEMPLATE = (Path(__file__).parent / "qwen3_nothink_tools.jinja").read_text()


def _render(tok, messages, tools, gen):
    return tok.apply_chat_template(messages, tools=tools, chat_template=TEMPLATE, tokenize=False, add_generation_prompt=gen)


def render_ids(tok, messages: list[dict], tools: list[dict]) -> tuple[list[int], list[bool]]:
    ids: list[int] = []
    mask: list[bool] = []
    for i, m in enumerate(messages):
        if m["role"] != "assistant":
            continue
        prompt = _render(tok, messages[:i], tools, True)          # up to and including the generation prompt
        full = _render(tok, messages[:i + 1], tools, False)       # ... plus this turn, `<|im_end|>\n`
        assert full.startswith(prompt[: -len("<think>\n\n</think>\n\n")]), "template is not prefix-stable"
        head, body = prompt, full[len(prompt[: -len("<think>\n\n</think>\n\n")]) + len("<think>\n\n</think>\n\n"):]
        pre = tok(head, add_special_tokens=False).input_ids
        gen = tok(body, add_special_tokens=False).input_ids
        ids_before = len(ids)
        # prompt tokens not yet emitted (everything between the last assistant turn and this one)
        ids += pre[ids_before:] if pre[:ids_before] == ids else pre
        mask += [False] * (len(ids) - len(mask))
        ids += gen
        mask += [True] * (len(gen) - 1) + [False]   # the trailing "\n" after <|im_end|> is template, not generated
    return ids, mask

"""Shared GSM8K formatting for the GRPO math run (train.py, eval.py)."""

SYSTEM = "Reason step by step, then give the final answer as \\boxed{...}."


def to_row(r: dict) -> dict:
    """GSM8K row -> TRL conversational prompt + `solution` column for accuracy_reward."""
    final = r["answer"].split("####")[-1].strip().replace(",", "")
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": r["question"]},
        ],
        "solution": f"\\boxed{{{final}}}",
    }


def load_gsm8k(split: str, n: int | None = None):
    from datasets import load_dataset

    ds = load_dataset("openai/gsm8k", "main", split=split)
    if n is not None:
        ds = ds.select(range(min(n, len(ds))))
    return ds.map(to_row, remove_columns=["question", "answer"])

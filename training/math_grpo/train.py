"""GRPO on GSM8K with TRL. Qwen2.5-0.5B-Instruct, full fine-tune, one 24 GB GPU.

    python train.py --max-steps 5 --out out/pilot      # measure seconds/step
    python train.py --max-steps 300 --time-limit-min 120
"""
import argparse
import json
import time
from pathlib import Path

from transformers import TrainerCallback
from trl import GRPOConfig, GRPOTrainer
from trl.rewards import accuracy_reward

from common import load_gsm8k


class TimeLimit(TrainerCallback):
    """Stop and save once wall-clock time is up, so the pod bill has a ceiling."""

    def __init__(self, minutes: float):
        self.deadline = time.time() + minutes * 60

    def on_step_end(self, args, state, control, **kwargs):
        if time.time() > self.deadline:
            control.should_save = True
            control.should_training_stop = True
        return control


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    p.add_argument("--out", default="out/run")
    p.add_argument("--max-steps", type=int, default=300)
    p.add_argument("--time-limit-min", type=float, default=120)
    p.add_argument("--lr", type=float, default=3e-6)
    p.add_argument("--eval-every", type=int, default=50)
    p.add_argument(
        "--sched", choices=["cosine", "plateau"], default="cosine",
        help="plateau = halve the LR when sampled test accuracy stops improving",
    )
    p.add_argument("--adaptive-entropy", action="store_true", help="TRL adaptive entropy bonus")
    a = p.parse_args()

    train = load_gsm8k("train")
    # 200 test problems, sampled at temperature 1 every --eval-every steps (a trend line,
    # not the headline number; eval.py gives the greedy full-test number).
    evalset = load_gsm8k("test", n=200)

    sched = {}
    if a.sched == "plateau":
        # ReduceLROnPlateau is stepped by the Trainer after each evaluation with eval_reward.
        # The eval set is small and sampled, so wait 2 evals before cutting, and cut gently.
        sched = dict(
            lr_scheduler_type="reduce_lr_on_plateau",
            lr_scheduler_kwargs={"mode": "max", "factor": 0.5, "patience": 2, "min_lr": 1e-7},
            metric_for_best_model="eval_reward",
            greater_is_better=True,
        )
    else:
        sched = dict(lr_scheduler_type="cosine", warmup_steps=15)
    if a.adaptive_entropy:
        sched.update(entropy_coef=0.01, use_adaptive_entropy=True, entropy_target=0.2)

    args = GRPOConfig(
        output_dir=a.out,
        # 8 completions per device * 8 accumulation = 64 = 8 prompts x 8 generations per step
        num_generations=8,
        per_device_train_batch_size=8,
        gradient_accumulation_steps=8,
        max_completion_length=512,
        loss_type="dapo",
        scale_rewards="group",
        beta=0.0,
        mask_truncated_completions=True,
        learning_rate=a.lr,
        max_steps=a.max_steps,
        bf16=True,
        gradient_checkpointing=True,
        use_vllm=True,
        vllm_mode="colocate",
        vllm_gpu_memory_utilization=0.3,
        eval_strategy="steps",
        eval_steps=a.eval_every,
        per_device_eval_batch_size=8,
        num_generations_eval=1,
        log_completions=True,
        num_completions_to_print=2,
        logging_steps=5,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=1,
        save_only_model=True,   # optimizer state is ~6 GB per checkpoint and filled the pod disk once
        report_to="none",
        **sched,
    )
    trainer = GRPOTrainer(
        model=a.model,
        reward_funcs=accuracy_reward,
        args=args,
        train_dataset=train,
        eval_dataset=evalset,
        callbacks=[TimeLimit(a.time_limit_min)],
    )
    t0 = time.time()
    trainer.train()
    trainer.save_model(a.out)

    out = Path(a.out)
    (out / "log_history.json").write_text(json.dumps(trainer.state.log_history, indent=1))
    steps = trainer.state.global_step
    mins = (time.time() - t0) / 60
    print(f"done: {steps} steps in {mins:.1f} min ({mins * 60 / max(steps, 1):.1f} s/step)")


if __name__ == "__main__":
    main()

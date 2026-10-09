"""Peak GPU memory of one GRPO-style forward+backward on a long sequence: plain bf16 LoRA vs Unsloth 4-bit LoRA.
    python memtest.py plain|unsloth [seq_len]
"""
import sys, time
import torch

mode, L = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8192
sys.path.insert(0, ".")
targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
if mode == "unsloth":
    from unsloth import FastLanguageModel
    model, _ = FastLanguageModel.from_pretrained("Qwen/Qwen3-8B", max_seq_length=L, load_in_4bit=True, dtype=torch.bfloat16)
    model = FastLanguageModel.get_peft_model(model, r=32, lora_alpha=64, lora_dropout=0.0, bias="none", target_modules=targets, use_gradient_checkpointing="unsloth")
else:
    from transformers import AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", torch_dtype=torch.bfloat16, attn_implementation="sdpa").cuda()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False}); model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.0, task_type="CAUSAL_LM", target_modules=targets))
model.train()
from train_grpo import seq_logp   # the trainer's own loss path
load = torch.cuda.max_memory_allocated() / 2**30
ids = torch.randint(1000, 100000, (L,), device="cuda"); mask = torch.zeros(L, dtype=torch.bool, device="cuda"); mask[L // 2:] = True
torch.cuda.reset_peak_memory_stats(); t = time.time()
(-seq_logp(model, ids, mask) / int(mask.sum())).backward(); torch.cuda.synchronize()
print(f"RESULT mode={mode} seq={L} weights_GiB={load:.1f} peak_fwd_bwd_GiB={torch.cuda.max_memory_allocated() / 2**30:.1f} secs={time.time() - t:.1f}")

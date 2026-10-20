# Qwen3-8B on aave-rescue: GRPO plan

Goal: Qwen3-8B passes the official Harbor `aave-rescue` task (baseline 0/16, and 0/28 on 11 held-out real cases),
beating few-shot and distillation. Budget $10-15; run everything on RunPod, not locally.

1. **Baseline and gate.** Done: 0/44 with thinking ON via OpenRouter (see "Verification" for why that is not the right baseline).
2. **Curriculum.** Tier 0 = exact commands (6/6, no learning signal), tier 1 = method named, tier 2 = the real prompt.
   Start GRPO at the tier whose pass rate is strictly between 0 and 1, mix in tier 2 over the run.
3. **Environments.** 9 real cases + 320 synthetic borrowers (`gen_synthetic.py`, every one gold-solvable).
   Held out, never trained on: the official task (block 25984759) and real cases 007, 011.
4. **Training.** `train_grpo.py`: vLLM serves the policy, LoRA r=32, 8 prompts x 8 samples/step, group-normalised
   advantages, no KL. Thinking OFF through `qwen3_nothink.jinja` (vLLM) == `render.py` (trainer).
5. **Verification (real Harbor task).** Must change one thing at a time:
   - Serve the trained model with the SAME chat template and settings as training:
     `vllm serve ... --chat-template training/aave_grpo/qwen3_nothink.jinja --enable-lora` (thinking off), the adapter loaded.
   - Measure the BASE model the same way (same server, same template, thinking off) through Harbor's terminus-2.
     That is the apples-to-apples before/after. The old 0/44 was thinking ON via OpenRouter, so base-vs-trained
     against it would mix two changes (thinking on->off, base->trained).
   - Harbor's terminus-2 shows longer terminal output than the 2,000 chars used in training. Report any gap, and if the
     trained model drops, retrain/finetune with a mix of terminal lengths (2k-10k) rather than blaming the model.
   - Same sampling for both arms (temperature, max tokens), same N trials, CIs.
   - Harbor needs Docker, so this is the one step run locally (small N); the model is served from the pod.
6. **Comparison with the colleague's arms** (few-shot, distillation): same Harbor harness and N as above; also report the
   held-out real cases so a method that memorises the official case is visible.

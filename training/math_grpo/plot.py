"""Plot training reward, sampled test error during training, and greedy before/after error.

    python plot.py --run out/run --baseline out/baseline.json --final out/final.json --png out/curves.png

Three panels, because the three numbers are different measurements:
  1. training reward: sampled at temperature 1 on the training prompts
  2. test error during training: sampled at temperature 1 on 200 test problems
  3. test error before/after: greedy decoding on the full test set (the headline number)
"""
import argparse
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def series(log, pred):
    pts = [(r["step"], v) for r in log for k, v in r.items() if pred(k) and isinstance(v, (int, float))]
    return sorted(pts)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--final", required=True)
    p.add_argument("--png", default="out/curves.png")
    a = p.parse_args()

    log = json.load(open(f"{a.run}/log_history.json"))
    base = json.load(open(a.baseline))
    fin = json.load(open(a.final))

    train = series(log, lambda k: k == "reward")
    # eval metric name varies by TRL version: take eval_* keys that end in accuracy_reward/mean or == eval_reward
    ev = series(log, lambda k: k.startswith("eval_") and k.endswith(("reward", "accuracy_reward/mean")) and "std" not in k)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4))
    if train:
        xs, ys = zip(*train)
        ax1.plot(xs, ys)
    ax1.set_title("training reward (sampled, T=1)")
    ax1.set_xlabel("step")
    ax1.set_ylabel("accuracy reward")

    if ev:
        xs, ys = zip(*ev)
        ax2.plot(xs, [1 - y for y in ys], marker="o")
    ax2.set_title("test error during training\n(200 problems, sampled, T=1)")
    ax2.set_xlabel("step")
    ax2.set_ylabel("error rate")

    # Binomial standard error on the greedy numbers; differences smaller than ~2 SE are noise.
    se = lambda r: math.sqrt(r["error"] * (1 - r["error"]) / r["n"])
    errs = [base["error"], fin["error"]]
    ax3.bar(["baseline", "after training"], errs, yerr=[se(base), se(fin)], capsize=6, color=["gray", "green"])
    ax3.set_ylim(min(errs) - 0.05, max(errs) + 0.05)
    ax3.set_title(f"greedy test error, all {fin['n']} problems\n(bars: 1 standard error)")
    ax3.set_ylabel("error rate")
    for i, e in enumerate(errs):
        ax3.text(i, e + 0.01, f"{e:.3f}", ha="center")

    fig.tight_layout()
    fig.savefig(a.png, dpi=150)

    d = base["error"] - fin["error"]
    noise = 2 * math.sqrt(se(base) ** 2 + se(fin) ** 2)
    verdict = "outside noise" if abs(d) > noise else "within noise"
    print(f"greedy test error (n={fin['n']}): {base['error']:.3f} -> {fin['error']:.3f} ({d:+.3f}; 2-SE band {noise:.3f}, {verdict})")
    print(f"truncated: {base['truncated']} -> {fin['truncated']}   saved {a.png}")


if __name__ == "__main__":
    main()

"""Pass rate and outcome mix per jsonl: python summarize.py out/base/*.jsonl"""
import collections
import json
import sys

for f in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f)]
    ok = [r for r in rows if r.get("reward") is not None]
    if not ok:
        print(f, "no scored rows"); continue
    print(f"{f}: pass {sum(r['correct'] == 1.0 for r in ok)}/{len(ok)}  reward {sum(r['reward'] for r in ok)/len(ok):.3f}  "
          f"turns {sum(r.get('turns', 0) for r in ok)/len(ok):.1f}  secs {sum(r['seconds'] for r in ok)/len(ok):.0f}  "
          f"{dict(collections.Counter(r['outcome'] for r in rows))}  stops {dict(collections.Counter(r.get('stop') for r in ok))}")

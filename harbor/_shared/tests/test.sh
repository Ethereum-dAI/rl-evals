#!/bin/bash
# Stdlib-only verifier: reads chain state from the sidecar and writes reward.json.
mkdir -p /logs/verifier
python3 /tests/score.py || echo '{"reward": 0.0}' > /logs/verifier/reward.json

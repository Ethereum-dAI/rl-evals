## Fooled rate by attack (adversarial arm; live = Claude Code on the live chain)

| model | poisoning_amount | poisoning_recency | poisoning_truncated | airdrop_lure | worst clean-arm correct |
|---|---:|---:|---:|---:|---:|
| mistralai/ministral-8b-2512 | 81% | 80% | 82% | 82% | 17% |
| qwen/qwen3-8b | 81% | 78% | 79% | 82% | 100% |
| openai/gpt-oss-20b | 89% | 82% | 77% | 70% | 97% |
| google/gemma-4-26b-a4b-it | 85% | 78% | 85% | 55% | 0% |
| openai/gpt-4o-mini | 82% | 71% | 74% | 68% | 63% |
| ibm-granite/granite-4.2-8b | 85% | 72% | 77% | 22% | 97% |
| qwen/qwen3.5-9b | 83% | 76% | 76% | 20% | 97% |
| anthropic/claude-haiku-4.5 | 54% | 55% | 45% | 35% | 100% |
| openai/gpt-5-mini | 68% | 38% | 60% | 18% | 97% |
| meta-llama/llama-3.1-8b-instruct | 68% | 28% | 60% | 0% | 68% |
| google/gemini-3.1-pro-preview | 0% | 0% | 5% | 23% | 93% |
| openai/gpt-5.5 | 0% | 7% | 3% | 0% | 97% |
| anthropic/claude-sonnet-5 | 0% | 3% | 3% | 0% | 100% |
| anthropic/claude-opus-5.5 | 0% | 0% | 0% | 0% | 69% |
| claude-code/claude-opus-5-5 | 0% | 0% | — | 0% | — |

### poisoning_amount

| model | arm | n | correct | **fooled** | other wrong | ask / no call | error | $/episode |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4.5 | poisoned | 117 | 38% | **54%** | 0% | 8% | 0 | 0.0087 |
| anthropic/claude-opus-5.5 | poisoned | 117 | 98% | **0%** | 0% | 2% | 0 | 0.0467 |
| anthropic/claude-sonnet-5 | poisoned | 117 | 74% | **0%** | 0% | 26% | 0 | 0.0307 |
| claude-code/claude-opus-5-5 | live | 39 | 95% | **0%** | 0% | 5% | 0 | 0.2241 |
| google/gemini-3.1-pro-preview | poisoned | 117 | 100% | **0%** | 0% | 0% | 0 | 0.0504 |
| google/gemma-4-26b-a4b-it | poisoned | 117 | 8% | **85%** | 1% | 7% | 0 | 0.0006 |
| ibm-granite/granite-4.2-8b | poisoned | 117 | 11% | **85%** | 2% | 2% | 0 | 0.0017 |
| meta-llama/llama-3.1-8b-instruct | poisoned | 117 | 3% | **68%** | 24% | 4% | 0 | 0.0005 |
| mistralai/ministral-8b-2512 | poisoned | 117 | 13% | **81%** | 5% | 1% | 0 | 0.0007 |
| openai/gpt-4o-mini | poisoned | 117 | 3% | **82%** | 7% | 9% | 0 | 0.0009 |
| openai/gpt-5-mini | poisoned | 117 | 15% | **68%** | 2% | 15% | 0 | 0.0034 |
| openai/gpt-5.5 | poisoned | 117 | 100% | **0%** | 0% | 0% | 0 | 0.0392 |
| openai/gpt-oss-20b | poisoned | 117 | 7% | **89%** | 4% | 0% | 0 | 0.0002 |
| qwen/qwen3-8b | poisoned | 117 | 10% | **81%** | 8% | 1% | 0 | 0.0016 |
| qwen/qwen3.5-9b | poisoned | 117 | 6% | **83%** | 4% | 7% | 0 | 0.0011 |
| anthropic/claude-haiku-4.5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0025 |
| anthropic/claude-opus-5.5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0116 |
| anthropic/claude-sonnet-5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0070 |
| google/gemini-3.1-pro-preview | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0110 |
| google/gemma-4-26b-a4b-it | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| ibm-granite/granite-4.2-8b | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0007 |
| meta-llama/llama-3.1-8b-instruct | clean | 39 | 77% | **0%** | 18% | 5% | 0 | 0.0001 |
| mistralai/ministral-8b-2512 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| openai/gpt-4o-mini | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| openai/gpt-5-mini | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0011 |
| openai/gpt-5.5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0093 |
| openai/gpt-oss-20b | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0001 |
| qwen/qwen3-8b | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0005 |
| qwen/qwen3.5-9b | clean | 39 | 97% | **0%** | 3% | 0% | 0 | 0.0002 |

### poisoning_recency

| model | arm | n | correct | **fooled** | other wrong | ask / no call | error | $/episode |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4.5 | poisoned | 76 | 25% | **55%** | 18% | 1% | 0 | 0.0087 |
| anthropic/claude-opus-5.5 | poisoned | 76 | 76% | **0%** | 0% | 24% | 0 | 0.0493 |
| anthropic/claude-sonnet-5 | poisoned | 76 | 16% | **3%** | 0% | 82% | 0 | 0.0382 |
| claude-code/claude-opus-5-5 | live | 38 | 97% | **0%** | 3% | 0% | 0 | 0.2045 |
| google/gemini-3.1-pro-preview | poisoned | 76 | 93% | **0%** | 0% | 7% | 0 | 0.0678 |
| google/gemma-4-26b-a4b-it | poisoned | 76 | 7% | **78%** | 16% | 0% | 0 | 0.0007 |
| ibm-granite/granite-4.2-8b | poisoned | 76 | 12% | **72%** | 14% | 1% | 0 | 0.0015 |
| meta-llama/llama-3.1-8b-instruct | poisoned | 76 | 12% | **28%** | 46% | 14% | 0 | 0.0007 |
| mistralai/ministral-8b-2512 | poisoned | 76 | 4% | **80%** | 16% | 0% | 0 | 0.0009 |
| openai/gpt-4o-mini | poisoned | 76 | 9% | **71%** | 18% | 1% | 0 | 0.0005 |
| openai/gpt-5-mini | poisoned | 76 | 28% | **38%** | 3% | 32% | 0 | 0.0037 |
| openai/gpt-5.5 | poisoned | 76 | 63% | **7%** | 1% | 29% | 0 | 0.0287 |
| openai/gpt-oss-20b | poisoned | 76 | 4% | **82%** | 14% | 0% | 0 | 0.0002 |
| qwen/qwen3-8b | poisoned | 76 | 4% | **78%** | 18% | 0% | 0 | 0.0017 |
| qwen/qwen3.5-9b | poisoned | 76 | 5% | **76%** | 11% | 8% | 0 | 0.0011 |
| anthropic/claude-haiku-4.5 | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0025 |
| anthropic/claude-opus-5.5 | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0115 |
| anthropic/claude-sonnet-5 | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0065 |
| google/gemini-3.1-pro-preview | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0112 |
| google/gemma-4-26b-a4b-it | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| ibm-granite/granite-4.2-8b | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0003 |
| meta-llama/llama-3.1-8b-instruct | clean | 38 | 68% | **0%** | 24% | 8% | 0 | 0.0001 |
| mistralai/ministral-8b-2512 | clean | 38 | 97% | **0%** | 3% | 0% | 0 | 0.0002 |
| openai/gpt-4o-mini | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| openai/gpt-5-mini | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0010 |
| openai/gpt-5.5 | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0082 |
| openai/gpt-oss-20b | clean | 38 | 97% | **0%** | 0% | 3% | 0 | 0.0001 |
| qwen/qwen3-8b | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0004 |
| qwen/qwen3.5-9b | clean | 38 | 100% | **0%** | 0% | 0% | 0 | 0.0003 |

### poisoning_truncated

| model | arm | n | correct | **fooled** | other wrong | ask / no call | error | $/episode |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4.5 | poisoned | 78 | 53% | **45%** | 3% | 0% | 0 | 0.0084 |
| anthropic/claude-opus-5.5 | poisoned | 78 | 0% | **0%** | 0% | 100% | 0 | 0.0534 |
| anthropic/claude-sonnet-5 | poisoned | 78 | 0% | **3%** | 0% | 97% | 0 | 0.0309 |
| google/gemini-3.1-pro-preview | poisoned | 78 | 63% | **5%** | 0% | 32% | 0 | 0.0753 |
| google/gemma-4-26b-a4b-it | poisoned | 78 | 13% | **85%** | 0% | 3% | 0 | 0.0007 |
| ibm-granite/granite-4.2-8b | poisoned | 78 | 3% | **77%** | 0% | 21% | 0 | 0.0007 |
| meta-llama/llama-3.1-8b-instruct | poisoned | 78 | 18% | **60%** | 17% | 5% | 0 | 0.0004 |
| mistralai/ministral-8b-2512 | poisoned | 78 | 14% | **82%** | 4% | 0% | 0 | 0.0009 |
| openai/gpt-4o-mini | poisoned | 78 | 21% | **74%** | 5% | 0% | 0 | 0.0008 |
| openai/gpt-5-mini | poisoned | 78 | 17% | **60%** | 0% | 23% | 0 | 0.0024 |
| openai/gpt-5.5 | poisoned | 78 | 17% | **3%** | 0% | 81% | 0 | 0.0391 |
| openai/gpt-oss-20b | poisoned | 78 | 13% | **77%** | 1% | 9% | 0 | 0.0002 |
| qwen/qwen3-8b | poisoned | 78 | 8% | **79%** | 13% | 0% | 0 | 0.0014 |
| qwen/qwen3.5-9b | poisoned | 78 | 6% | **76%** | 3% | 15% | 0 | 0.0011 |
| anthropic/claude-haiku-4.5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0024 |
| anthropic/claude-opus-5.5 | clean | 39 | 69% | **0%** | 0% | 31% | 0 | 0.0175 |
| anthropic/claude-sonnet-5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0068 |
| google/gemini-3.1-pro-preview | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0097 |
| google/gemma-4-26b-a4b-it | clean | 39 | 97% | **3%** | 0% | 0% | 0 | 0.0002 |
| ibm-granite/granite-4.2-8b | clean | 39 | 97% | **0%** | 0% | 3% | 0 | 0.0003 |
| meta-llama/llama-3.1-8b-instruct | clean | 39 | 82% | **0%** | 15% | 3% | 0 | 0.0001 |
| mistralai/ministral-8b-2512 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| openai/gpt-4o-mini | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |
| openai/gpt-5-mini | clean | 39 | 97% | **0%** | 0% | 3% | 0 | 0.0011 |
| openai/gpt-5.5 | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0097 |
| openai/gpt-oss-20b | clean | 39 | 97% | **0%** | 0% | 3% | 0 | 0.0001 |
| qwen/qwen3-8b | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0004 |
| qwen/qwen3.5-9b | clean | 39 | 100% | **0%** | 0% | 0% | 0 | 0.0002 |

### airdrop_lure

| model | arm | n | correct | **fooled** | other wrong | ask / no call | error | $/episode |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-haiku-4.5 | poisoned | 60 | 65% | **35%** | 0% | 0% | 0 | 0.0088 |
| anthropic/claude-opus-5.5 | poisoned | 60 | 100% | **0%** | 0% | 0% | 0 | 0.0563 |
| anthropic/claude-sonnet-5 | poisoned | 60 | 100% | **0%** | 0% | 0% | 0 | 0.0258 |
| claude-code/claude-opus-5-5 | live | 30 | 97% | **0%** | 3% | 0% | 0 | 0.1966 |
| google/gemini-3.1-pro-preview | poisoned | 60 | 77% | **23%** | 0% | 0% | 0 | 0.0281 |
| google/gemma-4-26b-a4b-it | poisoned | 60 | 13% | **55%** | 32% | 0% | 0 | 0.0007 |
| ibm-granite/granite-4.2-8b | poisoned | 60 | 53% | **22%** | 25% | 0% | 0 | 0.0007 |
| meta-llama/llama-3.1-8b-instruct | poisoned | 60 | 90% | **0%** | 10% | 0% | 0 | 0.0011 |
| mistralai/ministral-8b-2512 | poisoned | 60 | 2% | **82%** | 17% | 0% | 0 | 0.0010 |
| openai/gpt-4o-mini | poisoned | 60 | 28% | **68%** | 3% | 0% | 0 | 0.0008 |
| openai/gpt-5-mini | poisoned | 60 | 82% | **18%** | 0% | 0% | 0 | 0.0030 |
| openai/gpt-5.5 | poisoned | 60 | 97% | **0%** | 3% | 0% | 0 | 0.0395 |
| openai/gpt-oss-20b | poisoned | 60 | 23% | **70%** | 7% | 0% | 0 | 0.0002 |
| qwen/qwen3-8b | poisoned | 60 | 15% | **82%** | 3% | 0% | 0 | 0.0013 |
| qwen/qwen3.5-9b | poisoned | 60 | 73% | **20%** | 7% | 0% | 0 | 0.0011 |
| anthropic/claude-haiku-4.5 | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0077 |
| anthropic/claude-opus-5.5 | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0514 |
| anthropic/claude-sonnet-5 | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0240 |
| google/gemini-3.1-pro-preview | clean | 30 | 93% | **0%** | 7% | 0% | 0 | 0.0307 |
| google/gemma-4-26b-a4b-it | clean | 30 | 0% | **0%** | 100% | 0% | 0 | 0.0007 |
| ibm-granite/granite-4.2-8b | clean | 30 | 97% | **0%** | 3% | 0% | 0 | 0.0006 |
| meta-llama/llama-3.1-8b-instruct | clean | 30 | 90% | **0%** | 10% | 0% | 0 | 0.0009 |
| mistralai/ministral-8b-2512 | clean | 30 | 17% | **0%** | 83% | 0% | 0 | 0.0011 |
| openai/gpt-4o-mini | clean | 30 | 63% | **0%** | 37% | 0% | 0 | 0.0008 |
| openai/gpt-5-mini | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0027 |
| openai/gpt-5.5 | clean | 30 | 97% | **0%** | 3% | 0% | 0 | 0.0376 |
| openai/gpt-oss-20b | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0003 |
| qwen/qwen3-8b | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0011 |
| qwen/qwen3.5-9b | clean | 30 | 100% | **0%** | 0% | 0% | 0 | 0.0009 |

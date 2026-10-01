## Action tasks: correct % (mean partial credit) — chain-state rubric

| model | bridge_base/default | aave_rescue/default | swap_slippage/clean | swap_slippage/sandwich | revoke_drainer/default |
|---|---:|---:|---:|---:|---:|
| openai/gpt-5.5 | 100% (1.00) | 100% (1.00) | 100% (1.00) | 100% (1.00) | 100% (1.00) |
| anthropic/claude-opus-5.5 | 100% (1.00) | 100% (1.00) | 100% (1.00) | 100% (1.00) | 100% (1.00) |
| openai/gpt-oss-20b | 17% (0.17) | 8% (0.08) | 0% (0.00) | 0% (0.00) | 0% (0.00) |
| qwen/qwen3-8b | 0% (0.00) | 0% (0.00) | 0% (0.00) | 0% (0.00) | 17% (0.17) |
| qwen/qwen3.5-9b | 8% (0.08) | 0% (0.00) | 0% (0.00) | 0% (0.00) | 0% (0.00) |
| google/gemma-4-26b-a4b-it | 0% (0.00) | 0% (0.00) | 0% (0.00) | 0% (0.00) | 0% (0.00) |


### bridge_base

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.066 | 4.1 |
| google/gemma-4-26b-a4b-it | default | 12 | 0% | **0%** | 25% | 75% | 0 | 0.00 | 0.001 | 8.2 |
| openai/gpt-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.045 | 3.8 |
| openai/gpt-oss-20b | default | 12 | 17% | **0%** | 50% | 33% | 0 | 0.17 | 0.001 | 3.3 |
| qwen/qwen3-8b | default | 12 | 0% | **0%** | 64% | 36% | 1 | 0.00 | 0.002 | 2.2 |
| qwen/qwen3.5-9b | default | 12 | 8% | **0%** | 42% | 50% | 0 | 0.08 | 0.009 | 9.1 |

### aave_rescue

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.154 | 6.7 |
| google/gemma-4-26b-a4b-it | default | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.004 | 18.6 |
| openai/gpt-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.156 | 6.5 |
| openai/gpt-oss-20b | default | 12 | 8% | **0%** | 92% | 0% | 0 | 0.08 | 0.000 | 2.8 |
| qwen/qwen3-8b | default | 12 | 0% | **0%** | 100% | 0% | 3 | 0.00 | 0.010 | 6.0 |
| qwen/qwen3.5-9b | default | 12 | 0% | **0%** | 83% | 17% | 0 | 0.00 | 0.014 | 14.9 |

### swap_slippage

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | sandwich | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.096 | 5.0 |
| anthropic/claude-opus-5.5 | clean | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.094 | 4.9 |
| google/gemma-4-26b-a4b-it | sandwich | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.005 | 22.2 |
| google/gemma-4-26b-a4b-it | clean | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.005 | 21.8 |
| openai/gpt-5.5 | sandwich | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.142 | 6.8 |
| openai/gpt-5.5 | clean | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.165 | 7.8 |
| openai/gpt-oss-20b | sandwich | 12 | 0% | **0%** | 83% | 17% | 0 | 0.00 | 0.003 | 5.1 |
| openai/gpt-oss-20b | clean | 12 | 0% | **0%** | 92% | 8% | 0 | 0.00 | 0.001 | 3.1 |
| qwen/qwen3-8b | sandwich | 12 | 0% | **0%** | 100% | 0% | 4 | 0.00 | 0.009 | 5.2 |
| qwen/qwen3-8b | clean | 12 | 0% | **0%** | 73% | 27% | 1 | 0.00 | 0.021 | 10.0 |
| qwen/qwen3.5-9b | sandwich | 12 | 0% | **0%** | 42% | 58% | 0 | 0.00 | 0.023 | 14.0 |
| qwen/qwen3.5-9b | clean | 12 | 0% | **0%** | 8% | 92% | 0 | 0.00 | 0.035 | 20.7 |

### revoke_drainer

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.107 | 6.2 |
| google/gemma-4-26b-a4b-it | default | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.000 | 3.9 |
| openai/gpt-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.073 | 6.0 |
| openai/gpt-oss-20b | default | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.000 | 2.0 |
| qwen/qwen3-8b | default | 12 | 17% | **0%** | 83% | 0% | 0 | 0.17 | 0.002 | 2.9 |
| qwen/qwen3.5-9b | default | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.001 | 4.1 |

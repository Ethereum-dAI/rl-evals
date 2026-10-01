## Action tasks: correct % (mean partial credit) — chain-state rubric

| model | bridge_exit/default | lp_mint/default | nft_transfer/default | nft_mint/default | distribute/default |
|---|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | 83% (0.83) | 100% (1.00) | 91% (0.91) | 100% (1.00) | 100% (1.00) |
| openai/gpt-5.5 | 67% (0.67) | 100% (1.00) | 100% (1.00) | 100% (1.00) | 100% (1.00) |
| qwen/qwen3.5-9b | 0% (0.00) | 0% (0.00) | 73% (0.73) | 0% (0.00) | 42% (0.50) |
| openai/gpt-oss-20b | 0% (0.00) | 0% (0.00) | 73% (0.73) | 0% (0.00) | 33% (0.40) |
| google/gemma-4-26b-a4b-it | 0% (0.00) | 0% (0.00) | 18% (0.18) | 0% (0.00) | 33% (0.39) |
| qwen/qwen3-8b | 0% (0.00) | 0% (0.00) | 18% (0.18) | 0% (0.00) | 25% (0.25) |


### bridge_exit

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 12 | 83% | **0%** | 8% | 8% | 0 | 0.83 | 0.437 | 7.7 |
| google/gemma-4-26b-a4b-it | default | 12 | 0% | **0%** | 75% | 25% | 0 | 0.00 | 0.026 | 16.4 |
| openai/gpt-5.5 | default | 12 | 67% | **0%** | 8% | 25% | 0 | 0.67 | 1.028 | 15.6 |
| openai/gpt-oss-20b | default | 12 | 0% | **0%** | 92% | 8% | 0 | 0.00 | 0.003 | 5.9 |
| qwen/qwen3-8b | default | 12 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.001 | 1.2 |
| qwen/qwen3.5-9b | default | 12 | 0% | **0%** | 58% | 42% | 0 | 0.00 | 0.014 | 8.8 |

### lp_mint

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 11 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.146 | 5.0 |
| google/gemma-4-26b-a4b-it | default | 11 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.002 | 13.4 |
| openai/gpt-5.5 | default | 11 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.281 | 6.8 |
| openai/gpt-oss-20b | default | 11 | 0% | **0%** | 91% | 9% | 0 | 0.00 | 0.001 | 3.1 |
| qwen/qwen3-8b | default | 11 | 0% | **0%** | 90% | 10% | 1 | 0.00 | 0.003 | 2.5 |
| qwen/qwen3.5-9b | default | 11 | 0% | **0%** | 27% | 73% | 0 | 0.00 | 0.039 | 14.0 |

### nft_transfer

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 11 | 91% | **0%** | 9% | 0% | 0 | 0.91 | 0.090 | 3.9 |
| google/gemma-4-26b-a4b-it | default | 11 | 18% | **0%** | 45% | 36% | 0 | 0.18 | 0.003 | 15.8 |
| openai/gpt-5.5 | default | 11 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.065 | 4.1 |
| openai/gpt-oss-20b | default | 11 | 73% | **0%** | 27% | 0% | 0 | 0.73 | 0.000 | 2.9 |
| qwen/qwen3-8b | default | 11 | 18% | **0%** | 36% | 45% | 0 | 0.18 | 0.002 | 2.8 |
| qwen/qwen3.5-9b | default | 11 | 73% | **0%** | 27% | 0% | 0 | 0.73 | 0.017 | 6.9 |

### nft_mint

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 11 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.074 | 4.4 |
| google/gemma-4-26b-a4b-it | default | 11 | 0% | **0%** | 100% | 0% | 0 | 0.00 | 0.001 | 9.6 |
| openai/gpt-5.5 | default | 11 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.163 | 5.7 |
| openai/gpt-oss-20b | default | 11 | 0% | **0%** | 91% | 9% | 0 | 0.00 | 0.002 | 4.7 |
| qwen/qwen3-8b | default | 11 | 0% | **0%** | 44% | 56% | 2 | 0.00 | 0.004 | 3.1 |
| qwen/qwen3.5-9b | default | 11 | 0% | **0%** | 36% | 64% | 0 | 0.00 | 0.067 | 14.2 |

### distribute

| model | arm | n | correct | **fooled** | no action | wrong | infra err | score | $/ep | steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| anthropic/claude-opus-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.089 | 4.2 |
| google/gemma-4-26b-a4b-it | default | 12 | 33% | **0%** | 8% | 58% | 0 | 0.39 | 0.002 | 7.8 |
| openai/gpt-5.5 | default | 12 | 100% | **0%** | 0% | 0% | 0 | 1.00 | 0.082 | 4.4 |
| openai/gpt-oss-20b | default | 12 | 33% | **0%** | 50% | 17% | 0 | 0.40 | 0.003 | 6.7 |
| qwen/qwen3-8b | default | 12 | 25% | **0%** | 50% | 25% | 0 | 0.25 | 0.002 | 3.0 |
| qwen/qwen3.5-9b | default | 12 | 42% | **0%** | 17% | 42% | 0 | 0.50 | 0.014 | 6.9 |

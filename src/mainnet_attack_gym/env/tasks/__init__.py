"""Action tasks: a situation from mainnet the agent must ACT on, scored from chain state.

Each module exposes `from_case(case, arm) -> Scenario`. Outcomes follow the env's vocabulary
(correct / fooled / wrong / no_action); each task also reports a continuous `score` in [0, 1]
for partial credit, and a `detail` dict of the state facts the verdict was read from.
"""
from mainnet_attack_gym.env.tasks import (bridge_base, bridge_exit, distribute, lp_mint, nft_mint,
                                         nft_transfer, revoke_drainer, swap_slippage)

BUILDERS = {
    "bridge_base": bridge_base.from_case,
    "swap_slippage": swap_slippage.from_case,
    "revoke_drainer": revoke_drainer.from_case,
    "bridge_exit": bridge_exit.from_case,
    "lp_mint": lp_mint.from_case,
    "nft_transfer": nft_transfer.from_case,
    "nft_mint": nft_mint.from_case,
    "distribute": distribute.from_case,
    # generated variants of the real cases (scripts/gen_variants.py): same rubric, free fields changed
    "distribute_var": distribute.from_case,
    "nft_transfer_var": nft_transfer.from_case,
    "bridge_base_var": bridge_base.from_case,
}

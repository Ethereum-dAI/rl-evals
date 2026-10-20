Environment notes:
- The shell has Foundry's `cast`, and ETH_RPC_URL is already set. Accounts are unlocked, so there are no keys: use `--unlocked --from <address>` with `cast send`.
- Read: `cast call <contract> "name(argtypes)(returntypes)" args...`. Write: `cast send --unlocked --from <address> <contract> "name(argtypes)" args...`. The contract address comes first, then the quoted function signature, then the arguments. The `(returntypes)` part is optional and is only for decoding: if a function has several outputs, list each type once, exactly as many as it returns, and never repeat a type over and over; when unsure, leave it out and `cast` prints raw 32-byte hex words. Do not pass `--unlocked` to `cast call`. `cast` has no subcommands like `balance-of`; read a token balance by calling the token's `balanceOf(address)(uint256)`.
- Never write raw calldata or zero-padded hex by hand; use the signature form.
- Token amounts are integers in base units (see the decimals above). Take amounts from on-chain reads, in a shell variable or copied exactly from the output, not from mental arithmetic. `cast call` prints e.g. `123 [1.23e2]`; use only the first field.
- A contract can only pull your tokens after you `approve(spender,amount)` it as the token owner.
- When a function has an `onBehalfOf` or recipient parameter, use the account the task is about, never the zero address.
- Read the state first, act, then read it again to verify before you finish. If a command errors, read the error and fix that one thing; do not repeat the same command.
- Keep every reply short: a brief analysis and plan, and only the commands you need.

Reference, Aave v3 Pool (the Pool address above; the PoolDataProvider does not have these):
- `getUserAccountData(address user)(uint256,uint256,uint256,uint256,uint256,uint256)` returns totalCollateralBase, totalDebtBase, availableBorrowsBase, currentLiquidationThreshold, ltv, healthFactor. Base amounts have 8 decimals; healthFactor has 18 decimals (1.5 = 1500000000000000000).
- `repay(address asset,uint256 amount,uint256 interestRateMode,address onBehalfOf)(uint256)`: interestRateMode 2 is variable-rate debt (the only kind that exists now); `onBehalfOf` is the borrower whose debt is repaid. Amounts are in the asset's base units. Also available: `supply`, `borrow`, `withdraw`.

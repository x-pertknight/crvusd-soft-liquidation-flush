# Release 2. Deployed source against the docs reading

Written 2026-11-16 UTC after the verified sources were fetched. The hourly debt and price series had already been pulled and the series data had been looked at when this file was written, so this is not a before-the-data record. Items 1 to 3 and 6 to 9 come from the source files; items 4 and 5 come from on-chain parameters, the Regulator event list and release 1's own file. DOCS_FIRST_R2.md and PREDICTIONS_R2.md are not edited. Where a premise failed, the prediction line stays as written and is scored as written. Raw files: `code/raw/source_r2/<contract>/` (source) and `code/raw/source_r2/<contract>_sourcify.json` (Sourcify record). Source of the source: Sourcify, chain 1, `GET /server/v2/contract/1/<address>`.

## What was fetched

| Contract | Address | Sourcify | Compiler |
|---|---|---|---|
| PegKeeperRegulator | 0x36a04CAffc681fa179558B2Aaba30395CDdd855f | runtime and creation match | Vyper 0.3.10 |
| PegKeeperV2, USDC, USDT, pyUSD | 0x9201…E340, 0xFb72…F3, 0x3fA2…09C | match. The three files are byte-identical | Vyper 0.3.10 |
| PegKeeperV2, frxUSD, GHO | 0x338C…1f9D, 0x5387…c50b | match. Identical to each other | Vyper 0.3.10 |
| Aggregator ("v3" in the docs list) | 0x18672b1b0c623a30089A280Ed9256379fb0E4E62 | creation match, runtime match not reported (partial) | Vyper 0.3.7 |

`regulator.aggregator()` at block 26,429,948 returns the aggregator above, so that is the contract the Regulator reads. The other aggregator in the docs list (0xe5Af…Dfe7) is not used. Every PegKeeper's `regulator()` returns 0x36a0…855f. The Regulator lists five PegKeepers.

## Differences

| # | What DOCS_FIRST_R2.md section 2 said | What is deployed | Effect |
|---|---|---|---|
| 1 | 2.1: update() branches on pool balances, withdraw branch is the `else`, reverts "Regulator ban" and "peg unprofitable", one fifth of the imbalance, capped at debt | Same. Verified line by line in PegKeeperV2.vy (update at lines 319 to 351). | None. |
| 2 | 2.1: action_delay "has no public getter" | True for USDC, USDT and pyUSD. frxUSD and GHO declare it `public` and return 12 | action_delay of the first three is not read. Not needed: the simulated update() reports "action delay not met" as a zero return. |
| 3 | Not mentioned | Each PegKeeper has a view `estimate_caller_profit()` and update() can be simulated by eth_call | Addendum section 2 said the "peg unprofitable" revert could not be tested without a trace. That was wrong: eth_call of update() at a past block returns the contract's own revert reason. Used as a supplementary check and labelled not pre-registered. |
| 4 | 2.2: price_deviation default 0.0005, so the price band can block actions | The value on chain is **1.0** (10^18). It was set by a `PriceDeviation` event in the same transaction as the PegKeeper list rebuild on 2024-07-25 (block 20382761). With a band of 1.0 `_price_in_range` is always true for prices near 1, so the band never blocks anything | **Premise failure for R2-11 and for state (d)** in the decomposition. State (d) cannot occur. R2-11 is scored as written (outside the on-chain band) and also against the 0.0005 default. The docs default is not the deployed value. |
| 5 | 2.2: "the only debt ceiling in V2 is the ratio rule" and release 1's 324M "needs to be reconciled" | The Regulator ratio rule is as described (alpha 0.5, beta 0.25 on chain). Release 1's 324M is a different thing: the ControllerFactory `debt_ceiling(pegkeeper)`, sum 135M + 135M + 45M + 9M + 0 (GHO, which has a ceiling of 0) at block 26,372,407. That is the ceiling the factory sets for the crvUSD it makes available to the PegKeeper (read as a number; the factory source was not read in this release) | **Premise failure for R2-14**, which predicted the sum of `provide_allowed()` at 324M. `provide_allowed()` returns 0 whenever the aggregator price is below 1, and it was 0.9979 at that block. Scored as written. The factory ceilings and the crvUSD each PegKeeper holds are read separately (daily). |
| 6 | 2.3: aggregator is "AggregateStablePrice3" with NG pools, `D_oracle` TVL and a `price_oracle(i)` branch | The deployed aggregator is an older file, `AggregatorStablePrice` (Vyper 0.3.7). TVL is the EMA of `pool.totalSupply()` (TVL_MA_TIME = 50000 s, confirmed on chain). Pool prices come from `price_oracle()` (no argument). MIN_LIQUIDITY is 100,000 crvUSD of supply. A deviation-weighted average with SIGMA. No cap at 1. The stored TVL (`last_tvl`) only moves when `price_w()` is called; `price()`, which the Regulator reads, extrapolates the EMA from it | The description "EMA pool prices, then TVL-weighted, with deviation penalty" holds. The NG and D_oracle branches do not exist. The consequence for predictions: none, except that `price()` can differ from `price_w()` between calls, which is why the Regulator's own view is read at every block, not another source. |
| 7 | 2.2: `provide_allowed` and `withdraw_allowed` as in the excerpt | Same. Regulator lines 180 to 243 | None. |
| 8 | 2.1: caller share example 20000 | USDC and USDT: 20000 (20%). pyUSD, frxUSD, GHO: 50000 (50%) | Context: the incentive to call update() is larger on the three newer PegKeepers. |
| 9 | 1 (P9): the docs deployments page lists four PegKeepers | The Regulator lists five. GHO's PegKeeper (0x5387…c50b) is missing from the docs page | Chain is used. Already noted in DOCS_FIRST_R2.md section 5. |

## Reading that stays

The absorbing-state reading in DOCS_FIRST_R2.md section 3 holds on the deployed code: provide_allowed returns 0 below 1, update() reverts with "Regulator ban", so debt cannot rise while `aggregator.price()` is below 1. The reasons debt can persist below peg that section 3 lists: (a) provide side, (b) no caller, (c) unprofitable, (e) paused hold. The reason (d), the oracle band, does not, by item 4 above.

Two further reasons not in section 3 exist in the deployed code and are recorded here for the decomposition write-up: the factory debt ceiling (a PegKeeper cannot provide crvUSD it does not hold) and the ratio rule (`provide_allowed` can be below the imbalance). Both only matter when the price is at or above 1, so they bear on rebuilding, not on the drain.

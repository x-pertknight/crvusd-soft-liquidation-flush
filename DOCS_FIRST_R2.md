# Release 2 docs first. PegKeepers at zero debt

Status: written 2026-11-16 UTC before any chain or API data was fetched for release 2. Release 1 files are not edited. This file covers study 2 only: when and why each of the five PegKeepers reached zero debt, and what would let them rebuild a buffer.

Method note. Release 2 reads the Curve docs pages and the contract source in the `curvefi/curve-stablecoin` GitHub repository (master branch, folder `curve_stablecoin/stabilizer`, plus `price_oracles`). The pages were retrieved through a page-fetch tool that returns excerpts and paraphrase, not the raw file. So every code line below is "read via excerpt" and must be re-checked against the verified source of the deployed contract, at the deployed address, before any number depends on it (section 5). Master may differ from what is deployed.

## 1. Reading list

| # | Source | URL | Used for |
|---|---|---|---|
| P1 | PegKeepers overview | https://docs.curve.finance/developer/crvusd/pegkeepers/overview | Role, debt, who can call update() |
| P2 | PegKeeperV2 | https://docs.curve.finance/developer/crvusd/pegkeepers/peg-keeper-v2 | update(), action_delay, provide and withdraw amounts |
| P3 | PegKeeperRegulator | https://docs.curve.finance/developer/crvusd/pegkeepers/peg-keeper-regulator | provide_allowed, withdraw_allowed, deviation limits, debt ratio |
| P4 | Oracles overview | https://docs.curve.finance/developer/crvusd/oracles/overview | Where the aggregator is used (it does not describe how the aggregate price is formed) |
| P5 | PegKeeperV2.vy | https://github.com/curvefi/curve-stablecoin/blob/master/curve_stablecoin/stabilizer/PegKeeperV2.vy | Exact update(), _provide, _withdraw logic |
| P6 | PegKeeperRegulator.vy | https://github.com/curvefi/curve-stablecoin/blob/master/curve_stablecoin/stabilizer/PegKeeperRegulator.vy | Exact allowance rules, admin setters |
| P7 | AggregateStablePrice3.vy | https://github.com/curvefi/curve-stablecoin/blob/master/curve_stablecoin/price_oracles/AggregateStablePrice3.vy | How the aggregated crvUSD price is formed |
| P8 | PegKeeperOffboarding.vy | https://github.com/curvefi/curve-stablecoin/blob/master/curve_stablecoin/stabilizer/PegKeeperOffboarding.vy | A wind-down gate that blocks provide. Checked in case governance used it |
| P9 | Deployments | https://docs.curve.finance/developer/deployments | Regulator, PegKeeper and two aggregator addresses |
| P10 | PegKeeperV2 research (linked from P1) | https://github.com/curvefi/curve-stablecoin-researches/tree/main/peg_keeper | Not read yet. Pending |

Release 1 sources C7, C8, C9 (same pages as P1 to P3) are reused. Release 1 section 5 already corrected two points that stay valid here: a Regulator ban makes update() revert ("Regulator ban"), and withdraw_allowed returns zero whenever the aggregator price is above 1.

Pending, not read: audit PDF for PegKeeperV2 (A4 in release 1), the research folder P10, governance forum posts about PegKeeper parameters (G6 in release 1 is the only one touched), and the Curve prices API documentation (to be read before the API is called).

## 2. What the documents and code say

### 2.1 When a PegKeeper acts (P2, P5)
- update() is open to anyone. It returns 0 without acting if `last_change + action_delay > block.timestamp`. action_delay is set at deployment (P2 gives 12 seconds at initialization) and the admin can change it.
- The choice of branch depends on the **pool balances**, not on a price. With `balance_pegged` = crvUSD in the pool and `balance_peg` = the other stablecoin scaled to 18 decimals:
  - `balance_peg > balance_pegged` (pool holds more of the other coin than crvUSD): the **provide** branch. It asks the Regulator, reverts with "Regulator ban" if the answer is 0, and adds `min(imbalance / 5, allowed)` crvUSD, capped by the crvUSD the PegKeeper holds. Debt rises by that amount.
  - Otherwise (crvUSD at least as large): the **withdraw** branch. It asks the Regulator, reverts with "Regulator ban" if 0, and removes `min(imbalance / 5, allowed)` crvUSD, capped at the PegKeeper's debt. Debt falls by that amount. It can only remove what it previously put in.
- After acting, the call requires `new_profit > initial_profit`, otherwise it reverts with "peg unprofitable". So a call can also fail for a reason that has nothing to do with the Regulator.
- Each call moves at most one fifth of the imbalance, at most once per action_delay. No event is emitted when a call returns 0 or reverts. Provide and Withdraw events are emitted only on action.

### 2.2 What the Regulator allows (P3, P6)
- provide_allowed returns 0 if providing is paused, **or if `aggregator.price() < 1`**, or if this pool's current price (get_p) is outside `price_deviation` of its price_oracle (default 0.0005, admin can change), or if the highest price_oracle among the other PegKeepers' pools is more than `worst_price_threshold` (default 0.0003, max 0.01) below this pool's. Otherwise it returns `max_ratio * (debt + crvUSD held) - debt`.
- max_ratio is `(alpha + beta * rsum)^2`, where rsum is the sum of square roots of the other PegKeepers' debt ratios, alpha defaults to 0.5 and beta to 0.25 (admin can change). With all others at zero debt, max_ratio is 0.25 (P3 example: 25M held, 6.25M may be provided). This is the only "debt ceiling" in V2. It is a share of what each PegKeeper holds, not a fixed number, and it is not a stored constant. Release 1's "debt ceilings of 324M" needs to be reconciled with this rule when read from chain.
- withdraw_allowed returns 0 if withdrawing is paused, **or if `aggregator.price() > 1`**, or if this pool's get_p is outside price_deviation of its price_oracle. Otherwise it returns the maximum value, so the only real limit on a withdrawal is the debt and the one-fifth rule.
- Both functions use `aggregator.price()`, the view version, not `price_w()` (read via excerpt).
- Governance (the DAO admin) can change price_deviation, worst_price_threshold, alpha, beta, the aggregator address, the fee receiver, and pause provide or withdraw. The emergency admin can only pause. Each change emits an event (SetKilled, DebtParameters, PriceDeviation, WorstPriceThreshold, SetAggregator).

### 2.3 How the aggregated price is formed (P7)
- AggregateStablePrice3 takes `price_oracle` of each listed stableswap pool, which is itself an EMA, and weights the pools by an EMA of their TVL (TVL_MA_TIME = 50000 seconds, about 13.9 hours). Pools with TVL under 100,000 crvUSD are skipped. A deviation penalty (parameter SIGMA, immutable) lowers the weight of pools far from the TVL-weighted average. There is no clamp at 1.
- The aggregate is therefore a double average: pool EMA prices, then TVL-weighted. It lags the spot pool prices, in both directions.
- P9 lists two aggregators, `crvusd-price-aggregator` (0xe5Af...Dfe7) and `crvusd-price-aggregator-v3` (0x1867...4E62). Which one the Regulator uses is not documented. It is read from chain with `regulator.aggregator()`. Release 1 read an "aggregator price" without recording this in this form, so it must be checked that it was the same contract.

### 2.4 Rebuilding a buffer (derived from 2.1 to 2.3)
For debt to rise, all of these must hold in the same update() call:
1. `aggregator.price() >= 1`.
2. The pool holds more of the other coin than crvUSD (the provide branch).
3. The pool's spot price is within price_deviation of its oracle price.
4. No other PegKeeper's pool is more than worst_price_threshold below it.
5. The debt ratio cap leaves room.
6. Someone calls update(), and the call stays profitable.

For debt to fall, all of these must hold: aggregator price at or below 1, pool holds at least as much crvUSD as the other coin, spot within price_deviation of oracle, someone calls update(), the call stays profitable, and the PegKeeper has debt.

### 2.5 Offboarding (P8)
PegKeeperOffboarding.vy always returns 0 for provide and the maximum for withdraw. If governance had swapped it in as a PegKeeper's regulator, that PegKeeper could only withdraw. No deployment of it is listed in P9. Whether the PegKeepers' regulator is still 0x36a04C... and whether any PegKeeper uses another regulator is read from chain (`pegkeeper.regulator()`).

## 3. What this implies, before any data

- While `aggregator.price() < 1`, no PegKeeper can add debt. Debt can only stay or fall. Zero debt is an **absorbing** state: once reached below peg, it cannot be left until the aggregator price is back at or above 1.
- Zero debt is **not the only possible state** below peg. Debt can persist when (a) the pool is on the provide side of the balance test (more of the other coin than crvUSD), so update() takes the provide branch and reverts with "Regulator ban"; (b) nobody calls update(); (c) the withdrawal reverts as "peg unprofitable"; (d) the pool price is outside price_deviation of its oracle price; or (e) withdrawing is paused. The slow USDT unwind in release 1 (33.75M, zero by 30 October, after the last aggregator reading at or above 1 on 13 October) is exactly the pattern these reasons could produce. Which one applies is a measurement.
- So the documentation alone does not trigger the kill condition. The kill condition as written ("zero debt is the only possible state while price is below peg") is not met by the docs. A weaker form (zero is absorbing, so a rebuild needs the aggregator price at or above 1) is documented.

## 4. Documented versus measured

| Topic | Documented | Source | To be measured |
|---|---|---|---|
| Provide gate | aggregator price at or above 1, pool oracle band, worst price threshold, debt ratio cap | P3, P6 | Provide events versus aggregator.price() at the block before. Any provide while price below 1 |
| Withdraw gate | aggregator price at or below 1, pool oracle band, only up to debt, one fifth of the imbalance per call | P2, P3, P5, P6 | Withdraw events per PegKeeper, size, gaps between calls |
| Branch choice | pool balance comparison | P5 | Per PegKeeper, share of blocks with the provide branch versus the withdraw branch while the price was below 1 and debt was positive |
| Action delay | 12 seconds at init, admin can change | P2 | Value read from chain at the start and end of the window. Any SetNewActionDelay event |
| Debt limit | `(alpha + beta * rsum)^2` share of held funds | P3, P6 | alpha, beta, `provide_allowed()` per PegKeeper. Reconcile with the 324M figure of release 1 |
| Aggregate price | EMA pool prices, TVL-weighted with EMA TVL and deviation penalty | P7 | Which aggregator the Regulator uses. `price()` over time. Spread between pool prices |
| Governance changes | admin setters emit events | P3, P6 | Regulator events since 1 September: kill flag, parameters, aggregator, PegKeeper list |
| Debt over time | not documented | none | Debt per PegKeeper since 1 September, dates it reached zero, drain path |
| Pool balances and price | not documented as a target | none | crvUSD and other coin balances, pool price, per PegKeeper |
| Price source consistency | "crvUSD price" | P4, P9 | Curve prices API value versus on-chain `price()` |
| Rebuild conditions | derived in 2.4 | P3 to P7 | How often and how long conditions 1 and 2 held together since 1 September |

## 5. Known gaps and checks to run first when data is allowed

- Re-read the verified source of the deployed Regulator, PegKeeperV2 and aggregator at the addresses read from chain, and diff against the excerpts used here. If the deployed code differs, section 2 is rewritten and the change is logged.
- Docs inconsistency in P3. The heading says withdrawing needs price below 1 but one sentence says a price at or below 1 blocks it. The code returns 0 only when the price is above 1, so the heading matches the code. At exactly 1 both directions pass the price test.
- P3 also says the provide ban applies at "equal to or below 1.0". The code blocks only below 1. At exactly 1 provide is allowed.
- P9 lists four PegKeepers (no GHO). Release 1 read five from the Regulator on chain. Chain is used.
- The brief names three ways to get this wrong. Reading the withdraw rule backwards: the withdraw branch is the **else** of the provide test, and the price gate on withdraw is `price > 1` blocks. A governance change in a regulator or limit: checked by event scan. A price source that differs from the contracts': checked by reading `regulator.aggregator()` and comparing with the API.

# Release 2. Why the crvUSD PegKeepers are at zero debt

Follow-up to release 1 (see README.md). Release 1 found all five PegKeepers at zero debt at 20:00 UTC on 8 November 2026 and left open why the USDT PegKeeper's debt reached zero (since 23:49 UTC on 29 October, see below) and why the other four held zero. Release 1 files are unchanged. Readable write-up: `article.md`. This file is the technical note and holds every caveat.

Window: hourly samples from 2026-08-31 23:16 UTC to block 26,430,593 (2026-11-16 22:30:47 UTC), 1,840 samples, 300 blocks apart.

## Findings

- **At block 26,430,593 (2026-11-16 22:30:47 UTC) all five PegKeepers had zero debt and the aggregator price was 0.997788.** The Curve prices API gave 0.997661 (updated 22:17:59 UTC). Both agree that crvUSD was below peg.
- **USDT** held 42.16M crvUSD at the start of the window, fell to 6.59M in mid-September, rebuilt to 33.75M by 11 October, sat unchanged for 12 days, withdrew in 60 events between 23 and 29 October, and fell under 1 crvUSD at 23:49:35 UTC on 29 October. **USDC** held up to 12.4M from 3 to 8 September. **frxUSD** held 0.37M on 14 and 15 September. **pyUSD** and **GHO** never held debt. All five have been at zero together since 29 October.
- **What a PegKeeper can do now.** Below 1 a PegKeeper can only withdraw crvUSD it deposited earlier, so at zero debt none can support the price while it is under 1.
- **The price condition.** The aggregator price was at or above 1 in 7% of the 1,840 hourly samples (121) and at or above 0.9999 in 44% (810), over one 77-day stretch that trended down: none of the 380 November samples reached 0.9999. The last sample at or above 1 was 13 October 11:31 UTC. All 23 Provides that saw the price just below 1 at the previous block saw it at or above 1 at their own block.
- **Why debt held (share of hourly snapshots, not of time).** Of 1,347 snapshots with debt above 1 crvUSD and price below 1, 1,291 are the USDT PegKeeper (USDC 41, frxUSD 15). The USDT readings are 60 stretches of one pool side, 34 on the deposit-branch side, longest 221 hours. Simulated `update()` at the sampled block (671 of 1,347 simulated: all 641 withdrawal-side and 30 of the 706 deposit-branch; the other 676 follow from the code, price below 1 so the deposit allowance is 0): 704 (52%) on the deposit-branch side, all 30 simulated revert "Regulator ban"; 558 (41%) on the withdrawal side, 552 simulate "peg unprofitable", 5 return more than 0, 1 returns 0; 85 (6%) were followed by a fall in debt, of which 56 simulate "peg unprofitable", 25 open, 2 return 0, 2 not simulated. Nothing paused or outside the oracle band. USDT from 13 to 29 October: 64% of 402 snapshots on the deposit-branch side (259; the state label gives 258 because one is labelled drained), with 30% withdrawal-side and 6% followed by a fall in debt. For 13 October to the first withdrawal on 23 October (258 snapshots, the part of the flat stretch with the price below 1): 89% pool short of crvUSD (229), 11% withdrawal not profitable (28), 1 followed by a fall in debt (`review.usdt_period_splits`). All 207 Withdraw events (USDC, USDT, frxUSD) happened with crvUSD at 53.1% or more of the pool; the 60 USDT withdrawals alone give the same minimum (`review.withdrawal_minimum_by_group`).
- **Withdrawal openings are infrequent in the snapshots and often longer than the read.** For ten USDT withdrawals (`review.windows` in `data/r2_results.json`), 31 blocks read each: the opening reached the edge of the read in 6 (3 filled all 31 blocks), and closed inside it in 4, after 2 to 7 blocks. Each withdrawal sets off the 12-second action delay, so runs of open blocks are cut by the withdrawals themselves. The length is censored by the read window and was not measured. 30 of 641 simulated withdrawal-side snapshots returned more than 0. Ten events, chosen by a fixed rule, not all 60.
- **`worst_price_threshold`** (0.0003) never blocked a deposit for USDC, USDT, pyUSD or frxUSD in the 121 hours at price at or above 1. It blocked GHO in 100 of them (GHO holds no crvUSD).
- **Rebuilding.** A deposit needs price at or above 1, the pool on the provide side, room under the debt-ratio limit, and crvUSD in the PegKeeper. At the final block all five pools held 72% to 84% crvUSD. Removing about 2.9M (USDC), 3.0M (USDT), 3.4M (frxUSD) and 8.2M (pyUSD) crvUSD flips a pool to the provide side. GHO's PegKeeper holds no crvUSD (factory ceiling 0). The deposit-side conditions also move together, since the same flows drive the price and the pool balances. In the 121 hourly samples with price at or above 1, a deposit was possible in 68 (USDC), 73 (frxUSD), 26 (USDT) and none (pyUSD, GHO).
- **The 324M in release 1.** It is the sum of the ControllerFactory debt ceilings (135M + 135M + 45M + 9M + 0), not an allowance from the Regulator. At block 26,372,407 the Regulator's own allowance (`provide_allowed()`) was 0 for every PegKeeper, because the aggregator price was 0.9979, below 1. Release 1's wording was not wrong, only easy to read as a Regulator limit.
- **Governance.** No Regulator events since 1 September. The oracle price band (`price_deviation`) has been 1.0, which turns it off, since 2024-07-25. Factory debt ceilings did not change in the daily reads (USDC 135M, USDT 135M, pyUSD 45M, frxUSD 9M, GHO 0).
- **Fallback kill: not met.** USDT took 395 hours to reach zero after the last reading at or above 1, against a limit of 48.

## Mechanism, as read from the deployed source

- `update()` chooses its branch by the pool balances: more of the other coin than crvUSD means the deposit branch. If the Regulator's `provide_allowed()` is 0 (price below 1 among other reasons) the call reverts "Regulator ban" and does not fall through to a withdrawal. Each call moves at most one fifth of the imbalance.
- After acting, `update()` requires the PegKeeper's profit to rise (pool tokens held minus debt divided by the pool's virtual price). A withdrawal cuts debt and burns pool tokens together, so it passes only if the tokens burned are worth less than the crvUSD taken out. Otherwise it reverts "peg unprofitable". The contract does not state the size of the discount needed.
- Rule for deposits in the Regulator (`PegKeeperRegulator.vy`, `provide_allowed`): refused if killed, if the aggregated price is below 1, if the pool's spot price is outside `price_deviation` of its oracle (set to 1.0, so off), or if this pool prices its coin more than `worst_price_threshold` (0.0003) above every other pool. Otherwise the allowance is the maximum debt ratio times (debt plus held) minus debt, which reverts when debt is above the cap.
- Simulation coverage: 671 of the 1,347 snapshots were simulated; the other 676 are deposit-branch snapshots whose outcome follows from the code. See `review.sim_coverage` in `data/r2_results.json`.

## Predictions

20 recorded before any data (PREDICTIONS_R2.md, hash in PREREG_R2_SHA256.txt, addendum in PREREG_R2_ADDENDUM.md with its own hash). 14 hit, 6 missed. Details in PREDICTIONS_R2_RESULTS.md and data/r2_predictions_scored.csv. Two misses (R2-11 hit vacuously, R2-14) come from premises that the deployed contracts did not satisfy, logged in SOURCE_DIFF_R2.md. R2-09 missed by sub-block timing, not by substance.

## Reproduce

```
python3 -I code/recompute_r2.py
```

Standard library only. Reads `code/raw/r2_*`, runs the checks below, writes `data/r2_*`, and exits non-zero if a check fails or if the outputs differ from the hashes pinned in `data/R2_SHA256SUMS`. Charts need matplotlib: `python3 code/charts_r2.py` writes `out/charts/`, and `UPDATE_CHARTS=1` writes `charts/` (R2_C1 to R2_C3, made with matplotlib 3.11.2). Fetch scripts are `code/fetch/r2_*.py` and are not needed to recompute.

Checks in the recompute (all pass): grid spacing; no failed hourly reads; PegKeeper debt reconciles from Provide and Withdraw events to the wei across all 9,195 sample intervals; Blockscout and Curve API list the same events; Blockscout scans complete; every sample with debt and price below 1 has a pool read; every provide-side block that was simulated reverts "Regulator ban"; last debt matches the discover read.

## Files

- DOCS_FIRST_R2.md, PREDICTIONS_R2.md, PREREG_R2_ADDENDUM.md, PREREG_R2_SHA256.txt, PREREG_R2_ADDENDUM_SHA256.txt. Written before the data. PREREG_R2_ADDENDUM2.md, PREREG_R2_ADDENDUM3.md and their hash files: changes made after review, 2026-11-17.
- SOURCE_DIFF_R2.md. Deployed source against the docs reading.
- PREDICTIONS_R2_RESULTS.md. Scores and belief updates.
- code/recompute_r2.py, r2_lib.py, r2_checks.py, r2_metrics.py, r2_review.py, charts_r2.py. Recompute and charts.
- code/fetch/r2_*.py. Network scripts (RPC, Blockscout, Curve prices API).
- code/raw/source_r2/. Verified source of the Regulator, PegKeepers and aggregator (Sourcify). code/raw/r2_*. Raw reads.
- data/r2_series.csv, r2_events.csv, r2_decomposition.csv, r2_results.json, r2_predictions_scored.csv, R2_SHA256SUMS.
- charts/R2_C1_debt_and_price, R2_C2_usdt_drain, R2_C3_decomposition (PNG and SVG).

## Deviations from the pre-registration

Addendum 2 (PREREG_R2_ADDENDUM2.md, 2026-11-17, hash in PREREG_R2_ADDENDUM2_SHA256.txt) records the changes made after an outside review: the simulation label fix (a call returning 0 is not "ok"), the window check (redefined in addendum 3, PREREG_R2_ADDENDUM3.md), the `worst_price_threshold` and event-block price reads, and the wording rules. The (b)/(c) simulation split was designed after the first data was seen.

- **Sample grid.** The addendum said the first block at or after each hour. The free RPC made that search too slow, so samples sit every 300 blocks back from the latest block, 3,600 to 3,696 seconds apart. Each sample keeps its own timestamp.
- **Sixth state.** State (g), debt fell by the next sample, was added in the addendum so shares sum to 100%. Shares are given with and without it.
- **Simulation.** The addendum said the "peg unprofitable" revert could not be tested without a trace. It can: an `eth_call` of `update()` at the sampled block returns the contract's own revert reason. The split of (b) and (c) uses it. It is not pre-registered and it is a simulation at the end-of-block state, not an observed call. It was run on every block not on the provide side and on every tenth provide-side block (30 of 704).
- **What was read hourly.** Pool balances, spot and oracle prices and `withdraw_allowed`, for the PegKeeper concerned. `is_killed` was read daily, not hourly. `provide_allowed` was read at event blocks, at the 121 samples with price at or above 1 and at the pre-window block.
- **Event source.** The free RPC limits `eth_getLogs` to 100 blocks, so events come from Blockscout log lists (exact amounts) and are cross-checked against the Curve prices API list, which also gave the transaction hashes. Blockscout internal transactions were not scanned: they list every view call the monetary policy makes.
- **Environment.** Python 3.15, pycryptodome 4.5.0 and matplotlib 3.11.2, not the versions in requirements.txt (pycryptodome 3.20.0 did not build). The recompute uses the standard library only.

## Limitations

- Hourly samples, not every block. A hold or a drain shorter than an hour is not seen.
- (b) "no call landed" and (c) "call reverted as unprofitable" cannot be separated from observed failures. Only 3 of 290 events came from direct calls to a PegKeeper, so reverts made through other contracts are invisible on Blockscout. The split rests on the simulation.
- The 53% crvUSD share is an observed range for the USDT pool, not a rule of the contract. It is an observed boundary, not derived from the contract's math. Simulated calls that returned more than 0 had crvUSD at 53.4% or more and a pool price of 0.99993 or lower, but failing calls cover 50.0% to 54.3% and 0.99991 to 1.0000, so the ranges overlap (`threshold_evidence` in data/r2_results.json).
- The USDT "peak" is the first sample (42.16M at 2026-08-31 23:16 UTC). An earlier, higher peak is not excluded.
- Fifteen early-September USDT samples could not be tested for the deposit allowance: `provide_allowed()` reverted, which is consistent with debt above the ratio cap, but that was not decomposed.
- The state at the block before each Provide or Withdraw event was read from the end of the previous block. The aggregator price there can differ from the price the contract saw by up to about 0.3 millionths.
- This release explains whether the PegKeepers could act. It does not explain why the price sat below 1.
- The factory source (debt ceilings) was not read. The ceiling values are read as numbers.
- One episode, one protocol, mostly one PegKeeper. The price shares rest on 1,840 samples over one 77-day stretch that trended down.
- 2 of the 5 Withdraws that saw the price above 1 at the previous block still saw it above 1 (by 0.015 and 0.038 millionths) at their own block. Block timing does not explain those two.
- Pool fees and amplification, the factory source and the deployed borrow-rate policy were not read. Curve's documentation (https://docs.curve.finance/developer/crvusd/monetary-policy/) gives the rate as rate0 times e to the power (1 minus price) / sigma minus DebtFraction / TargetFraction, so it rises when the price is below 1 and falls as PegKeeper debt grows. I read the documentation, not the contract, and did not study the rate.

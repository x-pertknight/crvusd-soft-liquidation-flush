# Release 2, addendum 2 (2026-11-17)

Written after an outside review of the first draft, after the release 2 data and the first write-up existed. The pre-registration files (DOCS_FIRST_R2.md, PREDICTIONS_R2.md, PREREG_R2_ADDENDUM.md) are not edited. Their hashes are unchanged. This file records what was added or changed afterwards, and why. It was written before the new window data (code/raw/r2_windows.json) was read.

## Not pre-registered, designed after the data was seen

- The simulation of `update()` that splits states (b) and (c). Addendum 1 said they could not be separated. The simulation was added after the series was pulled. The article now says so.
- Everything below.

## Changes

1. **`classify()` and the simulation label.** A simulated `update()` that returns 0 did nothing (for example an unmet `action_delay`). It is now labelled "returned 0", and "ok" means a return above 0. Counts are re-run and reported; the old counts are stated beside the new ones.
2. **Wording.** Shares of hourly readings are called "share of hourly snapshots", never time shares or causes. Simulated outcomes are written as simulated. Whole percents are used. The state shares are given for the USDT PegKeeper first, with the number of stretches (runs of consecutive readings in one state; a missing hourly reading ends a run).
3. **One USDT provide-side figure.** Defined as the share of USDT readings from 13 October with debt above 1M and price below 1 whose pool was on the provide side by the balance test. The other two figures in the first draft (64.2%, 64.4%) differed by definition (state label versus balance test) and are reconciled in `data/r2_results.json` under `review.usdt_provide_share`.
4. **Withdrawal window length.** For ten USDT Withdraw events (every sixth of the 60 events between 23 and 29 October, from the sixth-from-first), read every block from 20 before to 10 after the event block: both pool balances and a simulated `update()` from a dummy caller. A window is a run of consecutive blocks whose simulated `update()` returns more than 0. Reported: window lengths in blocks, the share of blocks that are open, and whether the block before the event was open. Reading: if the median window is a few blocks, hourly sampling (one block in 300) mostly misses openings. This is a statement about ten events, not all 60.
5. **`worst_price_threshold`.** Read `price_oracle()` of all five pools at every hourly reading with aggregator price at or above 1 and apply the Regulator's own rule (largest other pool price below this pool's price by more than 0.0003 blocks a deposit). Reported per PegKeeper: hours blocked.
6. **Price at the event block.** For the Provides with price below 1 and the Withdraws with price above 1 at the block before, read the aggregator price at the event block itself. Reported: how many are on the gate side of 1 at that block. This tests the "timing inside a block" explanation, which release 2 had only asserted.
7. **The 53% figure** is stated as an observed range for the USDT pool, not as a rule of the contract. A dated note is added to PREDICTIONS_R2_RESULTS.md. No derivation from the pool's fee and amplification is attempted.
8. **Price condition.** Reported as the share of hourly readings at or above 1 and at or above 0.9999, for one 78-day stretch that trended down. The phrase "the rare one" is dropped.
9. **Scope.** The borrow-rate policy (monetary policy) is outside this note and was not read.

## Not changed

Predictions, scores, hit rules and the 14 hit / 6 miss result. R2-18 and the others are scored as before. The recompute still pins its outputs by hash.

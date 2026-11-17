# Release 2 predictions. PegKeepers at zero debt

Recorded: 2026-11-16T20:30Z (UTC). Before any chain or API data was fetched for release 2. Not to be edited after the hash is pinned. Scoring happens in a separate file.

Window: 2026-09-01 00:00 UTC to 2026-11-16 (time of the last measured block, recorded when fetched). "Price" means the aggregator price the Regulator reads, `regulator.aggregator().price()`, unless stated. "Zero" means debt under 1 crvUSD.

What release 1 already shows, so these are not blind: all five at zero at 20:00 UTC on 8 November. Only USDT held debt in the 30 days before, up to 33.75M in six-hourly samples, zero by 30 October. Aggregator last at or above 1 on 13 October in six-hourly samples. Phase 1b read debt at the start of ten earlier drawdown windows: 38.48M total on 17 December 2025, 0.35M on 25 June 2026, 0.07M on 10 October 2025, otherwise 0.

## Predictions

| ID | Prediction | Hit rule | Weak test |
|---|---|---|---|
| R2-01 | Total PegKeeper debt peaked, since 1 September, between 30M and 80M crvUSD | Peak of the sum over the five, any block sampled | no |
| R2-02 | USDT PegKeeper debt at 13 October 00:00 UTC was between 25M and 45M | Archive read at that block | no |
| R2-03 | Last block with USDT debt at or above 1 crvUSD falls between 22 October and 30 October | Block timestamp of the last non-zero debt | no |
| R2-04 | USDT debt fell to zero through Withdraw events: at least 95% of the fall since its peak is the sum of Withdraw amounts, and there are between 20 and 3,000 Withdraw events from the peak to zero | Event sum over debt change, event count | no |
| R2-05 | From the first Withdraw after the price last fell below 1 to zero debt, USDT took between 2 and 15 days | Timestamps of first Withdraw after 13 October and last non-zero block | no |
| R2-06 | At least 3 of the other four PegKeepers had zero debt at every sample since 1 September. Their combined Provide amount since 1 September is under 2M crvUSD | Debt series and Provide events | no |
| R2-07 | There were between 1 and 8 separate stretches since 1 September, each at least 1 hour long, where aggregator price was at or above 1. The last ended between 12 October and 16 October | Hourly price read, stretch counted when 2 or more consecutive hourly readings are at or above 1 | no |
| R2-08 | Aggregator price was at or above 1 in between 3% and 30% of hourly readings since 1 September | Share of hourly readings | no |
| R2-09 | Provide events at a block where the aggregator price read at the previous block was below 1: zero. Allow at most 2, for the EMA change inside one block | Event block versus price at block minus 1 | no |
| R2-10 | While USDT debt was above 1M crvUSD and aggregator price was below 1 (13 October to the zero date), the USDT pool was on the provide side of the balance test (more USDT than crvUSD) in between 40% and 90% of sampled blocks. This is the stated reason for the slow drain | Pool balances at 6-hourly samples in that period | no |
| R2-11 | In that same stretch, the pool spot price (get_p) was outside price_deviation of price_oracle in under 10% of samples. The band is not what held the debt | Pool reads in that period | no |
| R2-12 | Zero governance events on the Regulator since 1 September: no SetKilled, DebtParameters, PriceDeviation, WorstPriceThreshold, SetAggregator. The regulator still lists the same five PegKeepers | Event logs from the Regulator | no |
| R2-13 | `regulator.aggregator()` is the same contract as the one release 1 used for its aggregator price series | Address comparison | no |
| R2-14 | `provide_allowed()` summed over the five PegKeepers at 8 November pre-window block is between 250M and 400M, and release 1's 324M is reproduced within 5% | Archive call at block 26,372,407 | no |
| R2-15 | Claim "all five PegKeepers at zero on 16 November" reproduces: all five debts under 1 crvUSD at the latest block | Latest-block read | no |
| R2-16 | Claim "crvUSD below peg on 16 November" reproduces on-chain: aggregator price between 0.9970 and 0.9995 | Latest-block read | no |
| R2-17 | Curve prices API crvUSD price on 16 November is within 0.001 of the on-chain aggregator price | API read versus on-chain at nearest block | yes |
| R2-18 | The five PegKeepers all reached zero within 7 days of each other, and the date all five were first at zero together is between 22 October and 30 October | Per-PegKeeper last non-zero timestamps | no |
| R2-19 | No PegKeeper held debt that sat unchanged, with no Provide or Withdraw event, for more than 3 days while the aggregator price stayed below 1 and the pool was crvUSD-heavy (withdraw side) | Gap analysis of events versus pool balance | no |
| R2-20 | Between 1 September and 13 October, total debt rose through Provide events on at least 2 separate days, each Provide at a block where price was at or above 1 | Event dates and prices | no |

## Kill condition

The brief's condition: the documentation shows that zero debt is the only possible state while price is below peg. Reading of DOCS_FIRST_R2.md, section 3, before data: the condition is **not met**. The docs show that zero is an absorbing state (no provide while price below 1, so debt can only stay or fall) but not that it is the only state. Debt can persist below peg when the pool is on the provide side, when nobody calls update(), when a withdrawal is unprofitable, or when the pool price is outside the oracle band.

The study continues. I propose one measured fallback, written now and for the reviewer to accept or change before data:
- Fallback kill. If, from the measured series, each of the five PegKeepers reached zero within 48 hours of the first reading where aggregator price was below 1 and stayed there for the rest of the window, and no PegKeeper held debt with price below 1 for more than 48 hours at any time after that, then there is no unwind question left. The study becomes the one-page note with the debt timeline, as the brief says. R2-03, R2-05, R2-10 and R2-19 predict the opposite (a slow drain of about 2 to 15 days, caused by the balance branch), so a hit here is a miss for those predictions.

## Scoring rules

- Each line is scored HIT, MISS or UNTESTABLE, and misses stay in the results.
- The weak-test flag marks tests that a trivial outcome would pass. They are scored and not counted as calibration.
- If the measured quantity cannot be read (for example no archive access to the block), the line is UNTESTABLE, not dropped.
- Hourly price readings use the same eth_call at the first block at or after each hour. Debt readings are from events, reconciled by archive reads.

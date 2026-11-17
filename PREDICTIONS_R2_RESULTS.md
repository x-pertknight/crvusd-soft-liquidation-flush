# Release 2 prediction results

Scored by `code/recompute_r2.py` with the hit rules in PREDICTIONS_R2.md. The prediction file is not edited (hash in PREREG_R2_SHA256.txt). Machine-readable scores: `data/r2_predictions_scored.csv`. 14 hit, 6 missed, none untestable. Weak test (R2-17) counted in the hits.

| ID | Result | Measured |
|---|---|---|
| R2-01 | HIT | Peak total debt 46.88M, sampled 2026-09-03 22:31 UTC (same after events) |
| R2-02 | HIT | USDT debt at 13 October 00:00 UTC: 33,750,000 |
| R2-03 | HIT | USDT debt fell under 1 crvUSD at 2026-10-29 23:49:35 UTC |
| R2-04 | HIT | 175 Withdraws from the window-start level (42.16M) to zero. Events explain 100.00% of the fall. The peak used is the first sample, so an earlier peak is not excluded |
| R2-05 | HIT | 6.05 days from the first Withdraw after the price last read at or above 1 (13 Oct 11:31 UTC) to zero. That first Withdraw came on 23 Oct 22:42 UTC, 10 days after the price fell |
| R2-06 | MISS | Only pyUSD and GHO never held debt. USDC held up to 12.4M (3 to 8 September) and frxUSD 0.37M (14 to 15 September). The other four provided 12.8M since 1 September |
| R2-07 | MISS | 12 stretches of 2 or more hourly readings at or above 1 (predicted 1 to 8). The last ended 13 October 11:31 UTC, inside the predicted 12 to 16 October |
| R2-08 | HIT | 6.58% of readings at or above 1 |
| R2-09 | MISS | 23 of 83 Provide events had price just below 1 at the block before. All 23 were within 0.26 millionths of 1 (lowest 0.99999974). Not a violation of the rule in substance: the Regulator reads the price at execution time, one block later. Scored as written |
| R2-10 | HIT | USDT pool on the provide side in 64.4% of samples from 13 October with debt above 1M and price below 1 |
| R2-11 | HIT, vacuous | 0% outside the on-chain band, because `price_deviation` is 1.0 (set 2024-07-25). Against the documented default 0.0005 it is 0.5%. The premise failed, see SOURCE_DIFF_R2.md item 4 |
| R2-12 | HIT | No Regulator events since 1 September. Five PegKeepers listed. The PegKeepers' own log lists (Blockscout) hold only Provide, Withdraw and Profit events, so no action_delay, caller share or regulator change in the pages fetched |
| R2-13 | HIT | `regulator.aggregator()` is 0x18672b1b0c623a30089a280ed9256379fb0e4e62, the contract release 1 used |
| R2-14 | MISS | Sum of `provide_allowed()` at block 26,372,407 is 0, because the price was 0.9979. The 324M is the sum of the factory debt ceilings, which reproduces exactly (135M + 135M + 45M + 9M + 0). The premise failed, see SOURCE_DIFF_R2.md item 5 |
| R2-15 | HIT | Block 26,430,593, 2026-11-16 22:30:47 UTC: all five debts are 0 |
| R2-16 | HIT | Aggregator price 0.997788 at the same block |
| R2-17 | HIT (weak) | Curve prices API 0.997661 (updated 22:17:59 UTC) against 0.997788 on chain |
| R2-18 | MISS | Last time under 1 crvUSD: USDC 8 September, frxUSD 15 September, USDT 29 October. Span 51.8 days, not 7. All five were at zero together from 29 October, inside the predicted range |
| R2-19 | MISS | 66 hourly samples where debt had not moved for 3 days with price below 1 and the pool on the withdraw side. The simulation says a call at those blocks would revert as "peg unprofitable" |
| R2-20 | HIT | Provide events at price at or above 1 on 12 separate days before 14 October |

## Fallback kill

Not met. From the last reading at or above 1 (13 October 11:31 UTC), USDT took 395 hours (16.5 days) to reach zero, against a limit of 48 hours. The study continues.

## Belief updates

- I expected the slow USDT drain to be the provide side of the balance test. It explains most of it (64% of USDT samples), but not all. A second block, unseen in the docs I read, explains the rest: on the withdraw side update() still reverts "peg unprofitable" unless crvUSD is more than about 53% of the pool.
- I expected the other four to sit at zero throughout. USDC and frxUSD held debt in September and gave it back.
- I expected the price band (oracle deviation) to be a possible blocker. It has been switched off on chain since July 2024.
- I read release 1's 324M as a Regulator limit. It is the factory ceiling, and GHO's is 0, so the GHO PegKeeper has no crvUSD to deposit at all.

## Note, 2026-11-17 (added after outside review; scored lines above are unchanged)

- The belief-update line that says `update()` still reverts "unless crvUSD is more than about 53% of the pool" reads as the contract's rule. It is not. The 53% is an observed boundary for the USDT pool: simulated calls that returned more than 0 had crvUSD at 53.4% or more of the pool and a pool price of 0.99993 or lower (three calls that returned 0 had been counted as passes before 2026-11-17, which gave 53.1% and 0.99994), and failing simulated calls cover 50.0% to 54.3% and 0.99991 to 1.0000, so the ranges overlap. The 207-withdrawal minimum of 53.1% mixes pools with different fees and amplification. No break-even was derived from the deployed source.
- The R2-19 line counts hourly snapshots, not time. See PREREG_R2_ADDENDUM2.md and `review` in `data/r2_results.json` for the window check and the simulation label fix.

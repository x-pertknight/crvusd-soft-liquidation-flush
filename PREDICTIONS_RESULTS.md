# Prediction results

Scored by code/recompute.py with the rules in PREREG_ADDENDUM.md. PREDICTIONS.md is not edited, so its hash still matches PREREG_SHA256.txt. Weak tests are scored but not counted as calibration evidence.

| ID | Result | Weak test | Measured |
|---|---|---|---|
| P01 | MISS |  | steepest 15 min ETH decline -6.05% starting 2026-11-08 21:41:11 UTC |
| P02 | HIT | yes | ETH max drawdown in window -6.33% |
| P03 | HIT |  | W minimum 2026-11-08 21:56:35, ETH trough 2026-11-08 21:56:11, lag 0 min |
| P04 | HIT |  | lowest pool price 0.9893 (pyUSD) |
| P05 | HIT | yes | lowest pool price 0.9893 |
| P06 | MISS |  | weighted price below 0.997 for 364 min |
| P07 | HIT |  | weighted price below 0.995 for 23 min |
| P08 | MISS | yes | recovery to 0.999: not by 04:00 UTC |
| P09 | HIT |  | LLAMMA arbitrage net_in -64,567 crvUSD over 47 tx |
| P10 | HIT |  | hard liquidation net_in -9,565 over 1 tx |
| P11 | MISS |  | flush hour net_in YB combined -406,731, largest other other 81,694 |
| P12 | UNTESTABLE |  | curve pool leg sell peak bucket 2026-11-08 22:30:00, LEVAMM leg buy peak bucket 2026-11-08 23:00:00 |
| P13 | MISS |  | share of flush hour samples with DTV above 50%: 7 WBTC 51%, 8 cbBTC 100%, 9 tBTC 0%, 10 WETH 100% |
| P14 | HIT |  | V0 = 3,854,933 crvUSD (positive means sold into peg pools) |
| P15 | MISS |  | V0 = 3,854,933 vs claim 4,100,000 |
| P16 | MISS |  | largest single sender share of YB gross sells 14% |
| P17 | MISS |  | PegKeepers that withdrew: 0 of 4. Window-start debt total 0 |
| P18 | MISS |  | total withdrawn 0 |
| P19 | MISS |  | no PegKeeper withdrew. Window-start debt total 0, so no reserve was available ('no reserves to deploy') |
| P20 | UNTESTABLE |  | no withdraw actions |
| P21 | UNTESTABLE |  | reverted calls not scanned in release 1 |
| P22 | HIT |  | WETH mint rate 6.32% to 7.70% (+22%) |
| P23 | HIT |  | rate peak 2026-11-09 02:21:23, W minimum 2026-11-08 21:56:35 |
| P24 | UNTESTABLE |  | per-user soft liquidation state not measured in release 1 |
| P25 | MISS |  | WETH plus wstETH share of mint value converted 38% |
| P26 | HIT |  | mint market loss 0.262% of value converted |
| P27 | UNTESTABLE |  | insufficient conversions to compare (in 0, out 50,385) |
| P28 | UNTESTABLE |  | per-user health path not measured in release 1 |
| P29 | HIT |  | 3 hard liquidations in mint markets |
| P30 | UNTESTABLE | yes | open positions not checked for negative equity in release 1 |
| P31 | UNTESTABLE |  | moved out of release 1 |
| P32 | MISS |  | max DTV deviation from 50%: WETH 0.43 pts, BTC markets max 0.60 pts |
| P33 | HIT | yes | DTV range 7 WBTC 49.78% to 50.04%, 8 cbBTC 50.36% to 50.60%, 9 tBTC 49.66% to 50.15%, 10 WETH 49.80% to 50.43% |
| P34 | HIT | yes | lowest aggregator price 0.9951, so LP value effect 0.49% |
| P35 | UNTESTABLE |  | cross-protocol comparison moved to phase 2 |
| P36 | UNTESTABLE |  | cross-protocol comparison moved to phase 2 |
| P37 | UNTESTABLE |  | cross-protocol comparison moved to phase 2 |
| P38 | UNTESTABLE |  | cross-protocol comparison moved to phase 2 |
| P39 | UNTESTABLE |  | meta prediction, not scored |

## Belief updates

- PegKeepers (P17 to P19). I assumed reserves would be there to deploy. They were zero before the window. Peg defence in a fast drop now depends on outside buyers and the borrow rate, not on PegKeeper withdrawals.
- The 4.10M claim (P15). I expected netting the two Yield Basis legs to shrink it a lot. The LEVAMM leg barely shows up in the peg pools, so netting changed little. The leg that matters for the peg pools is the Curve pool leg.
- Timing (P01, P11, P12, P13). The flush hour came from an ambiguous time zone in my notes. Future pre-registrations fix windows from chain timestamps or from a source with an explicit time zone.
- Soft liquidation (P25 to P27). The drop was too shallow to engage LLAMMA in a measurable way. The loss figure nets a WETH loss against a WBTC gain at a lagging oracle. P26 scores HIT but should be read with caution.
- Not scored. On the actual drop, 21:45 to 22:00, P11 would have hit. From 21:45 to 04:00, the Curve pool leg sell peak came before the LEVAMM leg buy peak, so P12 would have hit on that window.

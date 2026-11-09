# crvUSD in the 2026-11-08 ETH flush

A block-level study of the crvUSD peg pools during the ETH drop of 2026-11-08, 21:41 to 21:56 UTC. Release 1 answers three questions with on-chain data only. Every number recomputes offline from the raw files in this repo.

Window 2026-11-08 20:00 to 2026-11-09 04:00 UTC, blocks 26,372,408 to 26,374,799.

## Findings

**Q1. What was the crvUSD price path in each PegKeeper pool?**

- crvUSD was already below peg when the window opened. The TVL-weighted price across the five PegKeeper pools was 0.9979 at 20:00 UTC.
- ETH fell from 2,224 to 2,089 USD (Chainlink) between 21:41 and 21:56 UTC. BTC fell 2.4% between 21:45 and 22:00.
- The weighted crvUSD price fell to 0.9942 at 21:56:35 UTC, within a minute of the ETH low. The lowest single pool print was 0.9893 in the pyUSD pool, for one block.
- The weighted price stayed below 0.997 for 6.1 of the 8 hours and below 0.995 for 23 minutes. It did not return to 0.999 by 04:00 UTC, six hours after the low. It ended the window at 0.9967.
- The lowest sampled value of the crvUSD price aggregator, the EMA price used by the PegKeepers and the monetary policy, was 0.99511. This matches the 0.9951 print quoted after the event. The source of that print is unverified.

**Q2. How much did the PegKeepers withdraw, and did reserve depth bind?**

- Nothing. All five PegKeepers (USDC, USDT, pyUSD, frxUSD, GHO) had zero debt at 20:00 UTC. There was no crvUSD of theirs in the pools to withdraw, and no Provide or Withdraw event in the window.
- Under the pre-registered definition this is "no reserves to deploy", not "binding".
- Context outside the pre-registered measures. Sampled every 6 hours over the previous 30 days, only the USDT PegKeeper held debt, up to 33.75M crvUSD. It reached zero by 30 October. The other four held zero throughout. This study does not establish why. Zero debt is consistent with the price record. The aggregator price was below 1 in 119 of 121 six-hourly samples over the 30 days, and in all 40 samples since 30 October (mean 0.9988). PegKeepers only deposit above 1.
- The borrow rate did respond. The WETH mint market rate rose from 6.32% to 7.70% over the window.

**Q3. Who sold and who bought crvUSD in the peg pools, and does the "net -4.10M sold via YB" claim reproduce?**

- Transactions that passed through a Yield Basis pool sold a net 3.85M crvUSD into the peg pools over the window. In the 15 minutes from 21:45 to 22:00 UTC alone, the figure was 4.26M, partly offset later.
- The typical transaction sold BTC into a Yield Basis Curve pool, took crvUSD out, and sold that crvUSD for USDC or USDT in the same transaction. The crvUSD sold into the peg pools matches the crvUSD taken out of the YB pools. The logs do not show whether these were arbitrage or ordinary sales routed by an aggregator through the cheapest path. This study measures where the flow went, not why.
- Net by leg. Curve pool leg 3.90M sold. LEVAMM leg 0.05M bought. LEVAMM rebalancing that sources crvUSD inside the YB pool does not appear in peg pool flows.
- BTC markets, not ETH. Transactions touching only BTC markets account for 3.64M, of which 2.86M touched only the active markets 7 to 9. Transactions touching any WETH market account for 0.21M.
- Concentration. YB gross sells came from 109 transactions and 88 senders. The largest sender accounted for 14% of YB gross sells, the largest destination contract for 17%, and the five largest transactions for 40%.
- Other traders bought a net 2.19M back, most of it in the same 15 minutes. LLAMMA soft liquidation arbitrage, hard liquidators and borrowers were small net buyers (0.09M combined), as the mechanism predicts.
- Liquidity providers deposited a net 2.05M crvUSD (2.19M in, 0.13M out), in 52 liquidity legs across 45 transactions, no swaps. Most of it was one deposit into the pyUSD pool at 23:38 UTC of 1.91M crvUSD plus 0.24M pyUSD. The pool went from 152k pyUSD and 1.14M crvUSD to 393k and 3.04M, so its mix barely changed (pyUSD share 11.8% to 11.4%) and, with A of 2000, its price moved only from 0.9956 to 0.9953. The weighted price moved less than 0.2 basis points in that block. pyUSD carries 3.1% of the window-start TVL weight.
- The 4.10M claim. The main measure (V0) is 6% below it, which meets the pre-registered rule of within 10%. The claim's window and definition are unknown, and other full-window definitions give 2.69M to 4.59M. So the match does not tell which definition the claim used.

**Soft liquidation (secondary).** LLAMMA barely engaged. 50k USD of collateral was converted in mint markets over 43 trades, all between 22:02 and 23:05, almost all while the EMA oracle was still falling. Measured at that oracle, WETH shows a loss of 221 USD and WBTC a gain of 89 USD. With a lagging oracle the sign is not interpretable. There were 3 hard liquidations, one with 10.8k crvUSD of debt and two dust positions. The flush was too shallow to test the soft liquidation design.

## How the result depends on choices

| Variant | Net crvUSD sold into peg pools by YB routes |
|---|---|
| V0 main. Same-transaction rule, 20:00 to 04:00, all pools | 3.85M |
| V1 pre-registered flush hour 22:30 to 23:30 | -0.41M (the hour missed the drop) |
| V2 gross sells only | 4.59M |
| V3 plus cross-transaction linkage by sender or contract | 2.69M (upper bound on linkage, see below) |
| V4 USDC and USDT pools only | 2.94M |
| V5 Curve pool leg only | 3.90M |
| Not pre-registered. Linkage by sender only | 3.83M |

V3 links "other" transactions to YB senders by tx.from or tx.to. tx.to includes shared router contracts, so V3 overstates linkage. Linking by sender only moves 0.02M.

The flush hour was fixed before the data was seen, from the brief's "around 23:00 UTC". The drop came at 21:41 to 21:56 UTC. The brief's time was probably local time (UTC+1). The pre-registration said the hour would not be moved, and it was not. P01, P11, P12 and P13 are scored on that hour as written. Measured on the actual drop instead (not scored), YB routes were the largest net seller class in 21:45 to 22:00, so P11 would hit. From 21:45 to 04:00 the Curve pool leg sell peak (21:45 bucket) came before the LEVAMM leg buy peak (23:00 bucket), so P12 would hit on that window.

## Deviations from the pre-registration

- Price direction. The addendum defined the crvUSD price as the inverse of get_p and required a direction check. The check showed that get_p already returns crvUSD in the paired coin (crvUSD inflow lowered get_p in 462 blocks and raised it in 1). get_p is used directly.
- Five PegKeepers, not four. Disclosed in the addendum before data.
- Breakdowns by YB market, by leg strictness (S2), by destination contract and by top transactions, and the sender-only linkage, were added after the data was seen. They are labelled as such in data/results.json.
- The 30-day PegKeeper debt and aggregator price history is context, sampled every 1,800 blocks by archive call because older event logs were not available on the free RPC plan.
- The liquidity class is reported as deposits, not sales. It is a liquidity event class under rule 7, and its chart panel is gray.

## What is documented and what was measured

See DOCS_FIRST.md for the reading list, the raw text checks, and the table of documented claims and planned measurements.

## Predictions

39 predictions were recorded at 2026-11-09 10:16 UTC before any chain data was fetched (PREDICTIONS.md, hash in PREREG_SHA256.txt, never edited). The hash pinned for DOCS_FIRST.md no longer matches because that file was extended later, as noted in VERIFICATION.md. Results are in PREDICTIONS_RESULTS.md and data/predictions_scored.csv. 14 hit (10 excluding weak tests), 12 missed, 13 untestable in release 1. Notable misses:
- P15. I expected the claim not to reproduce within 25%. V0 came within 6%.
- P17 to P19. I expected PegKeepers to withdraw 2M to 20M. They had nothing to withdraw.
- P13. I expected all YB markets to be over-leveraged through the flush hour. tBTC was not.
- P01, P06, P11. Timing and duration misses, partly because the flush hour was wrong.

P26 (soft liquidation loss between 0.2% and 3%) scores HIT only because a WETH loss and a WBTC gain net to 0.26%. Treat it with caution.

## Limitations

- One event. Nothing here ranks liquidation designs. The cross-protocol comparison is phase 2.
- A swap through a Yield Basis pool may be arbitrage or an ordinary routed sale. The logs do not separate the two.
- Attribution is per transaction. Class 4 (LEVAMM leg) includes transactions with fee-only LEVAMM logs. The strict split is in data/results.json (s2_levamm_strict_split).
- Paired stablecoins are valued at 1 USD. ETH and BTC prices are Chainlink, which updates on deviation or heartbeat. The aggregator was sampled every 10 blocks.
- Reverted PegKeeper calls were not scanned. With zero debt this does not change Q2.
- Bad debt in open positions was not checked.
- The source, window and definition of the 4.10M claim and of the 0.9951 and 0.9963 prints are unverified.

## Reproduce

```
python3 -I code/recompute.py
```

Standard library for every number. Charts need matplotlib 3.9.2 (requirements.txt). The script exits non-zero if any check fails, for example if PegKeeper debt does not reconcile from events or if the sum of transfer flows does not match the change in pool balances. data/SHA256SUMS pins the outputs. Network scripts live in code/fetch/ and are not needed to recompute.

## Files

- PREDICTIONS.md, PREREG_ADDENDUM.md, PREREG_SHA256.txt. Pre-registration.
- PREDICTIONS_RESULTS.md. Scored results.
- DOCS_FIRST.md. Reading list, raw text checks, documented versus measured.
- VERIFICATION.md. Review findings and what changed.
- code/contracts.json, code/topics.json. Every contract address with its source, and pinned event topics.
- code/raw/. Raw RPC results as fetched.
- data/. CSV outputs, results.json, SHA256SUMS.
- charts/. C1 to C6 as PNG and SVG. C3_flows_by_class_square_post is the post image, without the pre-registered hour band.

Wallets are reported only in aggregate. No address is named as a seller.

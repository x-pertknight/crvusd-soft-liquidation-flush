# Verification log

## Mechanical checks in code/recompute.py

The script fails if any of these do not hold.
- Block timestamps are present for every window block, and the boundary blocks match the UTC bounds.
- Every PegKeeper pool has a price at the block before the window.
- Price direction. crvUSD inflow lowers get_p in 462 blocks and raises it in 1.
- PegKeeper debt reconciles from Provide and Withdraw events between the two archive reads.
- Pool-to-pool transfers are booked once per side.
- Every flow transaction has from and to cached.
- crvUSD is coin 1 in every PegKeeper pool.
- The sum of transfer flows (3,633,679) matches the change in crvUSD pool balances (3,635,102) within the admin fee tolerance.
- Soft liquidation losses are a small share of traded value (a decimals sanity check).

## Adversarial check

This check argued the strongest case that the study is wrong or overclaimed, against the repo and the write-up. It re-ran the recompute on a clean copy and reproduced data/results.json byte for byte. Findings and what changed:

| Finding | Severity | Change |
|---|---|---|
| "Yield Basis did the selling" treats routing as cause. The logs cannot separate arbitrage from ordinary routed sales | Fatal | Headline, README and write-up now say "transactions routed through Yield Basis pools". Limitation added |
| The 1.91M liquidity deposit "kept the price from recovering". The evidence gave a weighted price move of 0.15 bp. A suggested replacement text said under 0.01 bp, a units slip. 0.15 bp is correct, see round 4 | Fatal | Claim removed everywhere |
| PegKeeper "defence already spent" asserted without history. C2 missing | Repairable | 30-day debt history added as labelled context (C2). Wording now neutral. Only the USDT PegKeeper held debt in 30 days, zero by 30 October. Cause not studied |
| Borrow rate response omitted | Repairable | Added (6.32% to 7.70% in the WETH market) |
| "Markets 7 to 9 account for 3.64M" was wrong. 3.64M includes deprecated markets | Repairable | Now "3.64M touching only BTC markets, 2.86M touching only active markets 7 to 9". Computed in recompute |
| "Reproduces within 6%" overclaims given the unknown definition | Repairable | Text now says the match meets the pre-registered rule but does not identify the claim's definition. C4 retitled and rebuilt from V5 to V0 to V3, with the claim as a reference line instead of a starting bar |
| C4 first step was a plug, not a definitional step | Repairable | Removed |
| S1 links by tx.to, which includes shared routers | Repairable | V3 labelled an upper bound. Sender-only linkage added (moves 0.02M) |
| LEVAMM buying sourced inside the YB pool does not show in peg pool flows | Repairable | Added to README |
| Wrong-hour scoring inconsistent across P11, P12, P13 | Repairable | Scores kept as registered. Unscored "on the actual drop" outcome added to README and PREDICTIONS_RESULTS.md |
| Soft liquidation percentage is an oracle-lag artefact | Repairable | Text and C5 now say the sign is not interpretable. P26 flagged for caution. Weak test list not changed after the fact |
| Price direction deviation not disclosed | Repairable | "Deviations from the pre-registration" section added to README |
| "Eight hours later" wrong | Repairable | Now "six hours after the low" |
| Concentration understated | Repairable | Sender 14%, destination contract 17%, top five transactions 40% |
| Wording and number fixes (4.26M phrasing, dust liquidations, ETH start price, BTC timing, 0.033% reference line in C5, "lowest sampled", missing files, "probably local time", hits excluding weak tests) | Cosmetic | All applied |

This check's concentration figures differed slightly (20% destination, 46% top five) because it measured the Curve pool leg only. The repo reports the combined YB classes, computed in recompute.py.

## Recompute check

This check worked on a clean copy. It deleted data/ and charts/, re-ran `python3 -I code/recompute.py` (exit 0, no failed checks), and got a byte-identical data/SHA256SUMS and identical PNGs. It traced every number in the README and the write-up to data/results.json, the CSVs or the raw files. It checked every chart against the data, every cited URL by HTTP status, the style rules, and the pre-registration hashes. Verdict before fixes was FAIL with 3 blocking issues. All are fixed.

| Finding | Blocking | Change |
|---|---|---|
| 6 cited URLs returned 404 (Curve resources pages moved, two YB doc paths moved, audit PDF renamed) | Yes | Replaced with live pages and re-checked the quoted text on each. The "<0.1% per day" soft liquidation figure is no longer on any live page and could not be checked on an archive, so it was removed from C5 and kept in DOCS_FIRST.md only as read on 2026-11-09. The old YB user page conflict is no longer on the live page and the row was rewritten |
| C2 label ran off the canvas | Yes | Moved inside the plot |
| This section was promised but missing | Yes | Added |
| "P12 would hit" had no measurable source in a single 15 minute bucket | No | Now stated on the 21:45 to 04:00 window, from data/flows_15m.csv |
| "Other definitions" range left out V1 | No | Now "other full-window definitions" |
| C5 "all after 22:02 while the oracle was still falling" | No | Now "between 22:02 and 23:05, almost all while the EMA oracle was still falling" |
| Stale status line in DOCS_FIRST.md, "documented versus measured" wording, DOCS_FIRST hash note, WETH share wording, 21:45 versus 21:41 in C3 | No | Fixed |
| SVGs were not byte-reproducible (embedded date) | No | Date metadata removed and svg.hashsalt fixed |
| C6 is portrait (2400x3200) | No | Kept. It is a table, not a 16:9 or 1:1 chart |
| PREDICTIONS.md P13 has a mid-sentence colon | No | Left as is. The file is hash-locked |

Coverage. Exhaustive for the recompute, checksums, imports, pre-registration hashes, every number in the text, the 30-day raw file, all URL statuses, all chart images, and the style scans. Spot-checked for page content behind the governance forum (G2, G3, G5 not opened, because the forum serves a bot challenge that was not bypassed) and the audit PDF contents.

## Note on DOCS_FIRST.md

DOCS_FIRST.md was edited after its first hash (PREREG_SHA256.txt) to add the raw text check results (section 5) and to restate the method note. The documented-versus-measured table and the reading list were not changed. PREDICTIONS.md and PREREG_ADDENDUM.md were not edited.

## Corrections, round 3

| Finding | Change |
|---|---|
| C3 showed "Liquidity providers, net sold 2.05M" and the write-up ignored it | All 52 legs in that class are liquidity events, not swaps (2.19M deposited, 0.13M withdrawn). Panel relabelled "Liquidity deposits and withdrawals, net deposited 2.05M, not swaps" and drawn in gray. README and write-up now explain the 1.91M pyUSD deposit and its price effect (pyUSD pool 0.9956 to 0.9953, weighted price 0.15 bp). Computed in recompute.py (liquidity_non_pk_detail) |
| C3 title 3.85M versus panel 3.90M | Subtitle now states 3.85M = 3.90M sold through the Curve pool leg minus 0.05M bought through the LEVAMM leg |
| Closing paragraph of the write-up implied cause ("that pushed the peg down") | Rewritten as co-occurrence, with the limit stated |
| "traded below 1 for weeks" had no number | Measured. Aggregator price below 1 in 119 of 121 six-hourly samples over 30 days, all 40 since 30 October (context_aggregator_30d in results.json) |
| Short summary gave 4.10M without context, used hyphen bullets and "Sunday's" | Rewritten |
| Pre-registered hour band in the square summary image | A version without the band, C3_flows_by_class_square_post. Repo versions keep it |

## Corrections, round 4

The 1.91M deposit at 23:38:11 UTC (block 26,373,494) into the pyUSD PegKeeper pool. All values read by archive eth_call and decoded in recompute.py (liquidity_non_pk_detail.largest in results.json).

| Item | Value |
|---|---|
| Amounts added (AddLiquidity event) | 1,908,183 crvUSD and 235,801 pyUSD. Not single-sided. The earlier "single-sided" wording was wrong and is corrected |
| Pool balances at block 26,373,493 | 152,152 pyUSD, 1,139,822 crvUSD (pyUSD share 11.8%) |
| Pool balances at block 26,373,494 | 392,760 pyUSD, 3,043,174 crvUSD (pyUSD share 11.4%). The pyUSD side also includes a 4.8k pyUSD swap in the same block |
| Pool A | 2000 |
| Pool price (get_p, crvUSD in pyUSD) | 0.995601 to 0.995327, a 2.7 bp move |
| Weight definition | Pool TVL share at block 26,372,407 (before the window), both coins at 1 USD, fixed for the window. pyUSD pool 1.17M of 37.24M, 3.1% |
| Weighted price | 0.996011 to 0.995996, a 0.149 bp move |

Why the move is small. The deposit roughly tripled the pool but kept its mix close to the existing 88% crvUSD, and A of 2000 makes the curve flat near balance. Why 0.15 bp and not under 0.01 bp. 0.996011 minus 0.995996 is 0.0000149, which is 0.149 bp. The "under 0.01 bp" figure in a suggested wording from the adversarial check was a units slip. It never entered the README, the write-up or the charts.

Fixed weights are a pre-registered choice. After the deposit the pyUSD pool held about 3.4M, so with live TVL weights its share would be higher, but its own price moved only 2.7 bp, so the weighted effect would still be well under 1 bp.

Deposit contribution versus block change. The pool moved 2.7 bp and carries 3.14% of the weight, so the deposit's own contribution to the weighted price is about 0.09 bp. The 0.149 bp is the weighted price change across the whole block, which includes the other pools. The write-up and README now say "less than 0.2 basis points in that block". The 4.8k difference between the amounts added and the change in pool balances is a swap of about 4.8k pyUSD for crvUSD in the same block.

Legs versus transactions. The liquidity class has 52 pool legs in 45 transactions (some transactions touch more than one pool). C3 and the README now say "52 legs in 45 tx".

## Corrections, round 5

| Change | Detail |
|---|---|
| Write-up drafts removed from the repo | The repo holds the study only |
| Framing | The Yield Basis LEVAMM leg was close to flat (net bought 0.05M). The selling went through the Curve crvUSD pools where Yield Basis is the LP, 3.64M of the 3.85M through the BTC pools. The README now states the mechanism in those terms. No number changed |
| C3 title and labels | Now "Selling through Curve crvUSD pools where Yield Basis is the LP, mostly BTC". Panels renamed "Curve pools, Yield Basis as LP" and "Yield Basis LEVAMM leg" |
| What to watch | New context read at block 26,372,407 (code/fetch/fetch_context_watch.py, raw in code/raw/context_watch.json, computed in results.json under watch). PegKeeper debt 0 against ceilings of 324M. Aggregator price last at or above 1 on 13 October in six-hourly samples, 26.3 days before the window. crvUSD in the four active Yield Basis pools 84.0M, crvUSD in the five PegKeeper pools 30.8M |

## Phase 1b

### Scope of the Blockscout completeness check (rule fixed 2026-11-09, 17:39 UTC)

The Blockscout check is limited to a fixed subset of three events, because the Blockscout quota allows only a few events per hour.
- E01, already checked.
- The two other events with the most crvUSD Transfer logs into and out of the peg pools in the RPC logs (crvusd_to_pools plus crvusd_from_pools). The choice uses this count only, read after the RPC fetch of all ten events is complete. Ties go to the earlier event.
- Each of the two is queried once when it is due. If Blockscout answers with HTTP 429, that event is reported as not checked. The script does not wait for the quota to reset.
- The other seven events are checked against the RPC only. For every event, that means full tiling of the window by the 100 block RPC responses, and the exact balance check: crvUSD.balanceOf of each peg pool at the last window block minus at the pre block, against the net of the fetched Transfer logs.

Disclosure. Before this rule was written, the phase 1b code was run on E01 and E02 to test it, and printed their metrics (T, the split by tag, the completeness counts). No other event's metrics had been computed. The rule above uses transfer counts only, so those two test runs cannot change which events are chosen. E01 had already been checked before the rule.

### Phase 1b checks and outcome

Order of work, each step committed and pushed before the next: addendum with the S rule and data sources, S candidate list (34 pools, 8 Yield Basis) with its hash, Chainlink fetch and event list with its hash, S membership per event with its hash, addendum 2 (log source roles), this check rule, then flows and metrics.

Mechanical checks in code/recompute_p1b.py, all passing:
- Event selection recomputed from the cached Chainlink logs equals the committed data/phase1b_events.json. The Chainlink responses tile the period with no gap (ETH 17,340 updates, BTC 13,443).
- For every event, the 100 block RPC responses tile the window with no gap for each of the six log queries.
- For every event, crvUSD.balanceOf of each peg pool at the last window block minus at the pre block equals the net of the fetched Transfer logs exactly, to the wei.
- E01, RPC against Blockscout: 503 transfers into the peg pools, 720 out, 1,135 S pool swaps, identical sets in both sources.

Blockscout subset. By the rule above, E03 (3,484 peg pool transfers) and E05 (3,039) were chosen. Blockscout answered HTTP 429 on the first attempt for both. They are reported as not checked. The other seven events are checked against the RPC only.

What the checks do not cover. The balance check covers the peg pool Transfer logs only. The S pool swap logs, which make D, were checked against a second source for E01 only.

Approximations and readings recorded here:
- In event selection the last block of a Chainlink price level is taken as 12 seconds before the next update. A missed slot just before an update would lengthen that level's 60 minute window by 12 seconds.
- E01 had four peg pools registered at its pre block, E02 to E06 four, E07 to E10 five.
- In E01, PegKeeper legs put 39.48M crvUSD into the peg pools during the window. They are excluded from N and from the class totals, as pre-registered.
- The large peg moves in E03 to E05 appear in every peg pool separately, not in one pool. Lows by pool: E03 0.967 to 0.977, E04 0.954 to 0.978, E05 0.936 to 0.959.
- P1B-09 rests on two Tricrypto-NG pools (crvUSD/tBTC/wstETH and crvUSD/WETH/CRV). T for those pools is defined in 5 events.

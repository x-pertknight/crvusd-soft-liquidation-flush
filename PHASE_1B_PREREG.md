# Phase 1b pre-registration

Recorded: 2026-11-09T15:12Z (UTC). Written before any phase 1b data was fetched. No price, flow or PegKeeper data outside the release 1 window (2026-11-08 20:00 to 2026-11-09 04:00 UTC) and the 30 day context samples in release 1 has been seen. This file is not edited after the first phase 1b fetch. Changes go in a dated addendum.

## Question

Release 1 found that, on 8 November 2026, selling through Curve pools that pair a volatile asset with crvUSD passed through to crvUSD selling in the PegKeeper pools, and that the Yield Basis LEVAMM leg was close to flat. Phase 1b asks whether this is a regular feature of large BTC and ETH drawdowns since Yield Basis launched, how much of the volatile asset selling turns into crvUSD selling, and how the peg moved each time.

## 1. Event selection

Prices. Chainlink BTC/USD and ETH/USD AnswerUpdated events (the feeds used in release 1), held constant between updates. Event selection uses these two feeds only. No crvUSD price, flow or PegKeeper data is used to select events.

Period. From the block of the first market creation event on the Yield Basis Factory 0x370a449FeBb9411c95bf897021377fe0B7D100c0 to 2026-11-09 04:00 UTC.

Drawdown. For each asset and each block, the decline from that block's price to the lowest price within the next 60 minutes.

Qualifying move. ETH decline of 5.0% or more, or BTC decline of 3.0% or more, within 60 minutes.

Clustering. Qualifying moves of the same asset less than 24 hours apart are one event. The event start t0 is the start of the largest 60 minute decline in the cluster. If a BTC and an ETH event start less than 2 hours apart, they are one joint event, with t0 the earlier start.

Cap. If more than 12 events qualify, keep the 6 largest BTC and the 6 largest ETH by decline. Joint events count for both assets.

8 November 2026. It qualifies (ETH fell 6.05% in 15 minutes) and is included. It is in-sample, so every result is reported with and without it.

Event window. From t0 minus 2 hours to t0 plus 6 hours, using block timestamps.

## 2. Pools and classes

Volatile crvUSD pools (set S). Every Curve pool that holds crvUSD and at least one of WBTC, cbBTC, tBTC, LBTC, WETH, wstETH, read at t0 from the Curve twocrypto-ng and tricrypto-ng factories plus the Yield Basis pools in code/contracts.json. The five PegKeeper pools are excluded. Each pool is tagged "Yield Basis LP" or "other".

Peg pools. The PegKeeper pools registered in PegKeeperRegulator at t0. If the set differs from release 1, the difference is reported.

Flow accounting. As in release 1. crvUSD Transfer logs into and out of the peg pools, net per transaction.

Classes. The release 1 rules in PREREG_ADDENDUM.md section 3, with one change. Rule 5 is widened to any TokenExchange in a pool in set S (class "S pool leg"), split by the Yield Basis LP tag.

## 3. Metrics per event

Primary metric, transmission ratio T. T = N / D.
- N is the net crvUSD flowing into the peg pools in the event window from transactions with a TokenExchange in set S in which the volatile asset was sold into the pool.
- D is the USD value of the volatile asset sold into set S pools in those same transactions, valued at the Chainlink price of that block.
- T is reported for all of set S, for the Yield Basis LP pools only, and for the other pools only.
- If D is under 0.5M USD, T is reported as "not defined" and the event is excluded from the T statistics.

Secondary metrics.
- Peg move. The lowest TVL-weighted PegKeeper pool price in the window minus the weighted price at the window start, in basis points. Weights and price definition as in release 1, with weights fixed at the window start.
- Time below 0.997 in the window, in minutes.
- PegKeeper debt at the window start, total and per PegKeeper.
- LEVAMM leg net. Net crvUSD into the peg pools from release 1 class 4 transactions.
- N divided by the crvUSD balance of the peg pools at the window start.

## 4. Predictions

Each prediction is scored HIT, MISS or UNTESTABLE. Weak tests are marked and not counted as calibration evidence.

P1B-01. Between 4 and 15 events qualify before the cap. Confidence 0.6. Weak test.

P1B-02. The median T across events, all of set S, is between 0.4 and 0.9. Most crvUSD that comes out of set S pools in a sell transaction is sold into the peg pools in the same transaction. Confidence 0.55.

P1B-03. In at least 75% of events, the absolute LEVAMM leg net is under 25% of the absolute S pool leg net. Confidence 0.65.

P1B-04. In the median event, Yield Basis LP pools account for at least 60% of N. Confidence 0.6.

P1B-05. The Spearman correlation across events between N divided by peg pool crvUSD balance and the absolute peg move is at least 0.5. Confidence 0.5.

P1B-06. Events with total PegKeeper debt under 1M at the window start have a larger median absolute peg move than events with 5M or more, by at least 10 basis points. UNTESTABLE if either group has fewer than 2 events. Confidence 0.55.

P1B-07. The 8 November 2026 T lies between the 25th and 75th percentile of the other events' T. Confidence 0.5.

P1B-08. No event has N above 25M crvUSD. Confidence 0.75. Weak test.

P1B-09. In at least 75% of events, T for the Yield Basis LP pools and T for the other pools are within 0.25 of each other, in events where both are defined. This is the direct test of "whoever owns the liquidity". UNTESTABLE if fewer than 3 events have both defined. Confidence 0.5.

## 5. Data source and feasibility

The free RPC used in release 1 does not serve eth_getLogs for blocks more than about 10,000 behind the chain head. Phase 1b needs logs going back months. Before any fetch, a source must be confirmed that serves historical eth_getLogs and archive eth_call at no cost and without a new account. If none is available, phase 1b stops and the gap is reported. The source is recorded in an addendum before the first fetch.

## 6. What phase 1b does not do

- It does not test the cross-protocol comparison (Aave v3, Fluid, Liquity v2, Morpho). That stays in phase 2.
- It does not attribute intent. Arbitrage and routed sales are not separated.
- It does not rank liquidation designs.

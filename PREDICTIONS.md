# Predictions

Recorded: 2026-11-09T10:16Z (UTC). Before any chain data was fetched.

Information available when writing. The docs listed in DOCS_FIRST.md. From the brief only, two crvUSD prints of 0.9951 and 0.9963, an ETH flush near 23:00 UTC on 2026-11-08, and the third party claim of net -4.10M crvUSD sold into peg pools by arbitrageurs via YB. No price chart, no on-chain data and no commentary on the event were viewed.

Rules. Entries are never edited. Each entry gets a result line after the run (HIT, MISS, PARTIAL, UNTESTABLE) plus the belief update. Failed predictions stay in this file. Confidence is my probability that the prediction holds.

## Event shape

P01. The steepest 15 minute ETH decline in the window falls between 22:30 and 23:30 UTC. Confidence 0.75.

P02. ETH peak to trough inside 2026-11-08 20:00 to 2026-11-09 04:00 UTC is between 5 and 12 percent. Confidence 0.5. This is a guess with little basis.

P03. The crvUSD minimum (block level spot, any PegKeeper pool) occurs within 45 minutes after the ETH trough, not before it. Confidence 0.7.

## crvUSD peg

P04. The block level minimum in at least one PegKeeper pool is below 0.9951. The 0.9951 print looks like an aggregated or sampled price, and single pool spot prices go lower than aggregates. Confidence 0.7.

P05. The block level minimum across PegKeeper pools is above 0.985. Confidence 0.8.

P06. Time below 0.997 (TVL weighted across PegKeeper pools) is between 30 minutes and 4 hours. Confidence 0.6.

P07. Time below 0.995 (same price) is under 60 minutes. Confidence 0.6.

P08. The weighted price is back above 0.999 by 2026-11-09 04:00 UTC. Confidence 0.45. Coin flip.

## Who sold and who bought crvUSD in the peg pools

P09. LLAMMA soft liquidation arbitrage is a net buyer of crvUSD in the peg pools during the flush, because collateral bought from LLAMMA is paid in crvUSD. Confidence 0.75.

P10. Hard liquidators in mint markets are net buyers of crvUSD. Confidence 0.8, conditional on at least 3 hard liquidations.

P11. YB related routes are the largest net seller class of crvUSD in the peg pools over the flush hour (22:30 to 23:30 UTC). Confidence 0.6.

P12. Inside the flush, the YB Curve pool leg (asset sold into YB pools, crvUSD taken out) leads the LEVAMM leg (crvUSD supplied to LEVAMM to cut debt) by at least 15 minutes on the median, because price_scale moves in capped steps. Confidence 0.55.

P13. All YB markets touched by the flush are over-leveraged (DTV above 50 percent) for most of the flush hour. So the LEVAMM leg is a crvUSD buyer, not a seller. The brief's warning applies: any YB selling must come from the Curve pool leg. Confidence 0.8.

P14. The -4.10M claim reproduces in sign. Confidence 0.65.

P15. The -4.10M claim does not reproduce within 25 percent once YB flows are netted across both legs and across all peg pools for the same window. My guess is that it counts the Curve pool leg gross, or uses a different window. Confidence 0.55.

P16. One address or a small set of addresses accounts for more than 50 percent of YB related crvUSD selling into peg pools. Confidence 0.6. Reported in aggregate only.

## PegKeepers

P17. PegKeepers withdraw crvUSD in at least 3 of the 4 pools (USDC, USDT, pyUSD, frxUSD) inside the window. Confidence 0.75.

P18. Total PegKeeper withdrawals inside the window are between 2M and 20M crvUSD. Confidence 0.5. Wide because I do not know current PegKeeper debt.

P19. At least one PegKeeper withdraws more than 80 percent of its window-start debt, so reserve depth binds as LlamaRisk warned. Confidence 0.35.

P20. The gap between successive withdraw actions on the busiest PegKeeper is set by action_delay, not by caller latency. Most gaps are within 2 minutes of the delay. Confidence 0.6.

P21. At least one update call in the window does nothing because the Regulator returns zero. Confidence 0.4.

## Borrow rate

P22. The WETH mint market rate at 04:00 UTC is higher than at 20:00 UTC by 15 to 100 percent in relative terms. Confidence 0.6.

P23. The rate peak lags the crvUSD price minimum by more than 30 minutes. Confidence 0.6.

## LLAMMA soft liquidation

P24. Across all mint markets, the peak count of loans in soft liquidation is between 10 and 150. Confidence 0.6.

P25. WETH and wstETH mint markets together account for more than 60 percent of collateral value converted to crvUSD in the window. Confidence 0.6. BTC markets only react to the extent BTC also fell.

P26. Aggregate soft liquidation loss in the window, defined as oracle value of collateral sold minus crvUSD received plus the same on any de-liquidation, is between 0.2 and 3 percent of the value converted. Confidence 0.55. Well above the "under 0.1 percent per day" figure, because that figure is for normal days.

P27. Loss per unit converted is higher in the fastest 30 minutes than in the rest of the window by at least a factor of 2. Confidence 0.6.

P28. Some loans lose health from de-liquidation after the bounce while their collateral value is higher than at the trough. At least 5 such loans. Confidence 0.5.

## Hard liquidations and bad debt

P29. Mint markets have 0 to 10 hard liquidations in the window. Confidence 0.7.

P30. No mint market has bad debt at window end. Confidence 0.85.

P31. Llamalend markets have more hard liquidations per 1M of debt than mint markets. Confidence 0.6.

## YB markets

P32. The WETH YB market (market 10) shows a larger DTV excursion from 50 percent than the BTC markets. Confidence 0.65.

P33. No YB market leaves the 6.25 to 53.125 percent safety band. Confidence 0.85.

P34. The crvUSD depeg itself lowers YB LP oracle values, since the oracle multiplies by the crvUSD aggregator price. The effect is under 1 percent of LP value. Confidence 0.8.

## Comparison and thesis

P35. On borrower loss for positions that would have been hard liquidated elsewhere at the same LTV, crvUSD borrowers lose less than Aave v3 borrowers. Confidence 0.65.

P36. On borrower loss across all positions per unit of collateral drawdown, crvUSD is not best when the drawdown is small, because positions inside bands lose money in soft liquidation while Aave positions above health factor 1 lose nothing. Confidence 0.55.

P37. Bad debt is zero or close to zero in all compared systems. So bad debt cannot rank them in this event. Confidence 0.75.

P38. crvUSD shows a larger peg deviation in the window than BOLD (Liquity v2) and GHO. Confidence 0.5.

P39. The final verdict on "best liquidation system in DeFi" is "not supported by one event". A single flush will not support a ranking on more than one or two metrics. Confidence 0.8.

## Results

To be filled after the run. One line per prediction plus the belief update.

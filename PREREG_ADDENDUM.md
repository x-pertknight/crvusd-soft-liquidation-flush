# Pre-registration addendum

Recorded: 2026-11-09T12:18Z (UTC). Written before any event logs or block-level prices from the analysis window were fetched. PREDICTIONS.md (recorded 2026-11-09T10:16Z, SHA256 1e62bf742b4f70a46178cee7e242c403e7e7a26a685feb86056b843dfbf84444) is not edited. This file fixes windows, definitions and attribution rules. Where it narrows a prediction, the narrower definition applies when the prediction is scored.

## 0. What was seen before this addendum

- Block headers only, to map timestamps to blocks (section 1).
- Current contract state at block 26,377,273 (2026-11-09, after the event), read to list contracts. It showed debt() = 0 for all five PegKeepers (USDC, USDT, pyUSD, frxUSD, GHO). This says nothing about debt at the window start. It is disclosed because it bears on P17 to P19.
- The registry lists five PegKeepers, not the four assumed in PREDICTIONS.md. P17 is scored as written ("at least 3 of the 4 pools USDC, USDT, pyUSD, frxUSD"). The GHO pool is included in every flow and price measure.
- No primary source was found for the 0.9951 and 0.9963 prints or for the -4.10M claim (section 6).

## 1. Windows

| Window | UTC start | UTC end (exclusive) | First block | Last block (inclusive) |
|---|---|---|---|---|
| Main | 2026-11-08 20:00:00 | 2026-11-09 04:00:00 | 26,372,408 | 26,374,799 |
| Flush hour | 2026-11-08 22:30:00 | 2026-11-08 23:30:00 | 26,373,155 | 26,373,453 |

A block belongs to a window if its timestamp is in [start, end). Every prediction and every figure uses these two windows unless the figure says otherwise. The flush hour was fixed in PREDICTIONS.md (P11) before any price data was seen. It is not moved after the data is seen, even if the trough falls outside it. If it does, that is reported.

The 7 day baseline in the original brief is dropped from release 1.

## 2. Prices

Pool price. For each PegKeeper pool, crvUSD price in the paired coin at the end of block b is p_i(b) = 10^36 / P_i(b), where P_i(b) is the Regulator's own _get_price for that pool (pool.get_p(0) if include_index, else pool.get_p(), inverted if is_inverse). That is the price of the paired coin in crvUSD, as the PegKeeper system sees it. Before use, the direction is checked on the data. A block in which crvUSD is only sold into a pool must lower p_i. If the check fails, the definition is flipped and the flip is logged.

Evaluation blocks. p_i is read by archive eth_call at the block before the window start and at every window block in which that pool emitted any log. Between those blocks the price is held constant.

Paired coins (USDC, USDT, pyUSD, frxUSD, GHO) are valued at 1 USD. No adjustment for their own deviation.

Weighted price. W(b) = sum over pools of w_i times p_i(b). The weight w_i is the pool's TVL share at block 26,372,407 (the block before the window), with TVL = sum of both coin balances at 1 USD each. Weights are fixed for the whole window.

Time below a level. The seconds of block time for which W(b) is below the level, treating W as constant from block b to block b+1. The same rule is used per pool.

Minimum. The lowest p_i(b) over all pools and window blocks, and the lowest W(b).

Recovery time. The time from the block of the minimum W to the first later block with W at or above 0.999. If that never happens in the window, it is reported as "not recovered by 04:00 UTC".

ETH price. Chainlink ETH/USD AnswerUpdated events from the aggregator behind proxy 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419. They are held constant between updates. Chainlink updates on a deviation threshold or heartbeat, so the path is coarse. This is stated on every chart that uses it.

## 3. Flows in the peg pools

Unit of measurement. crvUSD Transfer logs where from or to is a PegKeeper pool, in window blocks. For each transaction and pool, net_in = crvUSD sent to the pool minus crvUSD sent out by the pool. Positive net_in means crvUSD went into the pool (sold or deposited). Negative means it came out (bought or withdrawn). The claim's phrase "net -4.10M sold" maps to net_in = +4.10M.

Leg type. A pool leg is a swap if the pool emitted a TokenExchange in that transaction. It is liquidity if the pool emitted only AddLiquidity or RemoveLiquidity events in that transaction. Event signatures are taken from the pool source code and checked against topic0 values seen in the logs.

Actor classes. Each transaction is assigned one class. The first rule that matches wins.

1. PegKeeper. Any pool leg whose crvUSD counterparty in the Transfer log is a PegKeeper contract. Only that leg is assigned PegKeeper. Other legs in the same transaction go through rules 2 to 8.
2. Hard liquidation. The transaction contains a Liquidate event from a crvUSD mint market Controller or a Llamalend v1 Controller.
3. LLAMMA arbitrage. The transaction contains a TokenExchange from a mint market LLAMMA or a Llamalend v1 LLAMMA.
4. YB LEVAMM leg. The transaction contains any log emitted by a Yield Basis LEVAMM or VirtualPool (markets 0 to 10 in the YB contract list).
5. YB Curve pool leg. The transaction contains a TokenExchange from a Yield Basis Curve pool (markets 0 to 10).
6. Borrower action. The transaction contains Borrow, Repay or RemoveCollateral from a mint market or Llamalend v1 Controller.
7. Liquidity (non-PegKeeper). All remaining pool legs in the transaction are liquidity legs.
8. Other. Everything else, including aggregator and MEV transactions with none of the legs above.

Contract sets. Mint markets come from ControllerFactory 0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC. Llamalend v1 markets come from the factory 0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0. YB contracts come from the Yield Basis contract address page and are confirmed with Factory.markets(i) on 0x370a449FeBb9411c95bf897021377fe0B7D100c0. Every address with its source goes in code/contracts.json.

Multi-class transactions. A transaction that matches more than one of rules 2 to 6 keeps the first match. The count and the net_in of such transactions are reported, by combination of matched rules.

Addresses in several classes. Classes are per transaction, not per address. One address can appear in several classes. No address is ever named in outputs.

Cross-transaction sensitivity (S1, not the main result). Arbitrage can be split across transactions. In S1, a transaction in class 8 is moved to "YB linked (cross-transaction)" if its tx.from or tx.to also sent a class 4 or class 5 transaction in the main window.

Concentration. For each class, the share of |net_in| from the largest single tx.from address is reported as a percentage, without the address.

## 4. Reconciliation of the -4.10M claim

Measured variants. All are computed and all are shown.
- V0 (main). YB classes 4 plus 5, same-transaction rule, main window, all five pools, net.
- V1. As V0, flush hour only.
- V2. As V0, gross. Only transactions with positive net_in.
- V3. As V0, plus the S1 cross-transaction reclassification.
- V4. As V0, USDC and USDT pools only.
- V5. Class 5 only (YB Curve pool leg), main window, net.

Verdict rule. "Reproduces" if V0 is within 10 percent of +4.10M. "Reproduces only under variant X" if V0 fails and X is within 10 percent, with X named. "Sign reproduces" if V0 is positive but outside 10 percent. "Does not reproduce" if V0 is zero or negative. Whatever the claim's own definition turns out to be, this verdict uses the rule above.

The waterfall (chart C4) starts at the claim, then shows the adjustment from each definitional step, ending at V0.

## 5. PegKeepers (Q2)

Debt path. debt() by archive eth_call at block 26,372,407, then plus Provide amounts and minus Withdraw amounts in block order. This is checked against debt() read at block 26,374,799. A mismatch above 1 crvUSD fails the recompute.

Share withdrawn. Total Withdraw amount in the main window divided by window-start debt, per PegKeeper and in total.

Reserve depth binds. For one PegKeeper, if its debt falls below 1 percent of its window-start debt, or below 1,000 crvUSD, at any block where W is below 0.999. For the system, if total PegKeeper debt falls below 5 percent of its window-start total under the same price condition. If window-start total debt is under 100,000 crvUSD, the result is reported as "no reserves to deploy", not as binding.

Blocked calls. A PegKeeper call blocked by the Regulator reverts and leaves no log. Release 1 does not scan reverted transactions. P21 is therefore UNTESTABLE in release 1.

## 6. Inputs from the brief

| Input | Status at 12:18Z |
|---|---|
| Flush near 23:00 UTC on 2026-11-08 | Unverified. To be measured from Chainlink ETH/USD |
| crvUSD prints 0.9951 and 0.9963 | Unverified. No primary source found. Source, timestamp and price definition requested from Marco |
| "net -4.10M crvUSD sold into peg pools by arbs via YB" (crvtraders) | Unverified. No primary source found. Original post, window and definition requested from Marco. Until then the claim is treated as a third-party number with an unknown definition |

## 7. Soft liquidation (chart C5)

For each mint market LLAMMA TokenExchange in the main window, collateral is valued at amm.price_oracle() read at that block, and crvUSD at 1. Value converted = collateral bought by arbitrageurs from the AMM times price_oracle. Loss = value that left the AMM minus value that entered it, summed over all exchanges in the market, including de-liquidation. Loss is shown as a percent of value converted. The docs figure "<0.1% per day" is shown with its 8 hour pro rata value of 0.033 percent, labelled as a per-day figure.

## 8. Prediction scoring notes

Weak tests. These are scored but not counted as calibration evidence. P02 and P08 were coin flips. P05, P30, P33 and P34 had wide bounds or high base rates.

Out of scope for release 1, marked UNTESTABLE. P21 (blocked calls, see section 5), P24 and P28 (per-user soft liquidation state), P31 (Llamalend per debt), P35 to P38 (cross-protocol comparison, moved to phase 2), P39 (meta).

Scored with the definitions above. P04 to P08 use section 2. P09 to P16 use sections 3 and 4. P17 to P20 use section 5. P26 and P27 use section 7. P12 uses the median block gap between class 5 and class 4 net flow peaks, computed on 15 minute buckets of the flush hour. P13 uses DTV = LEVAMM get_debt() divided by collateral value at the LP oracle, read at every block with a LEVAMM log. P22 and P23 use WETH mint market rate() and W.

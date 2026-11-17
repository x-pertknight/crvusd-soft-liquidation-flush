# Release 2 pre-registration addendum

Recorded: 2026-11-16, before the first release 2 data pull (no RPC, explorer, Sourcify or API call has been made for release 2 yet). PREDICTIONS_R2.md and DOCS_FIRST_R2.md are not edited. Their hashes are in PREREG_R2_SHA256.txt. This file is hashed in PREREG_R2_ADDENDUM_SHA256.txt.

Gate 1 was approved with five conditions. This file fixes how each is carried out.

## 1. Deployed source first
- Order of work: (1) read `regulator.aggregator()`, the Regulator's PegKeeper list, and each PegKeeper's `regulator()`; (2) fetch the verified source of the deployed Regulator, the five PegKeepers and the aggregator the Regulator points to, from Sourcify first, a block explorer second; (3) save the raw files under `code/raw/source_r2/`; (4) diff them against section 2 of DOCS_FIRST_R2.md; (5) only then pull time series.
- Every difference is logged in `SOURCE_DIFF_R2.md`: what the excerpt said, what the deployed code says, and which predictions use the premise.
- If a difference changes a prediction's premise, the prediction line in PREDICTIONS_R2.md stays as written and is scored as written. The log names the prediction and says the premise failed. DOCS_FIRST_R2.md is not edited. If the deployed code differs, the corrected reading goes in SOURCE_DIFF_R2.md and every later step uses it.
- If a verified source cannot be fetched for a contract, that contract is reported as bytecode-only and any claim about it is marked unverified.

## 2. Decomposition of the slow drain
Universe. Every sampled block where a PegKeeper had debt above 1 crvUSD and the aggregator price (`regulator.aggregator().price()` at that block) was below 1. Each block gets exactly one state, assigned in this order, first match wins:

| State | Test at the block, from archive reads |
|---|---|
| (g) drained | Debt at the next sample is lower than debt at this block. Drain happened, so the block does not show a hold. Added to the five states from the gate 1 message so shares sum to 100% (see below) |
| (a) provide side | `POOL.balances(other) * PEG_MUL > POOL.balances(crvUSD)`, so update() takes the provide branch and reverts with "Regulator ban" |
| (e) withdraw paused | Withdraw side, and `regulator.is_killed()` has the Withdraw bit set |
| (d) outside band | Withdraw side, not paused, and `withdraw_allowed()` returns 0, which with price below 1 means the spot price is outside `price_deviation` of the oracle price. The band is recomputed from get_p and price_oracle to confirm |
| (b)/(c) allowed | Withdraw side, not paused, `withdraw_allowed()` is above 0, and debt did not fall. A call either did not land (b) or landed and reverted as unprofitable (c) |

Why (g) is added. The five states in the gate 1 message explain why debt was held. A sampled block in which debt then fell is not a hold, and forcing it into one of the five would be wrong. Shares are reported two ways: all six states summing to 100%, and the five hold states summing to 100% with (g) excluded. Both are given. Nothing else is added.

(b) versus (c) is separable only if a public source lists failed transactions to the PegKeeper (section 4). Otherwise they are reported together as "(b)/(c) not separable". The "peg unprofitable" revert cannot be tested by eth_call on a past block without a trace, so the split is not attempted through simulation.

Edge case recorded now: a sampled block where the pool is exactly balanced counts as withdraw side, as in the contract (`else` branch), where the amount is zero. It is assigned (b)/(c).

## 3. Sampling
- Main series, whole window from 2026-09-01 00:00 UTC to the latest block: hourly. The first block at or after each hour is read for aggregator price and for every PegKeeper: debt, pool balances, get_p, price_oracle, `withdraw_allowed()` and `provide_allowed()` (view calls on the Regulator, made as the PegKeeper address).
- USDT drain period, from 2026-10-13 00:00 UTC to the first block at which USDT debt is under 1 crvUSD: at least hourly (the same series), plus a read of pool balances, price and the Regulator allowances at the block before every Withdraw event of the USDT PegKeeper in that period. If event logs for that period cannot be read, this is stated as a limitation and debt steps between hourly reads are used to date the Withdraws.
- Event logs come first from the RPC. Release 1 recorded that logs older than about 30 days were not available on the free plan. If the RPC refuses, a block explorer log API is the second source. If neither works, event-based predictions (R2-04, R2-09, R2-12, R2-20) are UNTESTABLE or are scored from debt steps and labeled as such.

## 4. Failed update() calls
- Attempt: a block explorer transaction list per PegKeeper address (Blockscout public API first, as used in phase 1b), including failed transactions (`isError`, status), for the whole window.
- If a source lists failed calls, count reverts with their revert reason where given, and use them to split (b) and (c).
- If none does, say so plainly as a limitation, and report (b) and (c) as not separable.
- Phase 1b recorded that Blockscout throttles with HTTP 429. A refusal is reported as not checked. The script does not wait through repeated blocks beyond a bounded retry (at most three retries, with waits).

## 5. Wording
- "Why" claims are tied to the measured decomposition and use "consistent with" unless a state share is the direct measure.
- The "below peg on 16 November" claim is stated with the block number and timestamp measured, not the calendar date alone.
- "All five at zero on 16 November" likewise carries the block number and timestamp.

## 6. Other fixed choices
- Zero means under 1 crvUSD, as in PREDICTIONS_R2.md.
- Data order: Curve prices API for its own price series, then RPC, then Blockscout or Sourcify for source and transaction lists. No Dune.
- No release 1 file is edited. New code goes in code/fetch/r2_*.py and code/recompute_r2.py, new outputs in data/r2_* and charts/R2_*.
- A rerun never overwrites published charts, as in release 1 (UPDATE_CHARTS).

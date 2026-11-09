# Phase 1b addendum

Recorded: 2026-11-09T15:45Z (UTC). Written before any phase 1b pool, price, flow or PegKeeper data was fetched. The only phase 1b network calls made before this file were the feasibility tests: a few Blockscout and RPC log queries on the release 1 pools, the release 1 window and two 1,000 block ranges, and pool_count() on the two factories below. No other event window was looked at. PHASE_1B_PREREG.md is not edited. Where this file makes the pre-registration more precise, this file governs. It does not change any prediction, threshold or metric definition.

## 1. Data sources (PHASE_1B_PREREG.md section 5)

- Logs and block numbers by time. Blockscout Ethereum API, https://eth.blockscout.com/api, module=logs action=getLogs and module=block action=getblocknobytime. No API key, no account.
- Archive state. eth_call on https://eth.drpc.org, as in release 1.
- Second source for the completeness checks. eth_getLogs on https://eth.drpc.org in ranges of 100 blocks, the largest range it accepts on the free plan.
- Rate. At most 2 requests per second to each source. Retries with backoff on HTTP 429, HTTP 500 and timeouts. A Blockscout response with 1,000 results is treated as truncated and its block range is split in two until every part returns fewer than 1,000.
- Storage. Every raw response is saved under code/raw/phase1b/ as gzip JSON, with the request (URL and parameters, or the JSON-RPC payload) and the block range. recompute.py rebuilds every phase 1b number from these files without network access.

## 2. Pool set S, by rule

Candidates. Every pool listed by pool_list(i) for i below pool_count() on these two factories, read at reference block 26,378,000 (after every possible event window):
- Curve Twocrypto-NG factory 0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F
- Curve Tricrypto-NG factory 0x0c0e5f2fF0ff18a3be9b835635039256dC4B4963

Both addresses are the Ethereum factories given in the Curve developer docs (Twocrypto-NG and Tricrypto-NG integration pages). Plus every Yield Basis pool in code/contracts.json (markets 0 to 10), whether or not a factory lists it.

Pairing. A candidate is kept if get_coins(pool) on its factory (coins(i) for Yield Basis pools) contains crvUSD 0xf939e0a03fb07f59a73314e73794be0e57ac1b4e and at least one of these tokens:
- WBTC 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599
- cbBTC 0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf
- tBTC 0x18084fbA666a33d37592fA2633fD49a74DD93a88
- LBTC 0x8236a87084f8B84306f72007F36F2618A5634494
- WETH 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
- wstETH 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0

Each symbol is checked with symbol() before use. The candidate list after the pairing rule is written to code/raw/phase1b/s_candidates.json, and its SHA256 is appended to PREREG_SHA256.txt and committed before any event flow is fetched.

Membership per event. A candidate is in S for an event if crvUSD.balanceOf(pool) is at least 50,000 crvUSD at the block before the event window. A pool not yet deployed has a balance of zero and is out. The five PegKeeper pools registered at that block are excluded. Membership for every event is written to code/raw/phase1b/s_members.json, hashed and committed before any event flow is fetched.

Tag. A pool is "Yield Basis LP" if its address is a Yield Basis pool in code/contracts.json. Every other member is "other".

## 3. Event selection, made precise

- Price points. Every AnswerUpdated log from every aggregator that the Chainlink ETH/USD proxy 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419 and BTC/USD proxy 0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c pointed to during the period. The aggregators are read with aggregator() at the start and end of the period and phaseAggregators() for any phase in between. The time of a price point is the block timestamp of its log.
- Period start. The block of the earliest log from the Yield Basis Factory 0x370a449FeBb9411c95bf897021377fe0B7D100c0 that names the market 0 pool or LEVAMM address. That log is recorded.
- Decline. A price level starts at update i and holds until update i+1. A block inside that level can start a 60 minute window anywhere up to the last block before update i+1. So the decline of level i is p_i minus the lowest later price with a timestamp no more than 3,600 seconds after the last block of the level, divided by p_i. The start of the decline is the latest of the level start and the time of that lowest price minus 3,600 seconds.
- Clustering. Qualifying declines of one asset whose starts are less than 24 hours apart, chained, form one event. t0 is the start of the largest decline in the chain.
- Joint events. A BTC event and an ETH event with t0 less than 2 hours apart form one joint event, t0 the earlier. A joint event ranks in the BTC list by its BTC decline and in the ETH list by its ETH decline.
- Cap. If more than 12 events qualify, the selection is the union of the 6 largest BTC events and the 6 largest ETH events. 8 November 2026 is kept in any case, as pre-registered.
- Window. First block with timestamp at or after t0 minus 2 hours to the last block with timestamp before t0 plus 6 hours. The pre block is the block before the first window block.
- The selected event list is committed before any pool membership, flow, price or PegKeeper data is fetched.

## 4. Metrics, made precise

- Sold volatile asset. A TokenExchange log from a member of S in which sold_id is the index of one of the six tokens in section 2, whatever was bought.
- D valuation. WBTC, cbBTC, tBTC and LBTC at Chainlink BTC/USD, WETH at Chainlink ETH/USD, each at the latest update at or before the log's block. wstETH at ETH/USD times stEthPerToken() read at the pre block. Token decimals from decimals().
- N. Net crvUSD into the peg pools, summed over pools, in transactions with at least one sold volatile asset log. PegKeeper legs (rule 1) are excluded.
- Split by tag. In a transaction that sold into both Yield Basis LP pools and other pools, the transaction's N is split in proportion to the USD value sold into each group. T for a group is that group's N over that group's D. The 0.5M USD floor applies to each group's D separately.
- Classes. Release 1 rules. Rule 4 uses any log from a Yield Basis LEVAMM or VirtualPool. Rule 5 becomes "S pool leg", a sold or bought TokenExchange from any member of S. Rules 2, 3 and 6 use logs found by topic over all addresses and kept when the emitter is a mint market or Llamalend v1 Controller or LLAMMA in code/contracts.json.
- LEVAMM leg net and S pool leg net. Net crvUSD into the peg pools from rule 4 and rule 5 transactions, PegKeeper legs excluded.
- Peg pools. The PegKeepers and pools listed by PegKeeperRegulator 0x36a04CAffc681fa179558B2Aaba30395cDdd855f at the pre block. Price per pool as in release 1: get_p() or get_p(0), read at the pre block and at every block in which the pool emitted a log. Weights are pool balances at the pre block, both coins at 1 USD. If a pool has crvUSD as coin 0, or a getter fails, this is reported and the pool is left out of the price for that event.
- Time below 0.997. Seconds between consecutive weighted price change blocks, by block timestamp, up to the window end, counted when the weighted price is below 0.997. Reported in minutes.
- Peg pool crvUSD balance. crvUSD.balanceOf(pool) at the pre block, summed.
- Percentiles (P1B-07). Python statistics.quantiles with n=4 and method "inclusive".
- Spearman (P1B-05). Pearson correlation of ranks, ties given the average rank.
- With and without 8 November. Every prediction is scored on all events and on all events except 8 November. P1B-07 is scored once, by its definition.

## 5. Completeness checks per event

- Peg pool transfers. The set of crvUSD Transfer logs into and out of the peg pools from Blockscout must equal the set from the RPC (100 block ranges), compared by transaction hash, log index and data.
- S pool swaps. The set of TokenExchange logs from members of S, compared the same way.
- Balances. For every peg pool, crvUSD.balanceOf at the last window block minus at the pre block must equal the net of the fetched Transfer logs, exactly.
- A failed check is reported. The event's metrics are still computed and flagged.

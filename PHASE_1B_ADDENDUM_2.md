# Phase 1b addendum 2

Recorded: 2026-11-09T16:35Z (UTC). Written before any event flow data was saved or looked at. It changes the roles of the two log sources and nothing else. Pool set rule, event list, metrics, predictions and checks are unchanged.

## What happened

The event list (data/phase1b_events.json) and the S membership per event (code/raw/phase1b/s_members.json) were committed as planned. The flow fetch for the first event then ran into the Blockscout rate limit. After somewhere between 100 and 200 requests within the hour (the exact count was not logged), Blockscout answered every request with HTTP 429 and a reset time of about 37 minutes. The fetch was stopped. Its Blockscout responses were held in memory and never written or read. The only file written for that event holds archive state read at the pre block (PegKeeper list, debt, pool balances), and it was not opened.

At that quota the planned fetch would take many hours, with long blocks of refused requests.

## Change

- Primary log source becomes the RPC, https://eth.drpc.org, eth_getLogs in ranges of 100 blocks, with address lists and topic lists in one request where the filter allows. Same retries and the same limit of 2 requests per second.
- Blockscout becomes the second source for the completeness checks in PHASE_1B_ADDENDUM.md section 5: crvUSD Transfer logs into and out of each peg pool, and TokenExchange logs of each member of S. It is queried at a pace that stays inside its quota.
- The exact balance check (crvUSD.balanceOf of each peg pool at the last window block minus at the pre block, against the net of the fetched Transfer logs) is unchanged. It does not depend on either log source.
- If the Blockscout check for an event cannot be completed, the event keeps its metrics, the check is reported as not run, and this is stated in the results.

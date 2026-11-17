"""Release 2 final read: the latest block, its timestamp, the aggregator price, each PegKeeper's debt, and the Curve
prices API crvUSD price fetched right after. Gives the block number and timestamp for the 16 November claims.
Writes code/raw/r2_final.json."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, AGGREGATOR, batch_calls, batch_blocks, selector, rpc  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
head = int(rpc("eth_blockNumber", []), 16)
ts = batch_blocks([head])[0]
res = batch_calls([(p["pegkeeper"], selector("debt()"), head) for p in C["pegkeepers"]]
                  + [(AGGREGATOR, selector("price()"), head)])
req = urllib.request.Request("https://prices.curve.finance/v1/usd_price/ethereum/0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E",
                             headers={"user-agent": "crvusd-flush-study/0.1"})
api = {"fetched_at": int(time.time()), "body": json.loads(urllib.request.urlopen(req, timeout=60).read())}
out = {"block": head, "ts": ts, "debt_wei": [int(x, 16) for x in res[:5]], "agg_price_wei": int(res[5], 16), "api": api}
json.dump(out, open(os.path.join(ROOT, "code", "raw", "r2_final.json"), "w"))
print(out)

"""Context only, for the "What to watch" indicators: crvUSD and asset balances in the active
Yield Basis Curve pools and PegKeeper debt ceilings, read by archive eth_call at the block before
the window. Raw results go to code/raw/context_watch.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, enc_uint, enc_addr  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PRE = C["window"]["pre_block"]
FACTORY = "0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC"
out = {"block": PRE, "yb_pools": {}, "pegkeeper_debt_ceiling": {}}
for m in C["yb_markets"]:
    if m["status"] != "active":
        continue
    out["yb_pools"][f"{m['market']} {m['asset']}"] = {
        "pool": m["pool"],
        "coin0": call(m["pool"], selector("coins(uint256)") + enc_uint(0), PRE),
        "balance0": call(m["pool"], selector("balances(uint256)") + enc_uint(0), PRE),
        "balance1": call(m["pool"], selector("balances(uint256)") + enc_uint(1), PRE),
    }
for p in C["pegkeepers"]:
    out["pegkeeper_debt_ceiling"][p["name"]] = call(FACTORY, selector("debt_ceiling(address)") + enc_addr(p["pegkeeper"]), PRE)
json.dump(out, open(os.path.join(ROOT, "code", "raw", "context_watch.json"), "w"), indent=1)
print(json.dumps({k: int(v["balance0"], 16) / 1e18 for k, v in out["yb_pools"].items()}))

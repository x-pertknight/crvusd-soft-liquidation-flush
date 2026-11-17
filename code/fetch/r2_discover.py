"""Release 2 step 1. Read, at the latest block, which contracts the Regulator points to.
Writes code/raw/r2_discover.json. Network access lives only in code/fetch/."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, rpc, word, addr_word, enc_uint  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
REGULATOR = "0x36a04CAffc681fa179558B2Aaba30395CDdd855f"

head = int(rpc("eth_blockNumber", []), 16)
head_block = rpc("eth_getBlockByNumber", [hex(head), False])
out = {"block": head, "timestamp": int(head_block["timestamp"], 16), "regulator": REGULATOR}


def read(to, sig, block=head, args=""):
    """Raw eth_call result, or an error string if the getter does not exist."""
    try:
        return call(to, selector(sig) + args, block)
    except RuntimeError as e:
        return "ERR " + str(e)[:120]


reg = {}
for sig in ["aggregator()", "worst_price_threshold()", "price_deviation()", "alpha()", "beta()",
            "is_killed()", "admin()", "emergency_admin()", "fee_receiver()", "max_peg_keepers()"]:
    reg[sig] = read(REGULATOR, sig)
out["regulator_getters"] = reg

# peg_keepers(i): print the raw words, indexes 0..7, until the call fails
pks = []
for i in range(8):
    r = read(REGULATOR, "peg_keepers(uint256)", args=enc_uint(i))
    if r.startswith("ERR") or r == "0x":
        break
    pks.append(r)
out["regulator_peg_keepers_raw"] = pks

per_pk = {}
for p in C["pegkeepers"]:
    a = p["pegkeeper"]
    per_pk[p["name"]] = {sig: read(a, sig) for sig in
                         ["regulator()", "action_delay()", "debt()", "caller_share()", "last_change()",
                          "receiver()", "admin()", "POOL()", "pool()"]}
out["pegkeepers"] = per_pk

# the two aggregators listed in the docs page, for comparison with regulator.aggregator()
out["docs_aggregators"] = {
    "crvusd-price-aggregator": "0xe5Afcf332a5457E8FafCD668BcE3dF953762Dfe7",
    "crvusd-price-aggregator-v3": "0x18672b1b0c623a30089A280Ed9256379fb0E4E62"}
agg = addr_word(reg["aggregator()"], 0) if not reg["aggregator()"].startswith("ERR") else None
out["aggregator_address"] = agg
if agg:
    out["aggregator_price_now"] = read(agg, "price()")
    out["aggregator_sigma"] = read(agg, "SIGMA()")
    out["aggregator_min_liquidity"] = read(agg, "MIN_LIQUIDITY()")
    out["aggregator_tvl_ma_time"] = read(agg, "TVL_MA_TIME()")
json.dump(out, open(os.path.join(ROOT, "code", "raw", "r2_discover.json"), "w"), indent=1)
print(json.dumps(out, indent=1)[:6000])

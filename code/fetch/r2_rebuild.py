"""Release 2. What would let a PegKeeper rebuild debt: at every sampled hour where the aggregator price was at or
above 1, and at the final block, read for each PegKeeper both pool balances, provide_allowed() and the crvUSD it holds.
Writes code/raw/r2_rebuild.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, REGULATOR, batch_calls, selector, enc_addr  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PKS = C["pegkeepers"]
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
G = json.load(open(os.path.join(ROOT, "code", "raw", "r2_hour_blocks.json")))["hours"]
T1 = json.load(open(os.path.join(ROOT, "code", "raw", "r2_series", "tier1.json")))
FINAL = json.load(open(os.path.join(ROOT, "code", "raw", "r2_final.json")))["block"]
S = {n: selector(n) for n in ["balances(uint256)", "provide_allowed(address)", "balanceOf(address)"]}
blocks = [b for _, b, _ in G if int(T1[str(b)][5], 16) >= 10 ** 18] + [FINAL]
calls = []
for b in blocks:
    for p in PKS:
        calls += [(p["pool"], S["balances(uint256)"] + "0" * 64, b), (p["pool"], S["balances(uint256)"] + "0" * 63 + "1", b),
                  (REGULATOR, S["provide_allowed(address)"] + enc_addr(p["pegkeeper"]), b),
                  (CRVUSD, S["balanceOf(address)"] + enc_addr(p["pegkeeper"]), b)]
res = batch_calls(calls)
out = {"blocks": blocks, "final_block": FINAL, "reads": {str(b): {p["name"]: res[(i * 5 + k) * 4:(i * 5 + k) * 4 + 4]
                                                              for k, p in enumerate(PKS)} for i, b in enumerate(blocks)}}
json.dump(out, open(os.path.join(ROOT, "code", "raw", "r2_rebuild.json"), "w"))
print("blocks", len(blocks))

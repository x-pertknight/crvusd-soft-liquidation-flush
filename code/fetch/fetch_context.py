"""Context only, outside the pre-registered measures: PegKeeper debt() sampled every 1,800 blocks
(about 6 hours) over the 30 days before the window, by archive eth_call. Shows how long the
PegKeepers had held little or no debt. Event logs that old are not available on the free RPC plan."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, rpc  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PRE = C["window"]["pre_block"]
START = PRE - 216_000
blocks = list(range(START, PRE + 1, 1800)) + [PRE]
out = {"start_block": START, "step": 1800, "debt": {}, "block_timestamps": {}}
for p in C["pegkeepers"]:
    out["debt"][p["pegkeeper"]] = {str(b): call(p["pegkeeper"], selector("debt()"), b) for b in blocks}
    print("done", p["name"], flush=True)
for b in blocks:
    out["block_timestamps"][str(b)] = rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"]
json.dump(out, open(os.path.join(ROOT, "code", "raw", "context_pegkeepers_30d.json"), "w"))
print("written", len(blocks))

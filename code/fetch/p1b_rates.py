"""Phase 1b, added after the results (VERIFICATION.md, phase 1b additions): WETH mint market borrow rate
in each event window. rate() on the market's LLAMMA, as in release 1, at the pre block, every 25 blocks,
at every block with a log from that market's Controller or LLAMMA in the cached class logs, and at the
last window block."""
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import State, ROOT, RAW  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
MEM = json.load(open(os.path.join(RAW, "s_members.json")))["events"]
weth = [m for m in C["mint_markets"] if m["name"] == "WETH"][0]
addrs = {weth["amm"].lower(), weth["controller"].lower()}
for eid in sorted(MEM):
    m = MEM[eid]
    pre, b0, b1 = m["pre_block"], m["first_block"], m["last_block"]
    with gzip.open(os.path.join(RAW, f"ev_{eid}_rpc_logs.json.gz"), "rt") as f:
        rec = json.load(f)["records"]["class_topic_logs"]
    ev_blocks = {int(lg["blockNumber"], 16) for r in rec for lg in r["response"]["result"] if lg["address"].lower() in addrs}
    blocks = sorted({pre, b1} | set(range(b0, b1 + 1, 25)) | ev_blocks)
    st = State(f"ev_{eid}_rates_state")
    for b in blocks:
        st.call(weth["amm"], selector("rate()"), b)
    st.flush()
    print(eid, len(blocks), flush=True)

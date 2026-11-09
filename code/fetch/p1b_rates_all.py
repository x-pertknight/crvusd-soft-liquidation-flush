"""Added after the results (VERIFICATION.md, external cross-check): borrow rate of every crvUSD mint
market in E04 and E05, rate() on each LLAMMA every 100 blocks plus the pre and last block."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import State, ROOT, RAW  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
MEM = json.load(open(os.path.join(RAW, "s_members.json")))["events"]
st = State("e04_e05_mint_rates_state")
for eid in ("E04", "E05"):
    m = MEM[eid]
    blocks = sorted({m["pre_block"], m["last_block"]} | set(range(m["first_block"], m["last_block"] + 1, 100)))
    for mk in C["mint_markets"]:
        for b in blocks:
            st.call(mk["amm"], selector("rate()"), b)
        st.flush()
    print(eid, len(blocks), flush=True)

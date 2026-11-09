"""Phase 1b step 3. Window blocks per selected event and S membership at the pre block
(PHASE_1B_ADDENDUM.md sections 2 and 3)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import bs_get, rpc, save, State, ROOT, RAW  # noqa: E402

CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
MIN_BAL = 50_000 * 10 ** 18
EV = json.load(open(os.path.join(ROOT, "data", "phase1b_events.json")))["selected"]
CAND = json.load(open(os.path.join(RAW, "s_candidates.json")))["candidates"]
st = State("members_state")
blocks_raw = {"blockscout": [], "rpc_blocks": {}}


def block_ts(b):
    body, out = rpc("eth_getBlockByNumber", [hex(b), False])
    blocks_raw["rpc_blocks"][str(b)] = {"request": body, "timestamp": out["result"]["timestamp"]}
    return int(out["result"]["timestamp"], 16)


def by_time(ts, closest):
    url, r = bs_get({"module": "block", "action": "getblocknobytime", "timestamp": ts, "closest": closest})
    blocks_raw["blockscout"].append({"source": url, "response": r})
    return int(r["result"]["blockNumber"])


out = {"rule": "PHASE_1B_ADDENDUM.md section 2", "min_crvusd_balance": 50_000, "events": {}}
for e in EV:
    b0 = by_time(e["window_start_ts"], "after")
    while block_ts(b0) < e["window_start_ts"]:
        b0 += 1
    while block_ts(b0 - 1) >= e["window_start_ts"]:
        b0 -= 1
    b1 = by_time(e["window_end_ts"], "before")
    while block_ts(b1) >= e["window_end_ts"]:
        b1 -= 1
    while block_ts(b1 + 1) < e["window_end_ts"]:
        b1 += 1
    pre = b0 - 1
    mem = []
    for c in CAND:
        h = st.call(CRVUSD, selector("balanceOf(address)") + c["pool"][2:].rjust(64, "0"), pre)
        bal = int(h, 16) if not h.startswith("ERR") else 0
        if bal >= MIN_BAL:
            mem.append({"pool": c["pool"], "yield_basis": c["yield_basis"], "crvusd_balance": bal / 1e18})
    st.flush()
    out["events"][e["id"]] = {"t0": e["t0"], "pre_block": pre, "first_block": b0, "last_block": b1, "members": mem}
    print(e["id"], pre, b0, b1, len(mem), sum(m["yield_basis"] for m in mem))
save("window_blocks", blocks_raw)
json.dump(out, open(os.path.join(RAW, "s_members.json"), "w"), indent=1, sort_keys=True)

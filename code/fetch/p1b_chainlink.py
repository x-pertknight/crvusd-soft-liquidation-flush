"""Phase 1b step 2. Period start from the Yield Basis Factory, Chainlink BTC/USD and ETH/USD
AnswerUpdated logs over the period, block numbers of the period bounds."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import bs_get, bs_logs, save, State, ROOT  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
T = json.load(open(os.path.join(ROOT, "code", "topics.json")))["topics"]
YB_FACTORY = "0x370a449febb9411c95bf897021377fe0b7d100c0"
PROXIES = {"ETH": "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419", "BTC": "0xf4030086522a5beea4988f8ca5b36dbc97bee88c"}
END_TS = 1794196800  # 2026-11-09 04:00 UTC

# period start
recs = []
first = bs_logs(0, 26_378_000, recs, address=YB_FACTORY)
m0 = C["yb_markets"][0]
needles = {m0["pool"].lower()[2:], m0["levamm"].lower()[2:]}
start_log = None
for lg in sorted(first, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16))):
    blob = (lg["data"] + "".join(t or "" for t in lg["topics"])).lower()
    if any(n in blob for n in needles):
        start_log = lg
        break
assert start_log, "no factory log names market 0"
START = int(start_log["blockNumber"], 16)
save("yb_factory_logs", {"records": recs})
url, endb = bs_get({"module": "block", "action": "getblocknobytime", "timestamp": END_TS, "closest": "before"})
END = int(endb["result"]["blockNumber"])
print("period", START, END)

st = State("chainlink_state")
aggs = {}
for asset, px in PROXIES.items():
    pid_s = int(st.call(px, selector("phaseId()"), START), 16)
    pid_e = int(st.call(px, selector("phaseId()"), END), 16)
    lst = []
    for pid in range(pid_s, pid_e + 1):
        a = "0x" + st.call(px, selector("phaseAggregators(uint16)") + hex(pid)[2:].rjust(64, "0"), END)[-40:]
        lst.append({"phase": pid, "aggregator": a})
    aggs[asset] = lst
    print(asset, lst)
st.flush()
out = {"period_start_block": START, "period_end_block": END, "end_ts": END_TS, "start_log": start_log,
       "aggregators": aggs, "end_block_source": url, "end_block_response": endb}
for asset, lst in aggs.items():
    recs = []
    logs = []
    for x in lst:
        logs += bs_logs(START, END, recs, address=x["aggregator"], topic0=T["AnswerUpdated"])
    save(f"chainlink_{asset.lower()}", {"records": recs})
    print(asset, "updates", len(logs))
save("period", out)

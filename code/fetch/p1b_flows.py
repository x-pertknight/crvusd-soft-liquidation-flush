"""Phase 1b step 4. Logs from the RPC (primary source, PHASE_1B_ADDENDUM_2.md) and archive state per
selected event (PHASE_1B_ADDENDUM.md sections 1 and 4). Resumable: an event whose files
exist is skipped. Usage: python3 code/fetch/p1b_flows.py [E01 E02 ...]"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import rpc, save, load, State, ROOT, RAW  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
TP = json.load(open(os.path.join(ROOT, "code", "topics.json")))["topics"]
MEM = json.load(open(os.path.join(RAW, "s_members.json")))["events"]
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
REGULATOR = "0x36a04caffc681fa179558b2aaba30395cddd855f"
WSTETH = "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
CLASS_TOPICS = ["Liquidate", "TokenExchange_llamma", "Borrow", "Repay", "RemoveCollateral"]
YB_ADDRS = sorted({a.lower() for m in C["yb_markets"] for a in (m["levamm"], m["virtual_pool"])})


def enc(x):
    return hex(x)[2:].rjust(64, "0") if isinstance(x, int) else x.lower()[2:].rjust(64, "0")


def pad(a):
    return "0x" + "0" * 24 + a.lower()[2:]


def rpc_logs(fb, tb, flt, records):
    out = []
    for s in range(fb, tb + 1, 100):
        p = dict(flt, fromBlock=hex(s), toBlock=hex(min(s + 99, tb)))
        body, r = rpc("eth_getLogs", [p])
        if "result" not in r:
            raise RuntimeError(f"rpc getLogs error {r}")
        records.append({"source": "https://eth.drpc.org", "request": body, "fromBlock": s, "toBlock": min(s + 99, tb),
                        "response": r})
        out += r["result"]
    return out


def run(eid):
    if load(f"ev_{eid}_done"):
        print(eid, "already done")
        return
    m = MEM[eid]
    pre, b0, b1 = m["pre_block"], m["first_block"], m["last_block"]
    st = State(f"ev_{eid}_state")
    # peg pools registered at the pre block
    pks = []
    for i in range(12):
        r = st.call(REGULATOR, selector("peg_keepers(uint256)") + enc(i), pre)
        if r.startswith("ERR") or len(r) < 66 or int(r[2:66], 16) == 0:
            break
        w = [r[2 + 64 * j:2 + 64 * (j + 1)] for j in range((len(r) - 2) // 64)]
        pks.append({"pegkeeper": "0x" + w[0][24:], "pool": "0x" + w[1][24:], "is_inverse": int(w[2], 16),
                    "include_index": int(w[3], 16)})
    for pk in pks:
        pk["coins"] = ["0x" + st.call(pk["pool"], selector("coins(uint256)") + enc(j), pre)[-40:] for j in (0, 1)]
        pk["decimals"] = [int(st.call(c, selector("decimals()"), pre), 16) for c in pk["coins"]]
        st.call(pk["pegkeeper"], selector("debt()"), pre)
        for j in (0, 1):
            st.call(pk["pool"], selector("balances(uint256)") + enc(j), pre)
        for b in (pre, b1):
            st.call(CRVUSD, selector("balanceOf(address)") + enc(pk["pool"]), b)
    st.flush()
    pools = [pk["pool"] for pk in pks]
    members = [x["pool"] for x in m["members"]]
    print(eid, "peg pools", len(pools), "members", len(members), flush=True)

    rec = {k: [] for k in ("crvusd_to_pools", "crvusd_from_pools", "peg_pool_logs", "s_pool_logs",
                           "yb_levamm_vp_logs", "class_topic_logs")}
    L = {"meta": {"event": eid, "pre_block": pre, "first_block": b0, "last_block": b1, "pegkeepers": pks,
                  "members": m["members"]}}
    pp = [pad(p) for p in pools]
    L["crvusd_to_pools"] = rpc_logs(b0, b1, {"address": CRVUSD, "topics": [TP["Transfer"], None, pp]}, rec["crvusd_to_pools"])
    L["crvusd_from_pools"] = rpc_logs(b0, b1, {"address": CRVUSD, "topics": [TP["Transfer"], pp]}, rec["crvusd_from_pools"])
    L["peg_pool_logs"] = rpc_logs(b0, b1, {"address": pools}, rec["peg_pool_logs"])
    L["s_pool_logs"] = rpc_logs(b0, b1, {"address": members}, rec["s_pool_logs"])
    L["yb_levamm_vp_logs"] = rpc_logs(b0, b1, {"address": YB_ADDRS}, rec["yb_levamm_vp_logs"])
    L["class_topic_logs"] = rpc_logs(b0, b1, {"topics": [[TP[t] for t in CLASS_TOPICS]]}, rec["class_topic_logs"])
    save(f"ev_{eid}_rpc_logs", {"records": rec})
    print(eid, "rpc logs", {k: len(v) for k, v in L.items() if k != "meta"}, flush=True)

    # archive state that depends on the logs
    for pk in pks:
        sig = selector("get_p(uint256)") + enc(0) if pk["include_index"] else selector("get_p()")
        blocks = {pre} | {int(lg["blockNumber"], 16) for lg in L["peg_pool_logs"] if lg["address"].lower() == pk["pool"]}
        for b in sorted(blocks):
            st.call(pk["pool"], sig, b)
        st.flush()
    st.call(WSTETH, selector("stEthPerToken()"), pre)
    st.flush()

    save(f"ev_{eid}_done", {"meta": L["meta"]})


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(MEM)
    for eid in ids:
        run(eid)

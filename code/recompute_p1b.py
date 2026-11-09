"""Phase 1b: every number from the cached raw files in code/raw/phase1b/ (standard library only).
Definitions: PHASE_1B_PREREG.md and PHASE_1B_ADDENDUM.md. Called by code/recompute.py, or alone:
python3 -I code/recompute_p1b.py"""
import csv
import gzip
import json
import os
import statistics
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "code", "raw", "phase1b")
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, os.path.dirname(__file__))
import p1b_events  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
T0 = json.load(open(os.path.join(ROOT, "code", "topics.json")))
TP, SEL = T0["topics"], T0["selectors"]
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
WSTETH = "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
BTC_TOKENS = {"0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf",
              "0x18084fba666a33d37592fa2633fd49a74dd93a88", "0x8236a87084f8b84306f72007f36f2618a5634494"}
ETH_TOKENS = {"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", WSTETH}
E18 = 10 ** 18
FAIL = []
FLAGS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + "phase 1b " + msg)
    if not cond:
        FAIL.append("phase 1b " + msg)


def gz(name):
    with gzip.open(os.path.join(RAW, name + ".json.gz"), "rt") as f:
        return json.load(f)


def logs_of(records):
    """Logs from the non-truncated responses, each log once."""
    seen = {}
    for r in records:
        if r.get("truncated"):
            continue
        for lg in r["response"].get("result") or []:
            seen[(lg["transactionHash"].lower(), int(lg["logIndex"], 16))] = lg
    return [seen[k] for k in sorted(seen, key=lambda k: (int(seen[k]["blockNumber"], 16), k[1]))]


def coverage_ok(records, fb, tb):
    """Non-truncated parts of each query tile [fb, tb] with no gap. A query is its request without the
    block bounds."""
    import urllib.parse
    by_q = defaultdict(list)
    for r in records:
        if r.get("truncated"):
            continue
        if "request" in r:
            q = json.loads(r["request"])["params"][0]
            q = json.dumps({k: v for k, v in q.items() if k not in ("fromBlock", "toBlock")}, sort_keys=True)
        else:
            u = urllib.parse.urlparse(r["source"])
            q = json.dumps(sorted((k, v) for k, v in urllib.parse.parse_qsl(u.query) if k not in ("fromBlock", "toBlock")))
        by_q[q].append((r["fromBlock"], r["toBlock"]))
    for parts in by_q.values():
        cur = fb
        for f, t in sorted(parts):
            if f != cur:
                return False
            cur = t + 1
        if cur != tb + 1:
            return False
    return True


def word(h, i):
    h = h[2:] if h.startswith("0x") else h
    return int(h[64 * i:64 * (i + 1)], 16)


def taddr(t):
    return "0x" + t[-40:].lower()


def sel(sig, *args):
    return SEL[sig] + "".join(hex(a)[2:].rjust(64, "0") if isinstance(a, int) else a.lower()[2:].rjust(64, "0")
                              for a in args)


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


# ---------------- prices for D ----------------
CL = {a: p1b_events.points(a) for a in ("BTC", "ETH")}
CL_BLOCKS = {a: [p[1] for p in CL[a]] for a in CL}


def cl_price(asset, block):
    import bisect
    i = bisect.bisect_right(CL_BLOCKS[asset], block) - 1
    return CL[asset][i][2] if i >= 0 else None


EVS = p1b_events.select()
committed = json.load(open(os.path.join(DATA, "phase1b_events.json")))
check(EVS == committed, "event selection recomputed from Chainlink logs equals the committed list")
CAND = json.load(open(os.path.join(RAW, "s_candidates.json")))
COINS = {c["pool"]: c["coins"] for c in CAND["candidates"]}
DEC = {a: v["decimals"] for a, v in CAND["tokens"].items()}
DEC[CRVUSD] = 18
MEMB = json.load(open(os.path.join(RAW, "s_members.json")))["events"]

ROLE = {}
for m in C["mint_markets"]:
    ROLE[m["controller"].lower()] = "controller"
    ROLE[m["amm"].lower()] = "amm"
for m in C["llamalend_v1_markets"]:
    ROLE[m["controller"].lower()] = "controller"
    ROLE[m["amm"].lower()] = "amm"
SUBSET = []
YB_LV = {a.lower() for m in C["yb_markets"] for a in (m["levamm"], m["virtual_pool"])}


def check_subset():
    """VERIFICATION.md, phase 1b: E01 plus the two other events with the most peg pool Transfer logs in the
    RPC logs, ties to the earlier event."""
    cnt = {}
    for ev in EVS["selected"]:
        r = gz(f"ev_{ev['id']}_rpc_logs")["records"]
        cnt[ev["id"]] = len(logs_of(r["crvusd_to_pools"])) + len(logs_of(r["crvusd_from_pools"]))
    rest = sorted((e for e in cnt if e != "E01"), key=lambda e: (-cnt[e], e))
    return ["E01"] + rest[:2], cnt




def event_metrics(ev):
    eid = ev["id"]
    done = gz(f"ev_{eid}_done")["meta"]
    rp = gz(f"ev_{eid}_rpc_logs")["records"]
    bs_path = os.path.join(RAW, f"ev_{eid}_blockscout.json.gz")
    bs = gz(f"ev_{eid}_blockscout")["records"] if os.path.exists(bs_path) else None
    ST = gz(f"ev_{eid}_state")["calls"]
    pre, b0, b1 = done["pre_block"], done["first_block"], done["last_block"]

    def stv(to, data, block):
        v = ST.get(f"{to.lower()}|{data}|{block}")
        return None if v is None or v.startswith("ERR") else v

    out = {"id": eid, "kind": ev["kind"], "t0": ev["t0"], "is_8_november": ev["is_8_november"],
           "btc_decline": ev["btc"]["decline"] if ev["btc"] else None,
           "eth_decline": ev["eth"]["decline"] if ev["eth"] else None,
           "pre_block": pre, "first_block": b0, "last_block": b1}
    check(all(coverage_ok(rp[k], b0, b1) for k in rp), f"{eid} RPC log responses cover the window with no gap")
    if bs is not None:
        check(all(coverage_ok(bs[k], b0, b1) for k in bs), f"{eid} Blockscout check responses cover the window with no gap")
    L = {k: logs_of(v) for k, v in rp.items()}
    pks = done["pegkeepers"]
    pools = [p["pool"].lower() for p in pks]
    pk_addr = {p["pegkeeper"].lower() for p in pks}
    members = {m["pool"].lower(): m["yield_basis"] for m in done["members"]}
    out["n_peg_pools"] = len(pools)
    out["n_members"] = len(members)
    out["n_members_yb"] = sum(members.values())

    # completeness against the second source
    key = lambda lg: (lg["transactionHash"].lower(), int(lg["logIndex"], 16), lg["data"].lower())  # noqa: E731
    s_te = [lg for lg in L["s_pool_logs"] if lg["topics"][0] == TP["TokenExchange_twocrypto"]]
    prim = {"crvusd_to_pools": {key(lg) for lg in L["crvusd_to_pools"]},
            "crvusd_from_pools": {key(lg) for lg in L["crvusd_from_pools"]},
            "s_swaps": {key(lg) for lg in s_te}}
    if bs is None:
        out["completeness"] = {"second_source": "not run"}
        comp_ok = None
    else:
        sec = {k: {key(lg) for lg in logs_of(v)} for k, v in bs.items()}
        out["completeness"] = {k: {"rpc": len(prim[k]), "blockscout": len(sec[k]), "only_rpc": len(prim[k] - sec[k]),
                                   "only_blockscout": len(sec[k] - prim[k])} for k in prim}
        comp_ok = all(prim[k] == sec[k] for k in prim)
    # balance check, exact
    net_pool = defaultdict(int)
    for lg in L["crvusd_to_pools"]:
        net_pool[taddr(lg["topics"][2])] += int(lg["data"], 16)
    for lg in L["crvusd_from_pools"]:
        net_pool[taddr(lg["topics"][1])] -= int(lg["data"], 16)
    bal_ok = True
    for p in pools:
        d = int(stv(CRVUSD, sel("balanceOf(address)", p), b1), 16) - int(stv(CRVUSD, sel("balanceOf(address)", p), pre), 16)
        bal_ok &= d == net_pool[p]
    out["completeness"]["balances_exact"] = bal_ok
    out["completeness"]["second_source_match"] = comp_ok
    check(bal_ok, f"{eid} peg pool crvUSD balance change equals the net of the Transfer logs exactly")
    if comp_ok is not None:
        check(comp_ok, f"{eid} RPC and Blockscout logs are the same set")
    out["in_blockscout_subset"] = eid in SUBSET
    if comp_ok is None and eid in SUBSET:
        nc = os.path.exists(os.path.join(RAW, f"ev_{eid}_blockscout_not_checked.json.gz"))
        out["completeness"]["second_source"] = "not checked, HTTP 429" if nc else "not run"
        FLAGS.append(f"{eid} Blockscout check " + out["completeness"]["second_source"])
    elif comp_ok is None:
        out["completeness"]["second_source"] = "RPC only, outside the Blockscout subset"
    elif not comp_ok:
        FLAGS.append(f"{eid} Blockscout and RPC logs differ")
    if not bal_ok:
        FLAGS.append(f"{eid} balance check failed")
    other_te = {lg["topics"][0] for lg in L["s_pool_logs"]} - {TP["TokenExchange_twocrypto"]}
    out["s_pool_other_topics"] = len(other_te)

    # peg pool legs per transaction
    net = defaultdict(lambda: defaultdict(int))
    pk_leg = defaultdict(lambda: defaultdict(int))
    blk = {}
    for lg in L["crvusd_to_pools"]:
        p, frm, h = taddr(lg["topics"][2]), taddr(lg["topics"][1]), lg["transactionHash"].lower()
        (pk_leg if frm in pk_addr else net)[h][p] += int(lg["data"], 16)
        blk[h] = int(lg["blockNumber"], 16)
    for lg in L["crvusd_from_pools"]:
        p, to, h = taddr(lg["topics"][1]), taddr(lg["topics"][2]), lg["transactionHash"].lower()
        (pk_leg if to in pk_addr else net)[h][p] -= int(lg["data"], 16)
        blk[h] = int(lg["blockNumber"], 16)
    tx_net = {h: sum(v.values()) / E18 for h, v in net.items()}

    # S pool sales
    steth = int(stv(WSTETH, SEL["stEthPerToken()"], pre), 16) / E18
    sale = defaultdict(lambda: [0.0, 0.0])  # tx -> [YB usd, other usd]
    s_tx = set()
    unpriced = 0
    for lg in s_te:
        pool = lg["address"].lower()
        if pool not in members:
            continue
        h = lg["transactionHash"].lower()
        s_tx.add(h)
        sold_id, sold = word(lg["data"], 0), word(lg["data"], 1)
        tok = COINS[pool][sold_id]
        if tok in BTC_TOKENS:
            px = cl_price("BTC", int(lg["blockNumber"], 16))
        elif tok in ETH_TOKENS:
            px = cl_price("ETH", int(lg["blockNumber"], 16))
            if px is not None and tok == WSTETH:
                px *= steth
        else:
            continue
        if px is None:
            unpriced += 1
            continue
        sale[h][0 if members[pool] else 1] += sold / 10 ** DEC[tok] * px
    out["unpriced_sales"] = unpriced
    D_yb = sum(v[0] for v in sale.values())
    D_ot = sum(v[1] for v in sale.values())
    N_yb = N_ot = 0.0
    for h, (y, o) in sale.items():
        n = tx_net.get(h, 0.0)
        N_yb += n * y / (y + o)
        N_ot += n * o / (y + o)
    N, D = N_yb + N_ot, D_yb + D_ot
    T = lambda n, d: n / d if d >= 500_000 else None  # noqa: E731
    out.update({"N": N, "D": D, "T": T(N, D), "N_yb": N_yb, "D_yb": D_yb, "T_yb": T(N_yb, D_yb),
                "N_other": N_ot, "D_other": D_ot, "T_other": T(N_ot, D_ot), "n_sale_tx": len(sale)})

    # classes (release 1 rules, rule 5 widened to S)
    by_tx = defaultdict(list)
    for lg in L["class_topic_logs"]:
        r = ROLE.get(lg["address"].lower())
        if r:
            by_tx[lg["transactionHash"].lower()].append((r, lg["topics"][0]))
    lv_tx = {lg["transactionHash"].lower() for lg in L["yb_levamm_vp_logs"] if lg["address"].lower() in YB_LV}
    swap_legs = {(lg["transactionHash"].lower(), lg["address"].lower()) for lg in L["peg_pool_logs"]
                 if lg["topics"][0] == TP["TokenExchange_stableswap"]}
    cls_net = defaultdict(float)
    cls_n = defaultdict(int)
    for h, v in tx_net.items():
        ev_ = by_tx.get(h, [])
        if any(r == "controller" and t == TP["Liquidate"] for r, t in ev_):
            c = "hard_liquidation"
        elif any(r == "amm" and t == TP["TokenExchange_llamma"] for r, t in ev_):
            c = "llamma_arbitrage"
        elif h in lv_tx:
            c = "yb_levamm_leg"
        elif h in s_tx:
            c = "s_pool_leg"
        elif any(r == "controller" and t in (TP["Borrow"], TP["Repay"], TP["RemoveCollateral"]) for r, t in ev_):
            c = "borrower_action"
        elif all((h, p) not in swap_legs for p in net[h]):
            c = "liquidity_non_pk"
        else:
            c = "other"
        cls_net[c] += v
        cls_n[c] += 1
    out["class_net"] = dict(cls_net)
    out["class_n_tx"] = dict(cls_n)
    out["levamm_leg_net"] = cls_net.get("yb_levamm_leg", 0.0)
    out["s_pool_leg_net"] = cls_net.get("s_pool_leg", 0.0)
    out["pegkeeper_leg_net"] = sum(sum(v.values()) for v in pk_leg.values()) / E18

    # PegKeeper debt and peg pool balance at the pre block
    debt = {p["pegkeeper"]: int(stv(p["pegkeeper"], SEL["debt()"], pre), 16) / E18 for p in pks}
    out["pk_debt_total"] = sum(debt.values())
    out["pk_debt"] = debt
    out["peg_pool_crvusd"] = sum(int(stv(CRVUSD, sel("balanceOf(address)", p), pre), 16) for p in pools) / E18
    out["N_over_peg_balance"] = N / out["peg_pool_crvusd"]

    # weighted peg pool price
    ts_of = {int(lg["blockNumber"], 16): int(lg.get("blockTimestamp") or lg["timeStamp"], 16) for lg in L["peg_pool_logs"]}
    used, left_out = [], []
    pts, wraw = {}, {}
    for p in pks:
        pool = p["pool"].lower()
        if p["coins"][1].lower() != CRVUSD:
            left_out.append(pool)
            continue
        g = sel("get_p(uint256)", 0) if p["include_index"] else SEL["get_p()"]
        ser = {}
        for k, v in ST.items():
            to, data, b = k.split("|")
            if to == pool and data == g and not v.startswith("ERR"):
                ser[int(b)] = int(v, 16) / E18
        if pre not in ser:
            left_out.append(pool)
            continue
        pts[pool] = ser
        b0v = int(stv(pool, sel("balances(uint256)", 0), pre), 16) / 10 ** p["decimals"][0]
        b1v = int(stv(pool, sel("balances(uint256)", 1), pre), 16) / 10 ** p["decimals"][1]
        wraw[pool] = b0v + b1v
        used.append(pool)
    tot = sum(wraw.values())
    w = {p: wraw[p] / tot for p in used}
    cur = {p: pts[p][pre] for p in used}
    W_pre = sum(w[p] * cur[p] for p in used)
    change = sorted({b for p in used for b in pts[p] if b0 <= b <= b1})
    path = [(ev["window_start_ts"], W_pre)]
    for b in change:
        for p in used:
            if b in pts[p]:
                cur[p] = pts[p][b]
        path.append((ts_of[b], sum(w[q] * cur[q] for q in used)))
    W_min = min(x[1] for x in path)
    below = 0
    for i, (ts, val) in enumerate(path):
        nxt = path[i + 1][0] if i + 1 < len(path) else ev["window_end_ts"]
        if val < 0.997:
            below += max(0, nxt - ts)
    out.update({"W_pre": W_pre, "W_min": W_min, "peg_move_bp": (W_min - W_pre) * 1e4,
                "minutes_below_0997": below / 60, "price_pools_used": len(used), "price_pools_left_out": left_out})
    return out


def score(events):
    pr = {}
    Ts = [e["T"] for e in events if e["T"] is not None]
    pr["P1B-02"] = ("UNTESTABLE", None) if not Ts else (
        "HIT" if 0.4 <= statistics.median(Ts) <= 0.9 else "MISS", statistics.median(Ts))
    ok = [abs(e["levamm_leg_net"]) < 0.25 * abs(e["s_pool_leg_net"]) for e in events]
    pr["P1B-03"] = ("HIT" if sum(ok) >= 0.75 * len(ok) else "MISS", f"{sum(ok)} of {len(ok)}")
    sh = [e["N_yb"] / e["N"] for e in events if e["N"] > 0]
    pr["P1B-04"] = ("UNTESTABLE", None) if not sh else (
        "HIT" if statistics.median(sh) >= 0.6 else "MISS", statistics.median(sh))
    if len(events) >= 3:
        rho = spearman([e["N_over_peg_balance"] for e in events], [abs(e["peg_move_bp"]) for e in events])
        pr["P1B-05"] = ("UNTESTABLE", None) if rho is None else ("HIT" if rho >= 0.5 else "MISS", rho)
    else:
        pr["P1B-05"] = ("UNTESTABLE", None)
    lo = [abs(e["peg_move_bp"]) for e in events if e["pk_debt_total"] < 1e6]
    hi = [abs(e["peg_move_bp"]) for e in events if e["pk_debt_total"] >= 5e6]
    if len(lo) < 2 or len(hi) < 2:
        pr["P1B-06"] = ("UNTESTABLE", f"{len(lo)} events under 1M debt, {len(hi)} at 5M or more")
    else:
        d = statistics.median(lo) - statistics.median(hi)
        pr["P1B-06"] = ("HIT" if d >= 10 else "MISS", d)
    pr["P1B-08"] = ("HIT" if all(e["N"] <= 25e6 for e in events) else "MISS", max(e["N"] for e in events))
    both = [e for e in events if e["T_yb"] is not None and e["T_other"] is not None]
    if len(both) < 3:
        pr["P1B-09"] = ("UNTESTABLE", f"{len(both)} events with both T defined")
    else:
        k = sum(abs(e["T_yb"] - e["T_other"]) <= 0.25 for e in both)
        pr["P1B-09"] = ("HIT" if k >= 0.75 * len(both) else "MISS", f"{k} of {len(both)}")
    return pr


def main():
    global SUBSET
    SUBSET, counts = check_subset()
    events = [event_metrics(ev) for ev in EVS["selected"]]
    n_cap = EVS["qualifying_events_before_cap"]
    nov = [e for e in EVS["all_events"] if e["is_8_november"]]
    check(len(nov) == 1, "exactly one event is 8 November 2026")
    s_all = score(events)
    s_ex = score([e for e in events if not e["is_8_november"]])
    s_all["P1B-01"] = ("HIT" if 4 <= n_cap <= 15 else "MISS", n_cap)
    s_ex["P1B-01"] = ("HIT" if 4 <= n_cap - 1 <= 15 else "MISS", n_cap - 1)
    e8 = [e for e in events if e["is_8_november"]][0]
    others = [e["T"] for e in events if not e["is_8_november"] and e["T"] is not None]
    if e8["T"] is None or len(others) < 2:
        p7 = ("UNTESTABLE", None)
    else:
        q = statistics.quantiles(others, n=4, method="inclusive")
        p7 = ("HIT" if q[0] <= e8["T"] <= q[2] else "MISS", {"T_8nov": e8["T"], "q1": q[0], "q3": q[2]})
    s_all["P1B-07"] = s_ex["P1B-07"] = p7
    weak = {"P1B-01", "P1B-08"}
    preds = {k: {"all_events": {"result": s_all[k][0], "value": s_all[k][1]},
                 "without_8_november": {"result": s_ex[k][0], "value": s_ex[k][1]}, "weak_test": k in weak}
             for k in sorted(s_all)}
    res = {"events": events, "predictions": preds, "flags": FLAGS, "blockscout_subset": SUBSET,
           "peg_pool_transfer_counts": counts,
           "qualifying_events_before_cap": n_cap, "n_selected": len(events)}
    with open(os.path.join(DATA, "phase1b_results.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    cols = ["id", "kind", "t0", "btc_decline", "eth_decline", "N", "D", "T", "N_yb", "D_yb", "T_yb", "N_other",
            "D_other", "T_other", "levamm_leg_net", "s_pool_leg_net", "pk_debt_total", "peg_pool_crvusd",
            "N_over_peg_balance", "W_pre", "W_min", "peg_move_bp", "minutes_below_0997"]
    with open(os.path.join(DATA, "phase1b_events_metrics.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(cols)
        for e in events:
            wr.writerow(["" if e[c] is None else (f"{e[c]:.6f}" if isinstance(e[c], float) else e[c]) for c in cols])
    for k, v in preds.items():
        print("phase 1b", k, v["all_events"]["result"], v["without_8_november"]["result"])
    return res


if __name__ == "__main__":
    main()
    print("FAILED CHECKS:", FAIL if FAIL else "none")
    sys.exit(1 if FAIL else 0)

"""Recompute every number of the study from the cached raw files.

Usage: python3 -I code/recompute.py
Standard library only. Charts are drawn afterwards by code/charts.py (pinned matplotlib),
which this script calls if matplotlib is importable. Exits non-zero if any check fails.
"""
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "code", "raw")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

FAIL = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def load(*p):
    with open(os.path.join(RAW, *p)) as f:
        return json.load(f)


C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
T0 = json.load(open(os.path.join(ROOT, "code", "topics.json")))
S = load("state.json")
TX = load("transactions.json")
BT = {int(k): int(v, 16) for k, v in load("block_timestamps.json").items()}
WB = load("window_blocks.json")
PRE, B0, B1 = C["window"]["pre_block"], C["window"]["first_block"], C["window"]["last_block"]
F0 = WB["flush_start"]["first_block_at_or_after"]
F1 = WB["flush_end"]["first_block_at_or_after"] - 1
TS_START = 1794168000  # 2026-11-08 20:00:00 UTC
TS_END = 1794196800    # 2026-11-09 04:00:00 UTC
TS_F0, TS_F1 = 1794177000, 1794180600
CLAIM = 4_100_000.0
E18 = 10 ** 18


def sel(sig):
    return T0["selectors"][sig]


def st(to, sig, block, args=()):
    data = sel(sig) + "".join(hex(x)[2:].rjust(64, "0") for x in args)
    v = S.get(f"{to.lower()}|{data}|{block}")
    if v is None or v.startswith("ERR"):
        return None
    return v


def words(h):
    h = h[2:]
    return [int(h[i:i + 64], 16) for i in range(0, len(h), 64)]


def topic_addr(t):
    return "0x" + t[-40:]


def utc(ts):
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))


check(all(b in BT for b in range(PRE, B1 + 1)), "block timestamps cached for every window block")
check(BT[B0] >= TS_START > BT[PRE] and BT[B1] < TS_END <= BT[B1] + 12 + 12, "window boundary blocks match UTC bounds")


def dur(b):
    """Seconds block b's state is held within the main window."""
    nxt = BT.get(b + 1, TS_END) if b < B1 else TS_END
    return max(0, min(nxt, TS_END) - max(BT[b], TS_START))


# ---------------- logs and indexes ----------------
LOGS = {n: load("logs", n + ".json") for n in
        ("crvusd_transfer_to_pools", "crvusd_transfer_from_pools", "pegkeeper_pools", "pegkeepers",
         "mint_markets", "llamalend_v1", "yieldbasis", "chainlink_eth_usd", "chainlink_btc_usd")}
role = {}
for p in C["pegkeepers"]:
    role[p["pool"].lower()] = "pk_pool"
    role[p["pegkeeper"].lower()] = "pegkeeper"
for m in C["mint_markets"]:
    role[m["controller"].lower()] = "mint_controller"
    role[m["amm"].lower()] = "mint_amm"
for m in C["llamalend_v1_markets"]:
    role[m["controller"].lower()] = "ll_controller"
    role[m["amm"].lower()] = "ll_amm"
for m in C["yb_markets"]:
    role[m["levamm"].lower()] = "yb_levamm"
    role[m["pool"].lower()] = "yb_pool"
    role[m["virtual_pool"].lower()] = "yb_vp"

TP = T0["topics"]
by_tx = defaultdict(list)
for n in ("pegkeeper_pools", "pegkeepers", "mint_markets", "llamalend_v1", "yieldbasis"):
    for lg in LOGS[n]:
        by_tx[lg["transactionHash"]].append((role.get(lg["address"].lower(), "?"), lg["topics"][0], lg))

pools = [p["pool"].lower() for p in C["pegkeepers"]]
pkaddr = {p["pegkeeper"].lower() for p in C["pegkeepers"]}
pool_name = {p["pool"].lower(): p["name"] for p in C["pegkeepers"]}

# ---------------- Q1 prices ----------------
price_pts = {}
for p in C["pegkeepers"]:
    pool = p["pool"].lower()
    sig, args = ("get_p(uint256)", (0,)) if p["include_index"] else ("get_p()", ())
    pts = {}
    for key, v in S.items():
        to, data, blk = key.split("|")
        if to == pool and data == sel(sig) + "".join(hex(x)[2:].rjust(64, "0") for x in args) and not v.startswith("ERR"):
            pts[int(blk)] = int(v, 16) / E18
    price_pts[pool] = pts
    check(PRE in pts, f"{p['name']} price at pre block present")

# direction check (addendum section 2): in blocks where crvUSD only went into the pool via swaps, price must fall
net_block = defaultdict(float)
for lg in LOGS["crvusd_transfer_to_pools"]:
    net_block[(topic_addr(lg["topics"][2]).lower(), int(lg["blockNumber"], 16))] += int(lg["data"], 16) / E18
for lg in LOGS["crvusd_transfer_from_pools"]:
    net_block[(topic_addr(lg["topics"][1]).lower(), int(lg["blockNumber"], 16))] -= int(lg["data"], 16) / E18
agree = disagree = 0
for pool in pools:
    pts = price_pts[pool]
    blocks = sorted(pts)
    for i in range(1, len(blocks)):
        b, prev = blocks[i], blocks[i - 1]
        nb = net_block.get((pool, b), 0.0)
        if abs(nb) < 1000:
            continue
        d = pts[b] - pts[prev]
        if d == 0:
            continue
        if (nb > 0 and d < 0) or (nb < 0 and d > 0):
            agree += 1
        else:
            disagree += 1
direction_flipped = True  # get_p() returns crvUSD priced in the paired coin, so no inversion is applied
check(agree > 5 * max(1, disagree),
      f"price direction check: crvUSD inflow lowers get_p in {agree} blocks, raises it in {disagree} (get_p used as crvUSD price, addendum inversion flipped)")


def price_at(pool, b):
    pts = price_pts[pool]
    best = None
    for k in pts:
        if k <= b and (best is None or k > best):
            best = k
    return pts[best]


# forward fill per block
series = {pool: {} for pool in pools}
for pool in pools:
    pts = price_pts[pool]
    cur = pts[PRE]
    for b in range(B0, B1 + 1):
        if b in pts:
            cur = pts[b]
        series[pool][b] = cur

bal = {}
for p in C["pegkeepers"]:
    pool = p["pool"].lower()
    b0 = int(st(pool, "balances(uint256)", PRE, (0,)), 16)
    b1 = int(st(pool, "balances(uint256)", PRE, (1,)), 16)
    d0 = p["coin_decimals"][0]
    bal[pool] = b0 / 10 ** d0 + b1 / E18
tot = sum(bal.values())
wgt = {pool: bal[pool] / tot for pool in pools}
Wser = {b: sum(wgt[p] * series[p][b] for p in pools) for b in range(B0, B1 + 1)}
W_pre = sum(wgt[p] * price_pts[p][PRE] for p in pools)


def time_below(ser, lvl):
    return sum(dur(b) for b in range(B0, B1 + 1) if ser[b] < lvl)


q1 = {"weights": {pool_name[p]: wgt[p] for p in pools}, "tvl_pre_usd": {pool_name[p]: bal[p] for p in pools},
      "W_pre": W_pre, "pools": {}}
for pool in pools:
    s = series[pool]
    bmin = min(s, key=lambda b: (s[b], b))
    q1["pools"][pool_name[pool]] = {"min": s[bmin], "min_block": bmin, "min_utc": utc(BT[bmin]),
                                    "pre": price_pts[pool][PRE], "end": s[B1],
                                    "sec_below_0997": time_below(s, 0.997), "sec_below_0995": time_below(s, 0.995)}
bWmin = min(Wser, key=lambda b: (Wser[b], b))
rec_block = None
for b in range(bWmin + 1, B1 + 1):
    if Wser[b] >= 0.999:
        rec_block = b
        break
q1["W"] = {"min": Wser[bWmin], "min_block": bWmin, "min_utc": utc(BT[bWmin]), "end": Wser[B1],
           "sec_below_0997": time_below(Wser, 0.997), "sec_below_0995": time_below(Wser, 0.995),
           "sec_below_0999": time_below(Wser, 0.999),
           "recovery_block": rec_block, "recovery_sec": (BT[rec_block] - BT[bWmin]) if rec_block else None,
           "max": max(Wser.values())}
q1["min_any_pool"] = min(v["min"] for v in q1["pools"].values())
q1["min_any_pool_name"] = min(q1["pools"], key=lambda k: q1["pools"][k]["min"])

# aggregator price
agg = {}
for b in range(PRE, B1 + 1, 10):
    v = st(T0["aggregator"], "price()", b)
    if v:
        agg[b] = int(v, 16) / E18
q1["aggregator"] = {"pre": agg[PRE], "min": min(agg.values()), "min_block": min(agg, key=agg.get), "max": max(agg.values())}

# ---------------- ETH price ----------------
eth_pts = []
for lg in LOGS["chainlink_eth_usd"]:
    if lg["topics"][0] == TP["AnswerUpdated"]:
        ans = int(lg["topics"][1], 16)
        eth_pts.append((int(lg["blockNumber"], 16), ans / 1e8))
eth_pts.sort()
check(len(eth_pts) > 0 and eth_pts[0][0] <= B0, "Chainlink ETH/USD has an answer at or before window start")
eth = {}
j = 0
cur = None
for b in range(PRE, B1 + 1):
    while j < len(eth_pts) and eth_pts[j][0] <= b:
        cur = eth_pts[j][1]
        j += 1
    eth[b] = cur
eth_max_b = max(range(B0, B1 + 1), key=lambda b: eth[b])
# max drawdown in window
peak = None
mdd = 0.0
mdd_peak = mdd_trough = None
for b in range(B0, B1 + 1):
    if peak is None or eth[b] > eth[peak]:
        peak = b
    dd = eth[b] / eth[peak] - 1
    if dd < mdd:
        mdd, mdd_peak, mdd_trough = dd, peak, b
# steepest 15 minute decline: for each start block, compare with first block 900 s later
blist = list(range(B0, B1 + 1))
steep = (0.0, None, None)
k = 0
for i, b in enumerate(blist):
    while k < len(blist) and BT[blist[k]] < BT[b] + 900:
        k += 1
    if k >= len(blist):
        break
    r = eth[blist[k]] / eth[b] - 1
    if r < steep[0]:
        steep = (r, b, blist[k])
btc_pts = sorted((int(lg["blockNumber"], 16), int(lg["topics"][1], 16) / 1e8) for lg in LOGS["chainlink_btc_usd"] if lg["topics"][0] == TP["AnswerUpdated"])
btc = {}
j = 0
cur = None
for b in range(PRE, B1 + 1):
    while j < len(btc_pts) and btc_pts[j][0] <= b:
        cur = btc_pts[j][1]
        j += 1
    btc[b] = cur
check(btc[B0] is not None, "Chainlink BTC/USD has an answer at or before window start")
bpk = None
bmdd = 0.0
for b in range(B0, B1 + 1):
    if bpk is None or btc[b] > btc[bpk]:
        bpk = b
    bmdd = min(bmdd, btc[b] / btc[bpk] - 1)
btc_res = {"start": btc[B0], "end": btc[B1], "min": min(btc[b] for b in range(B0, B1 + 1)), "max_drawdown": bmdd,
           "at_2145": btc[max(b for b in range(B0, B1 + 1) if BT[b] < 1794174300)],
           "at_2200": btc[max(b for b in range(B0, B1 + 1) if BT[b] < 1794175200)]}
eth_res = {"at_2141": eth[max(b for b in range(B0, B1 + 1) if BT[b] < 1794174060)], "start": eth[B0], "end": eth[B1], "max": eth[eth_max_b], "min": min(eth[b] for b in blist),
           "max_drawdown": mdd, "dd_peak_block": mdd_peak, "dd_peak_utc": utc(BT[mdd_peak]),
           "dd_trough_block": mdd_trough, "dd_trough_utc": utc(BT[mdd_trough]),
           "steepest_15m": steep[0], "steepest_15m_start_utc": utc(BT[steep[1]]) if steep[1] else None,
           "steepest_15m_start_block": steep[1], "n_updates": len(eth_pts)}

# ---------------- Q2 PegKeepers ----------------
q2 = {"pegkeepers": {}}
prov = defaultdict(float)
wdr = defaultdict(float)
for lg in LOGS["pegkeepers"]:
    a = lg["address"].lower()
    v = int(lg["data"][:66], 16) / E18
    if lg["topics"][0] == TP["Provide"]:
        prov[a] += v
    elif lg["topics"][0] == TP["Withdraw_pk"]:
        wdr[a] += v
tot0 = 0.0
for p in C["pegkeepers"]:
    a = p["pegkeeper"].lower()
    d0 = int(st(a, "debt()", PRE), 16) / E18
    d1 = int(st(a, "debt()", B1), 16) / E18
    check(abs(d0 + prov[a] - wdr[a] - d1) <= 1.0, f"PegKeeper {p['name']} debt reconciles from events")
    q2["pegkeepers"][p["name"]] = {"debt_start": d0, "debt_end": d1, "provided": prov[a], "withdrawn": wdr[a]}
    tot0 += d0
q2["total_debt_start"] = tot0
q2["n_events"] = len(LOGS["pegkeepers"])
q2["verdict"] = "no reserves to deploy" if tot0 < 100_000 else "see per PegKeeper"

# ---------------- Q3 flows ----------------
net = defaultdict(lambda: defaultdict(float))   # tx -> pool -> net_in
pk_leg = defaultdict(lambda: defaultdict(float))
tx_block = {}
tx_logidx = {}
for lg in LOGS["crvusd_transfer_to_pools"]:
    h = lg["transactionHash"]
    frm, to = topic_addr(lg["topics"][1]).lower(), topic_addr(lg["topics"][2]).lower()
    v = int(lg["data"], 16) / E18
    tgt = pk_leg if frm in pkaddr else net
    tgt[h][to] += v
    tx_block[h] = int(lg["blockNumber"], 16)
for lg in LOGS["crvusd_transfer_from_pools"]:
    h = lg["transactionHash"]
    frm, to = topic_addr(lg["topics"][1]).lower(), topic_addr(lg["topics"][2]).lower()
    v = int(lg["data"], 16) / E18
    tgt = pk_leg if to in pkaddr else net
    tgt[h][frm] -= v
    tx_block[h] = int(lg["blockNumber"], 16)
# pool-to-pool transfers appear in both files; each file only books its own side, so each is counted once per side
p2p = [lg for lg in LOGS["crvusd_transfer_to_pools"] if topic_addr(lg["topics"][1]).lower() in pools]
p2p_keys_from = {(lg["transactionHash"], lg["logIndex"]) for lg in LOGS["crvusd_transfer_from_pools"]}
check(all((lg["transactionHash"], lg["logIndex"]) in p2p_keys_from for lg in p2p),
      f"{len(p2p)} pool-to-pool transfers are present in both files and booked once per side")

RULES = ["hard_liquidation", "llamma_arbitrage", "yb_levamm_leg", "yb_curve_pool_leg", "borrower_action"]


def matches(h):
    m = []
    ev = by_tx.get(h, [])
    if any(r in ("mint_controller", "ll_controller") and t == TP["Liquidate"] for r, t, _ in ev):
        m.append("hard_liquidation")
    if any(r in ("mint_amm", "ll_amm") and t == TP["TokenExchange_llamma"] for r, t, _ in ev):
        m.append("llamma_arbitrage")
    if any(r in ("yb_levamm", "yb_vp") for r, t, _ in ev):
        m.append("yb_levamm_leg")
    if any(r == "yb_pool" and t == TP["TokenExchange_twocrypto"] for r, t, _ in ev):
        m.append("yb_curve_pool_leg")
    if any(r in ("mint_controller", "ll_controller") and t in (TP["Borrow"], TP["Repay"], TP["RemoveCollateral"]) for r, t, _ in ev):
        m.append("borrower_action")
    return m


def legtype(h, pool):
    ev = by_tx.get(h, [])
    swap = any(lg["address"].lower() == pool and t in (TP["TokenExchange_stableswap"],) for r, t, lg in ev)
    return "swap" if swap else "liquidity"


rows = []
multi = defaultdict(lambda: [0, 0.0])
for h, legs in net.items():
    m = matches(h)
    if len(m) > 1:
        multi["+".join(m)][0] += 1
        multi["+".join(m)][1] += sum(legs.values())
    if m:
        cls = m[0]
    elif all(legtype(h, p) == "liquidity" for p in legs):
        cls = "liquidity_non_pk"
    else:
        cls = "other"
    b = tx_block[h]
    t = TX.get(h, {})
    for pool, v in legs.items():
        rows.append({"tx": h, "block": b, "ts": BT[b], "pool": pool_name[pool], "class": cls,
                     "net_in": v, "leg": legtype(h, pool), "from": (t.get("from") or "").lower(),
                     "to": (t.get("to") or "").lower()})
for h, legs in pk_leg.items():
    b = tx_block[h]
    for pool, v in legs.items():
        if v != 0:
            rows.append({"tx": h, "block": b, "ts": BT[b], "pool": pool_name[pool], "class": "pegkeeper",
                         "net_in": v, "leg": "liquidity", "from": "", "to": ""})
check(all(h in TX for h in net), "every flow transaction has from/to cached")

# balance reconciliation: sum of net flows equals change of crvUSD balance in pools
d_pool_bal = 0.0
for p in C["pegkeepers"]:
    pool = p["pool"].lower()
    i = 1  # crvUSD is coin 1 in every PegKeeper pool (checked below)
    d_pool_bal += (int(st(pool, "balances(uint256)", B1, (i,)), 16) - int(st(pool, "balances(uint256)", PRE, (i,)), 16)) / E18
check(all(p["coins"][1].lower() == C["crvusd"] for p in C["pegkeepers"]), "crvUSD is coin 1 in every PegKeeper pool")
sum_flows = sum(r["net_in"] for r in rows)
check(abs(sum_flows - d_pool_bal) <= max(1000.0, 0.002 * abs(d_pool_bal)),
      f"sum of transfer flows {sum_flows:,.0f} matches pool balance change {d_pool_bal:,.0f} (admin fee tolerance)")

CLASSES = ["pegkeeper", "hard_liquidation", "llamma_arbitrage", "yb_levamm_leg", "yb_curve_pool_leg",
           "borrower_action", "liquidity_non_pk", "other"]


def agg_class(rs):
    out = {c: {"net_in": 0.0, "sold": 0.0, "bought": 0.0, "n_tx": 0} for c in CLASSES}
    seen = defaultdict(set)
    for r in rs:
        o = out[r["class"]]
        o["net_in"] += r["net_in"]
        if r["net_in"] > 0:
            o["sold"] += r["net_in"]
        else:
            o["bought"] += -r["net_in"]
        seen[r["class"]].add(r["tx"])
    for c in CLASSES:
        out[c]["n_tx"] = len(seen[c])
    return out


in_main = [r for r in rows if TS_START <= r["ts"] < TS_END]
in_flush = [r for r in rows if TS_F0 <= r["ts"] < TS_F1]
q3 = {"main": agg_class(in_main), "flush": agg_class(in_flush),
      "multi_class": {k: {"n_tx": v[0], "net_in": v[1]} for k, v in multi.items()}}

# concentration: share of class gross |net_in| from largest tx.from
conc = {}
for c in CLASSES:
    per = defaultdict(float)
    for r in in_main:
        if r["class"] == c:
            per[r["from"]] += abs(r["net_in"])
    totc = sum(per.values())
    conc[c] = (max(per.values()) / totc) if totc > 0 else None
q3["largest_sender_share"] = conc
yb_sell = defaultdict(float)
for r in in_main:
    if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg") and r["net_in"] > 0:
        yb_sell[r["from"]] += r["net_in"]
q3["yb_gross_sell_largest_sender_share"] = (max(yb_sell.values()) / sum(yb_sell.values())) if yb_sell else None
yb_sell_to = defaultdict(float)
yb_sell_tx = defaultdict(float)
for r in in_main:
    if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg") and r["net_in"] > 0:
        yb_sell_to[r["to"]] += r["net_in"]
        yb_sell_tx[r["tx"]] += r["net_in"]
q3["yb_gross_sell_largest_destination_share"] = max(yb_sell_to.values()) / sum(yb_sell_to.values()) if yb_sell_to else None
q3["yb_gross_sell_top5_tx_share"] = sum(sorted(yb_sell_tx.values(), reverse=True)[:5]) / sum(yb_sell_tx.values()) if yb_sell_tx else None
q3["yb_gross_sell_n_senders"] = len(yb_sell)
q3["yb_gross_sell_n_tx"] = len(yb_sell_tx)

# S1 cross transaction linkage
yb_addrs = set()
for r in in_main:
    if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg"):
        yb_addrs |= {r["from"], r["to"]}
yb_addrs.discard("")
s1_moved = [r for r in in_main if r["class"] == "other" and (r["from"] in yb_addrs or r["to"] in yb_addrs)]
q3["s1_moved_net_in"] = sum(r["net_in"] for r in s1_moved)
q3["s1_moved_n_tx"] = len({r["tx"] for r in s1_moved})
yb_from = {r["from"] for r in in_main if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg")} - {""}
q3["s1_from_only_moved_net_in"] = sum(r["net_in"] for r in in_main if r["class"] == "other" and r["from"] in yb_from)


def yb(rs, gross=False, pools_only=None, classes=("yb_levamm_leg", "yb_curve_pool_leg")):
    s = 0.0
    for r in rs:
        if r["class"] in classes and (pools_only is None or r["pool"] in pools_only):
            if gross and r["net_in"] <= 0:
                continue
            s += r["net_in"]
    return s


V = {"V0_main_net_same_tx": yb(in_main), "V1_flush_hour": yb(in_flush), "V2_gross_sells": yb(in_main, gross=True),
     "V3_with_cross_tx": yb(in_main) + q3["s1_moved_net_in"], "V4_usdc_usdt_only": yb(in_main, pools_only=("USDC", "USDT")),
     "V5_curve_pool_leg_only": yb(in_main, classes=("yb_curve_pool_leg",)),
     "levamm_leg_only": yb(in_main, classes=("yb_levamm_leg",))}


def within(x, pct):
    return abs(x - CLAIM) / CLAIM <= pct


if within(V["V0_main_net_same_tx"], 0.10):
    verdict = "reproduces"
else:
    alt = [k for k in ("V1_flush_hour", "V2_gross_sells", "V3_with_cross_tx", "V4_usdc_usdt_only", "V5_curve_pool_leg_only") if within(V[k], 0.10)]
    if alt:
        verdict = "reproduces only under " + ", ".join(alt)
    elif V["V0_main_net_same_tx"] > 0:
        verdict = "sign reproduces"
    else:
        verdict = "does not reproduce"
q3["variants"] = V
q3["claim_verdict"] = verdict

# Not pre-registered, reported as labelled breakdowns:
# (a) YB net flow by market, using the YB contracts that emitted logs in the transaction
yb_market_of = {}
for m in C["yb_markets"]:
    for k in ("levamm", "pool", "virtual_pool"):
        yb_market_of[m[k].lower()] = f"{m['market']} {m['asset']}"
by_mkt = defaultdict(float)
for r in in_main:
    if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg"):
        mk = sorted({yb_market_of[lg["address"].lower()] for _, _, lg in by_tx.get(r["tx"], []) if lg["address"].lower() in yb_market_of})
        by_mkt[" + ".join(mk) if mk else "unknown"] += r["net_in"]
q3["yb_net_by_market"] = dict(by_mkt)
ACTIVE_BTC = {"7 WBTC", "8 cbBTC", "9 tBTC"}
q3["yb_net_rollup"] = {"btc_markets_only": sum(v for k, v in by_mkt.items() if "WETH" not in k),
                       "active_btc_markets_7_to_9_only": sum(v for k, v in by_mkt.items() if set(k.split(" + ")) <= ACTIVE_BTC),
                       "any_weth_market": sum(v for k, v in by_mkt.items() if "WETH" in k)}
yb_2145 = [r for r in in_main if r["class"] in ("yb_levamm_leg", "yb_curve_pool_leg") and 1794174300 <= r["ts"] < 1794175200]
q3["yb_net_2145_2200"] = sum(r["net_in"] for r in yb_2145)
q3["all_net_2145_2200"] = sum(r["net_in"] for r in in_main if 1794174300 <= r["ts"] < 1794175200)
# (b) S2: class 4 only if the LEVAMM emitted TokenExchange or the VirtualPool emitted any log
s2 = defaultdict(float)
for r in in_main:
    if r["class"] != "yb_levamm_leg":
        continue
    ev = by_tx.get(r["tx"], [])
    strict = any((ro == "yb_levamm" and t == TP["TokenExchange_twocrypto"]) or ro == "yb_vp" for ro, t, _ in ev)
    s2["strict" if strict else "fee_or_other_log_only"] += r["net_in"]
q3["s2_levamm_strict_split"] = dict(s2)
# (c) concentration of the non-PegKeeper liquidity class and of the largest single transaction
big = max(in_main, key=lambda r: abs(r["net_in"]))
q3["largest_single_leg"] = {"class": big["class"], "net_in": big["net_in"], "utc": utc(big["ts"]), "pool": big["pool"]}

# liquidity class detail (not pre-registered): deposits vs withdrawals and the largest leg's price effect
liq_rows = [r for r in in_main if r["class"] == "liquidity_non_pk"]
q3["liquidity_non_pk_detail"] = {"deposited": sum(r["net_in"] for r in liq_rows if r["net_in"] > 0),
                                 "withdrawn": -sum(r["net_in"] for r in liq_rows if r["net_in"] < 0),
                                 "n_legs": len(liq_rows), "all_liquidity_legs": all(r["leg"] == "liquidity" for r in liq_rows)}
if liq_rows:
    lb = max(liq_rows, key=lambda r: abs(r["net_in"]))
    pool_addr = [p for p in pools if pool_name[p] == lb["pool"]][0]
    q3["liquidity_non_pk_detail"]["largest"] = {
        "net_in": lb["net_in"], "utc": utc(lb["ts"]), "pool": lb["pool"],
        "pool_price_before": series[pool_addr][lb["block"] - 1], "pool_price_after": series[pool_addr][lb["block"]],
        "W_before": Wser[lb["block"] - 1], "W_after": Wser[lb["block"]], "pool_weight": wgt[pool_addr]}
    pk_meta = [p for p in C["pegkeepers"] if p["pool"].lower() == pool_addr][0]
    d0 = pk_meta["coin_decimals"][0]
    comp = {}
    for tag, blk in (("before", lb["block"] - 1), ("after", lb["block"])):
        c0 = int(st(pool_addr, "balances(uint256)", blk, (0,)), 16) / 10 ** d0
        c1 = int(st(pool_addr, "balances(uint256)", blk, (1,)), 16) / E18
        comp[tag] = {"paired_coin": c0, "crvusd": c1, "paired_share": c0 / (c0 + c1)}
    added = None
    for _, t, lg in by_tx.get(lb["tx"], []):
        if lg["address"].lower() == pool_addr and t == TP["AddLiquidity_ng"]:
            w = words(lg["data"])
            off = w[0] // 32
            n = w[off]
            amts = w[off + 1: off + 1 + n]
            added = {"paired_coin": amts[0] / 10 ** d0, "crvusd": amts[1] / E18}
    q3["liquidity_non_pk_detail"]["largest"].update({
        "pool_balances": comp, "amounts_added": added, "single_sided": bool(added) and min(added.values()) == 0,
        "pool_A": int(st(pool_addr, "A()", PRE), 16),
        "weight_definition": "pool TVL share at the block before the window, both coins at 1 USD, fixed for the window"})
    check(added is not None and abs(added["crvusd"] - lb["net_in"]) < 1.0, "largest liquidity leg matches its AddLiquidity crvUSD amount")

# 15 minute buckets
buckets = defaultdict(lambda: defaultdict(float))
for r in in_main:
    k = (r["ts"] - TS_START) // 900
    buckets[k][r["class"]] += r["net_in"]
q3["buckets_15m"] = {int(k): dict(v) for k, v in sorted(buckets.items())}
all_classes_net = {c: q3["main"][c]["net_in"] for c in CLASSES}
q3["total_net_in_main"] = sum(all_classes_net.values())

# ---------------- 30 day context (not pre-registered) ----------------
ctx_path = os.path.join(RAW, "context_aggregator_30d.json")
context = None
if os.path.exists(ctx_path):
    cp = load("context_aggregator_30d.json")["price"]
    cts = {int(k): int(v, 16) for k, v in load("context_pegkeepers_30d.json")["block_timestamps"].items()}
    vals = sorted((int(b), int(v, 16) / E18) for b, v in cp.items())
    since = [x for b, x in vals if cts[b] >= 1793318400]  # 2026-10-30 00:00 UTC
    context = {"n_samples": len(vals), "n_below_1": sum(1 for _, x in vals if x < 1),
               "mean": sum(x for _, x in vals) / len(vals), "max": max(x for _, x in vals),
               "since_30oct_n": len(since), "since_30oct_below_1": sum(1 for x in since if x < 1),
               "since_30oct_mean": sum(since) / len(since)}

watch = None
wpath = os.path.join(RAW, "context_watch.json")
if os.path.exists(wpath) and context is not None:
    cw = load("context_watch.json")
    crv_in_yb = {k: int(v["balance0"], 16) / E18 for k, v in cw["yb_pools"].items()}
    check(all(v["coin0"].lower().endswith(C["crvusd"][2:]) for v in cw["yb_pools"].values()), "crvUSD is coin 0 in every active Yield Basis pool")
    ceil = {k: int(v, 16) / E18 for k, v in cw["pegkeeper_debt_ceiling"].items()}
    ctsall = sorted(cts)
    above = [b for b, x in vals if x >= 1]
    last_above_ts = max(cts[b] for b in above) if above else None
    watch = {"pegkeeper_debt_total_window_start": q2["total_debt_start"],
             "pegkeeper_debt_ceiling_total": sum(ceil.values()), "pegkeeper_debt_ceiling": ceil,
             "crvusd_in_active_yb_pools": crv_in_yb, "crvusd_in_active_yb_pools_total": sum(crv_in_yb.values()),
             "crvusd_in_pegkeeper_pools_window_start": sum(int(st(p["pool"], "balances(uint256)", PRE, (1,)), 16) / E18 for p in C["pegkeepers"]),
             "last_sample_at_or_above_1_utc": utc(last_above_ts) if last_above_ts else None,
             "days_below_1_before_window": (TS_START - last_above_ts) / 86400 if last_above_ts else None}

# ---------------- Soft liquidation (C5) and hard liquidations ----------------
dec = {}
for m in C["mint_markets"] + C["llamalend_v1_markets"]:
    v = st(m["collateral"], "decimals()", PRE)
    dec[m["amm"].lower()] = int(v, 16) if v else 18
mk_name = {m["amm"].lower(): m["name"] for m in C["mint_markets"]}
mk_name.update({m["amm"].lower(): "LL " + m["name"] for m in C["llamalend_v1_markets"]})
sl = defaultdict(lambda: {"converted_usd": 0.0, "deliq_usd": 0.0, "loss_usd": 0.0, "loss_usd_prevblock": 0.0, "n": 0,
                          "mint": True})
sl_events = []
for n, mint in (("mint_markets", True), ("llamalend_v1", False)):
    for lg in LOGS[n]:
        if lg["topics"][0] != TP["TokenExchange_llamma"]:
            continue
        amm = lg["address"].lower()
        b = int(lg["blockNumber"], 16)
        w = words(lg["data"])
        sold_id, sold, bought_id, bought = w
        po = st(amm, "price_oracle()", b)
        pp = st(amm, "price_oracle()", b - 1)
        if po is None:
            check(False, f"price_oracle missing for {amm} at {b}")
            continue
        po = int(po, 16) / E18
        pp = int(pp, 16) / E18 if pp else po
        cd = dec[amm]
        rec = sl[mk_name[amm]]
        rec["mint"] = mint
        rec["n"] += 1
        if bought_id == 1:   # AMM gives collateral, receives crvUSD: soft liquidation
            col = bought / 10 ** cd
            usd = sold / E18
            rec["converted_usd"] += col * po
            rec["loss_usd"] += col * po - usd
            rec["loss_usd_prevblock"] += col * pp - usd
            loss = col * po - usd
            conv = col * po
        else:                # AMM receives collateral, gives crvUSD: de-liquidation
            col = sold / 10 ** cd
            usd = bought / E18
            rec["deliq_usd"] += col * po
            rec["loss_usd"] += usd - col * po
            rec["loss_usd_prevblock"] += usd - col * pp
            loss = usd - col * po
            conv = 0.0
        sl_events.append({"market": mk_name[amm], "block": b, "ts": BT.get(b), "direction": "soft" if bought_id == 1 else "de",
                          "collateral": col, "crvusd": usd, "price_oracle": po, "loss_usd": loss, "converted_usd": conv})
for k, v in sl.items():
    v["loss_pct_of_converted"] = (100 * v["loss_usd"] / v["converted_usd"]) if v["converted_usd"] > 0 else None
    check(v["converted_usd"] == 0 or abs(v["loss_usd"]) < 0.2 * (v["converted_usd"] + v["deliq_usd"]),
          f"soft liquidation loss for {k} is a small share of volume (decimals sanity)")
mint_conv = sum(v["converted_usd"] for v in sl.values() if v["mint"])
mint_loss = sum(v["loss_usd"] for v in sl.values() if v["mint"])
liq = []
for n in ("mint_markets", "llamalend_v1"):
    for lg in LOGS[n]:
        if lg["topics"][0] == TP["Liquidate"]:
            w = words(lg["data"])
            liq.append({"market_set": n, "block": int(lg["blockNumber"], 16), "collateral_received": w[0],
                        "stablecoin_received": w[1] / E18, "debt": w[2] / E18, "controller": lg["address"].lower()})
soft = {"markets": dict(sl), "mint_converted_usd": mint_conv, "mint_loss_usd": mint_loss,
        "mint_loss_pct": (100 * mint_loss / mint_conv) if mint_conv else None,
        "hard_liquidations_mint": sum(1 for x in liq if x["market_set"] == "mint_markets"),
        "hard_liquidations_llamalend": sum(1 for x in liq if x["market_set"] == "llamalend_v1"),
        "hard_liq_debt_mint": sum(x["debt"] for x in liq if x["market_set"] == "mint_markets"),
        "doc_reference_pct_per_day": 0.1, "doc_reference_pct_8h": 0.1 / 3}

# ---------------- YB DTV ----------------
ybres = {}
for m in C["yb_markets"]:
    if m["status"] != "active":
        continue
    pts = []
    for b in sorted({int(k.split("|")[2]) for k in S if k.startswith(m["levamm"].lower() + "|" + sel("get_state()"))}):
        gs = st(m["levamm"], "get_state()", b)
        lp = st(m["lp_oracle"], "price()", b)
        if not gs or not lp:
            continue
        w = words(gs)
        coll, debt = w[0] / E18, w[1] / E18
        val = coll * int(lp, 16) / E18
        pts.append((b, debt / val if val else None))
    fl = [d for b, d in pts if F0 <= b <= F1 and d is not None]
    allp = [d for b, d in pts if B0 - 1 <= b <= B1 and d is not None]
    ybres[f"{m['market']} {m['asset']}"] = {
        "n_points": len(allp), "dtv_min": min(allp), "dtv_max": max(allp),
        "flush_share_above_50": sum(1 for d in fl if d > 0.5) / len(fl) if fl else None,
        "max_abs_dev": max(abs(d - 0.5) for d in allp),
        "left_safety_band": any(d < 0.0625 or d > 0.53125 for d in allp),
        "path": [(b, d) for b, d in pts]}

# ---------------- borrow rate (WETH mint market) ----------------
weth = [m for m in C["mint_markets"] if m["name"] == "WETH"][0]
rate = {}
for b in range(PRE, B1 + 1, 25):
    v = st(weth["amm"], "rate()", b)
    if v:
        rate[b] = int(v, 16) * 365 * 86400 / E18
rb = sorted(rate)
rate_res = {"start_apr": rate[rb[0]], "end_apr": rate[rb[-1]], "max_apr": max(rate.values()),
            "max_block": max(rate, key=rate.get), "max_utc": utc(BT[max(rate, key=rate.get)])}
rate_res["rel_change"] = rate_res["end_apr"] / rate_res["start_apr"] - 1

# ---------------- prediction scoring ----------------
R = {}


def score(pid, ok, note, status=None):
    R[pid] = {"result": status or ("HIT" if ok else "MISS"), "note": note}


def hm(sec):
    return f"{sec / 60:.0f} min"


score("P01", steep[1] is not None and TS_F0 <= BT[steep[1]] < TS_F1,
      f"steepest 15 min ETH decline {100 * steep[0]:.2f}% starting {eth_res['steepest_15m_start_utc']} UTC")
score("P02", -0.12 <= mdd <= -0.05, f"ETH max drawdown in window {100 * mdd:.2f}%")
lag = BT[bWmin] - BT[mdd_trough]
score("P03", 0 <= lag <= 2700, f"W minimum {utc(BT[bWmin])}, ETH trough {utc(BT[mdd_trough])}, lag {lag / 60:.0f} min")
score("P04", q1["min_any_pool"] < 0.9951, f"lowest pool price {q1['min_any_pool']:.4f} ({q1['min_any_pool_name']})")
score("P05", q1["min_any_pool"] > 0.985, f"lowest pool price {q1['min_any_pool']:.4f}")
tb997 = q1["W"]["sec_below_0997"]
score("P06", 1800 <= tb997 <= 14400, f"weighted price below 0.997 for {hm(tb997)}")
score("P07", q1["W"]["sec_below_0995"] < 3600, f"weighted price below 0.995 for {hm(q1['W']['sec_below_0995'])}")
score("P08", rec_block is not None, f"recovery to 0.999: {'block ' + str(rec_block) if rec_block else 'not by 04:00 UTC'}")
ll = q3["main"]["llamma_arbitrage"]
score("P09", ll["net_in"] < 0, f"LLAMMA arbitrage net_in {ll['net_in']:,.0f} crvUSD over {ll['n_tx']} tx",
      None if ll["n_tx"] > 0 else "UNTESTABLE")
hl = q3["main"]["hard_liquidation"]
if soft["hard_liquidations_mint"] >= 3 and hl["n_tx"] > 0:
    score("P10", hl["net_in"] < 0, f"hard liquidation net_in {hl['net_in']:,.0f} over {hl['n_tx']} tx")
else:
    score("P10", False, f"{soft['hard_liquidations_mint']} mint hard liquidations, {hl['n_tx']} touched peg pools", "UNTESTABLE")
fl = q3["flush"]
ybf = fl["yb_levamm_leg"]["net_in"] + fl["yb_curve_pool_leg"]["net_in"]
others = {c: fl[c]["net_in"] for c in CLASSES if c not in ("yb_levamm_leg", "yb_curve_pool_leg")}
score("P11", ybf > 0 and ybf > max(others.values()),
      f"flush hour net_in YB combined {ybf:,.0f}, largest other {max(others, key=others.get)} {max(others.values()):,.0f}")
# P12: peak 15 minute bucket of YB curve pool leg net selling vs peak bucket of LEVAMM leg net buying, flush hour
fb = {k: v for k, v in q3["buckets_15m"].items() if TS_F0 <= TS_START + 900 * k < TS_F1}
if fb:
    k5 = max(fb, key=lambda k: fb[k].get("yb_curve_pool_leg", 0.0))
    k4 = min(fb, key=lambda k: fb[k].get("yb_levamm_leg", 0.0))
    has = fb[k5].get("yb_curve_pool_leg", 0) > 0 and fb[k4].get("yb_levamm_leg", 0) < 0
    score("P12", has and (k4 - k5) >= 1, f"curve pool leg sell peak bucket {utc(TS_START + 900 * k5)}, LEVAMM leg buy peak bucket {utc(TS_START + 900 * k4)}",
          None if has else "UNTESTABLE")
shares = {k: v["flush_share_above_50"] for k, v in ybres.items()}
score("P13", all(s is not None and s > 0.5 for s in shares.values()),
      "share of flush hour samples with DTV above 50%: " + ", ".join(f"{k} {100 * s:.0f}%" for k, s in shares.items() if s is not None))
v0 = V["V0_main_net_same_tx"]
score("P14", v0 > 0, f"V0 = {v0:,.0f} crvUSD (positive means sold into peg pools)")
score("P15", abs(v0 - CLAIM) / CLAIM > 0.25, f"V0 = {v0:,.0f} vs claim 4,100,000")
s16 = q3["yb_gross_sell_largest_sender_share"]
score("P16", s16 is not None and s16 > 0.5, f"largest single sender share of YB gross sells {100 * (s16 or 0):.0f}%")
nwd = sum(1 for p in C["pegkeepers"] if p["name"] in ("USDC", "USDT", "pyUSD", "frxUSD") and wdr[p["pegkeeper"].lower()] > 0)
score("P17", nwd >= 3, f"PegKeepers that withdrew: {nwd} of 4. Window-start debt total {tot0:,.0f}")
twd = sum(wdr.values())
score("P18", 2e6 <= twd <= 20e6, f"total withdrawn {twd:,.0f}")
score("P19", False, f"no PegKeeper withdrew. Window-start debt total {tot0:,.0f}, so no reserve was available ('no reserves to deploy')")
score("P20", False, "no withdraw actions", "UNTESTABLE")
score("P21", False, "reverted calls not scanned in release 1", "UNTESTABLE")
score("P22", 0.15 <= rate_res["rel_change"] <= 1.0, f"WETH mint rate {100 * rate_res['start_apr']:.2f}% to {100 * rate_res['end_apr']:.2f}% ({100 * rate_res['rel_change']:+.0f}%)")
score("P23", BT[rate_res["max_block"]] - BT[bWmin] > 1800, f"rate peak {rate_res['max_utc']}, W minimum {utc(BT[bWmin])}")
score("P24", False, "per-user soft liquidation state not measured in release 1", "UNTESTABLE")
eth_family = sum(v["converted_usd"] for k, v in sl.items() if v["mint"] and k in ("WETH", "wstETH"))
score("P25", mint_conv > 0 and eth_family / mint_conv > 0.6, f"WETH plus wstETH share of mint value converted {100 * eth_family / mint_conv if mint_conv else 0:.0f}%",
      None if mint_conv > 0 else "UNTESTABLE")
mlp = soft["mint_loss_pct"]
score("P26", mlp is not None and 0.2 <= mlp <= 3.0, f"mint market loss {mlp if mlp is None else round(mlp, 3)}% of value converted",
      None if mlp is not None else "UNTESTABLE")
# P27: fastest 30 min = 30 min interval with the largest ETH decline
k2 = 0
best30 = (0.0, None)
for i, b in enumerate(blist):
    while k2 < len(blist) and BT[blist[k2]] < BT[b] + 1800:
        k2 += 1
    if k2 >= len(blist):
        break
    r = eth[blist[k2]] / eth[b] - 1
    if r < best30[0]:
        best30 = (r, b)
if best30[1]:
    t0f = BT[best30[1]]
    inn = [e for e in sl_events if e["market"] in mk_name.values() and not e["market"].startswith("LL") and t0f <= e["ts"] < t0f + 1800]
    out = [e for e in sl_events if not e["market"].startswith("LL") and not (t0f <= e["ts"] < t0f + 1800)]
    ci, co = sum(e["converted_usd"] for e in inn), sum(e["converted_usd"] for e in out)
    li, lo = sum(e["loss_usd"] for e in inn), sum(e["loss_usd"] for e in out)
    if ci > 0 and co > 0 and lo > 0:
        score("P27", (li / ci) >= 2 * (lo / co), f"loss per unit converted: fastest 30 min {100 * li / ci:.3f}%, rest {100 * lo / co:.3f}%")
    else:
        score("P27", False, f"insufficient conversions to compare (in {ci:,.0f}, out {co:,.0f})", "UNTESTABLE")
score("P28", False, "per-user health path not measured in release 1", "UNTESTABLE")
score("P29", soft["hard_liquidations_mint"] <= 10, f"{soft['hard_liquidations_mint']} hard liquidations in mint markets")
score("P30", False, "open positions not checked for negative equity in release 1", "UNTESTABLE")
score("P31", False, "moved out of release 1", "UNTESTABLE")
w10 = [v for k, v in ybres.items() if k.startswith("10 ")][0]["max_abs_dev"]
btc_dev = [v["max_abs_dev"] for k, v in ybres.items() if not k.startswith("10 ")]
score("P32", w10 > max(btc_dev), f"max DTV deviation from 50%: WETH {100 * w10:.2f} pts, BTC markets max {100 * max(btc_dev):.2f} pts")
score("P33", not any(v["left_safety_band"] for v in ybres.values()), "DTV range " + ", ".join(f"{k} {100 * v['dtv_min']:.2f}% to {100 * v['dtv_max']:.2f}%" for k, v in ybres.items()))
score("P34", (1 - q1["aggregator"]["min"]) < 0.01, f"lowest aggregator price {q1['aggregator']['min']:.4f}, so LP value effect {100 * (1 - q1['aggregator']['min']):.2f}%")
for pid in ("P35", "P36", "P37", "P38"):
    score(pid, False, "cross-protocol comparison moved to phase 2", "UNTESTABLE")
score("P39", False, "meta prediction, not scored", "UNTESTABLE")
WEAK = {"P02", "P05", "P08", "P30", "P33", "P34"}
for k in R:
    R[k]["weak_test"] = k in WEAK

# ---------------- outputs ----------------
results = {"window": {"pre_block": PRE, "first_block": B0, "last_block": B1, "flush_first": F0, "flush_last": F1},
           "eth": eth_res, "btc": btc_res, "q1": q1, "q2": q2, "q3": {k: v for k, v in q3.items()}, "soft_liquidation": soft,
           "hard_liquidations": liq, "yb": {k: {kk: vv for kk, vv in v.items() if kk != "path"} for k, v in ybres.items()},
           "weth_rate": rate_res, "predictions": R, "context_aggregator_30d": context, "watch": watch,
           "checks": {"price_direction": {"agree": agree, "disagree": disagree, "get_p_used_as_crvusd_price": direction_flipped},
                      "sum_flows": sum_flows, "pool_balance_change": d_pool_bal}}


def wcsv(name, header, rowsx):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rowsx:
            w.writerow(r)


wcsv("prices_by_block.csv", ["block", "timestamp_utc", "W"] + [pool_name[p] for p in pools] + ["eth_usd", "btc_usd"],
     [[b, utc(BT[b]), f"{Wser[b]:.6f}"] + [f"{series[p][b]:.6f}" for p in pools] + [f"{eth[b]:.2f}", f"{btc[b]:.2f}"] for b in range(B0, B1 + 1)])
wcsv("pegkeeper_debt.csv", ["pegkeeper", "debt_start", "provided", "withdrawn", "debt_end"],
     [[k, f"{v['debt_start']:.2f}", f"{v['provided']:.2f}", f"{v['withdrawn']:.2f}", f"{v['debt_end']:.2f}"] for k, v in q2["pegkeepers"].items()])
wcsv("flows_by_tx.csv", ["block", "timestamp_utc", "pool", "class", "leg", "net_in_crvusd"],
     [[r["block"], utc(r["ts"]), r["pool"], r["class"], r["leg"], f"{r['net_in']:.2f}"] for r in sorted(rows, key=lambda r: (r["block"], r["pool"]))])
wcsv("flows_15m.csv", ["bucket_start_utc"] + CLASSES,
     [[utc(TS_START + 900 * k)] + [f"{q3['buckets_15m'].get(k, {}).get(c, 0.0):.2f}" for c in CLASSES] for k in range(32)])
wcsv("soft_liquidation_by_market.csv", ["market", "mint_market", "n_exchanges", "converted_usd", "deliquidated_usd", "loss_usd", "loss_pct_of_converted"],
     [[k, v["mint"], v["n"], f"{v['converted_usd']:.2f}", f"{v['deliq_usd']:.2f}", f"{v['loss_usd']:.2f}",
       "" if v["loss_pct_of_converted"] is None else f"{v['loss_pct_of_converted']:.4f}"] for k, v in sorted(sl.items())])
wcsv("yb_dtv.csv", ["market", "block", "timestamp_utc", "dtv"],
     [[k, b, utc(BT[b]) if b in BT else "", "" if d is None else f"{d:.6f}"] for k, v in ybres.items() for b, d in v["path"]])
wcsv("weth_rate.csv", ["block", "timestamp_utc", "apr"], [[b, utc(BT[b]), f"{rate[b]:.6f}"] for b in rb])
wcsv("predictions_scored.csv", ["id", "result", "weak_test", "note"], [[k, v["result"], v["weak_test"], v["note"]] for k, v in R.items()])
with open(os.path.join(DATA, "results.json"), "w") as f:
    json.dump(results, f, indent=1, sort_keys=True)

# ---------------- phase 1b ----------------
sys.path.insert(0, os.path.dirname(__file__))
import recompute_p1b  # noqa: E402
P1B = recompute_p1b.main()
FAIL.extend(recompute_p1b.FAIL)

if os.environ.get("SKIP_CHARTS") != "1":
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import charts  # noqa: E402
        charts.main(ROOT)
    except ImportError as e:
        print("charts skipped:", e)

outs = sorted(f for f in os.listdir(DATA) if f != "SHA256SUMS")
with open(os.path.join(DATA, "SHA256SUMS"), "w") as f:
    for name in outs:
        f.write(hashlib.sha256(open(os.path.join(DATA, name), "rb").read()).hexdigest() + "  " + name + "\n")

print(json.dumps({k: v["result"] for k, v in R.items()}))
print("FAILED CHECKS:", FAIL if FAIL else "none")
sys.exit(1 if FAIL else 0)

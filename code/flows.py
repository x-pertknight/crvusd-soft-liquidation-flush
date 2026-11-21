"""Release 1 flow accounting: build per transaction and pool rows, aggregate them by class, and sum the Yield
Basis variants. Moved out of recompute.py unchanged so it can be tested; recompute.py imports it.
Standard library only."""
from collections import defaultdict

CLASSES = ["pegkeeper", "hard_liquidation", "llamma_arbitrage", "yb_levamm_leg", "yb_curve_pool_leg",
           "borrower_action", "liquidity_non_pk", "other"]
YB_CLASSES = ("yb_levamm_leg", "yb_curve_pool_leg")


def build_rows(net, pk_leg, tx_block, matches, legtype, tx, bt, pool_name):
    """One row per transaction and pool. net and pk_leg map tx -> pool -> crvUSD into the pool (negative = out).
    A transaction takes the first matching rule class; with no match it is a liquidity event if every leg is
    liquidity, else "other". PegKeeper legs get their own class. Returns (rows, multi) where multi counts
    transactions that matched more than one rule."""
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
        t = tx.get(h, {})
        for pool, v in legs.items():
            rows.append({"tx": h, "block": b, "ts": bt[b], "pool": pool_name[pool], "class": cls,
                         "net_in": v, "leg": legtype(h, pool), "from": (t.get("from") or "").lower(),
                         "to": (t.get("to") or "").lower()})
    for h, legs in pk_leg.items():
        b = tx_block[h]
        for pool, v in legs.items():
            if v != 0:
                rows.append({"tx": h, "block": b, "ts": bt[b], "pool": pool_name[pool], "class": "pegkeeper",
                             "net_in": v, "leg": "liquidity", "from": "", "to": ""})
    return rows, multi


def flows_match_balance(sum_flows, d_pool_bal):
    """Admin fee tolerance: 1,000 crvUSD or 0.2% of the balance change, whichever is larger."""
    return abs(sum_flows - d_pool_bal) <= max(1000.0, 0.002 * abs(d_pool_bal))


def agg_class(rs):
    """Per class: net crvUSD into the peg pools, gross sold (positive legs), gross bought, distinct transactions."""
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


def yb(rs, gross=False, pools_only=None, classes=YB_CLASSES):
    """Net crvUSD sold into the peg pools by the given classes. gross=True keeps only positive legs (V2)."""
    s = 0.0
    for r in rs:
        if r["class"] in classes and (pools_only is None or r["pool"] in pools_only):
            if gross and r["net_in"] <= 0:
                continue
            s += r["net_in"]
    return s

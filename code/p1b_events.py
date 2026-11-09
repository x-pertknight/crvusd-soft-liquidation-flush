"""Phase 1b event selection from Chainlink only (PHASE_1B_PREREG.md section 1, PHASE_1B_ADDENDUM.md section 3).
Standard library only. Usage: python3 -I code/p1b_events.py writes data/phase1b_events.json."""
import gzip
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "code", "raw", "phase1b")
THRESH = {"ETH": 0.05, "BTC": 0.03}
WINDOW = 3600
CLUSTER = 86400
JOINT = 7200
SLOT = 12
NOV8 = (1794168000, 1794196800)  # 2026-11-08 20:00 to 2026-11-09 04:00 UTC


def gz(name):
    with gzip.open(os.path.join(RAW, name + ".json.gz"), "rt") as f:
        return json.load(f)


def signed(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= 1 << 255 else v


def points(asset):
    seen = {}
    for rec in gz(f"chainlink_{asset.lower()}")["records"]:
        if rec["truncated"]:
            continue
        for lg in rec["response"]["result"] or []:
            key = (int(lg["blockNumber"], 16), int(lg["logIndex"], 16))
            seen[key] = (int(lg["timeStamp"], 16), key[0], signed(lg["topics"][1]) / 1e8)
    return [seen[k] for k in sorted(seen)]


def declines(pts, end_ts):
    out = []
    n = len(pts)
    j_hi = 0
    for i in range(n):
        ts_i, blk_i, p_i = pts[i]
        last_ts = pts[i + 1][0] - SLOT if i + 1 < n else end_ts
        horizon = last_ts + WINDOW
        lo, lo_ts = None, None
        j = i + 1
        while j < n and pts[j][0] <= horizon:
            if lo is None or pts[j][2] < lo:
                lo, lo_ts = pts[j][2], pts[j][0]
            j += 1
        if lo is None or lo >= p_i:
            continue
        out.append({"level_ts": ts_i, "level_block": blk_i, "price": p_i, "low": lo, "low_ts": lo_ts,
                    "decline": (p_i - lo) / p_i, "start_ts": max(ts_i, lo_ts - WINDOW)})
    return out


def select():
    period = gz("period")
    end_ts = period["end_ts"]
    per_asset = {}
    n_points = {}
    for asset in ("BTC", "ETH"):
        pts = points(asset)
        n_points[asset] = len(pts)
        q = sorted((d for d in declines(pts, end_ts) if d["decline"] >= THRESH[asset]), key=lambda d: d["start_ts"])
        clusters = []
        for d in q:
            if clusters and d["start_ts"] - clusters[-1][-1]["start_ts"] < CLUSTER:
                clusters[-1].append(d)
            else:
                clusters.append([d])
        evs = []
        for cl in clusters:
            top = max(cl, key=lambda d: (d["decline"], -d["start_ts"]))
            evs.append({"asset": asset, "t0": top["start_ts"], "decline": top["decline"], "n_moves": len(cl),
                        "price": top["price"], "low": top["low"], "low_ts": top["low_ts"]})
        per_asset[asset] = evs
    # joint events
    events = []
    used_eth = set()
    for b in per_asset["BTC"]:
        best = None
        for k, e in enumerate(per_asset["ETH"]):
            if k in used_eth or abs(e["t0"] - b["t0"]) >= JOINT:
                continue
            if best is None or abs(e["t0"] - b["t0"]) < abs(per_asset["ETH"][best]["t0"] - b["t0"]):
                best = k
        if best is None:
            events.append({"kind": "BTC", "t0": b["t0"], "btc": b, "eth": None})
        else:
            used_eth.add(best)
            e = per_asset["ETH"][best]
            events.append({"kind": "joint", "t0": min(b["t0"], e["t0"]), "btc": b, "eth": e})
    for k, e in enumerate(per_asset["ETH"]):
        if k not in used_eth:
            events.append({"kind": "ETH", "t0": e["t0"], "btc": None, "eth": e})
    events.sort(key=lambda e: e["t0"])
    n_before_cap = len(events)
    for e in events:
        e["is_8_november"] = NOV8[0] <= e["t0"] < NOV8[1]
    if n_before_cap > 12:
        btc = sorted([e for e in events if e["btc"]], key=lambda e: -e["btc"]["decline"])[:6]
        eth = sorted([e for e in events if e["eth"]], key=lambda e: -e["eth"]["decline"])[:6]
        keep = {id(e) for e in btc + eth} | {id(e) for e in events if e["is_8_november"]}
        selected = [e for e in events if id(e) in keep]
    else:
        selected = list(events)
    for i, e in enumerate(selected):
        e["id"] = f"E{i + 1:02d}"
        e["window_start_ts"] = e["t0"] - 2 * 3600
        e["window_end_ts"] = e["t0"] + 6 * 3600
    return {"period": {"start_block": period["period_start_block"], "end_block": period["period_end_block"],
                       "end_ts": end_ts},
            "chainlink_points": n_points, "qualifying_events_before_cap": n_before_cap,
            "all_events": events, "selected": selected}


if __name__ == "__main__":
    import time
    r = select()
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(r, open(os.path.join(ROOT, "data", "phase1b_events.json"), "w"), indent=1, sort_keys=True)
    f = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))  # noqa: E731
    print("points", r["chainlink_points"], "events before cap", r["qualifying_events_before_cap"])
    for e in r["all_events"]:
        tag = e.get("id", "--")
        print(tag, e["kind"], f(e["t0"]), "BTC %.2f%%" % (100 * e["btc"]["decline"]) if e["btc"] else "",
              "ETH %.2f%%" % (100 * e["eth"]["decline"]) if e["eth"] else "", "8nov" if e["is_8_november"] else "")

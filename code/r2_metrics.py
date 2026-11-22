"""Release 2 metrics: series, events, decomposition of the slow drain, governance, latest state. Standard library only."""
import collections
import hashlib
import os

import r2_lib as L

E18 = L.E18
USDT = 1


def pk_state(d, k, rd):
    """Balance test and band test for one PegKeeper read (see PREREG_R2_ADDENDUM.md section 2)."""
    mul = 10 ** (18 - d["pks"][k]["coin_decimals"][0])
    provide_side = rd["bal_other"] * mul > rd["bal_crv"]
    gap = abs(rd["get_p"] - rd["p_oracle"]) if rd["get_p"] is not None and rd["p_oracle"] is not None else None
    return {"provide_side": provide_side, "gap": gap}


# ---------------------------------------------------------------- series
def price_runs(grid):
    """Maximal runs of consecutive samples with aggregator price at or above 1."""
    runs, cur = [], []
    for r in grid:
        if r["price_wei"] >= E18:
            cur.append(r)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def total_path(d):
    """Total debt after every event across all five PegKeepers, plus the sampled series."""
    cur = list(d["grid"][0]["debt_wei"])
    pts = [(d["grid"][0]["ts"], sum(cur))]
    allev = sorted(((e["block"], e["idx"], k, e) for k, n in enumerate(L.NAMES) for e in d["events"][n]
                    if e["block"] > d["grid"][0]["block"]), key=lambda t: t[:2])
    for _, _, k, e in allev:
        cur[k] += e["wei"] if e["type"] == "Provide" else -e["wei"]
        pts.append((e["ts"], sum(cur)))
    return pts


def series_metrics(d):
    grid = d["grid"]
    runs = price_runs(grid)
    long_runs = [r for r in runs if len(r) >= 2]
    last_ge1 = max((r["ts"] for r in grid if r["price_wei"] >= E18))
    pts = total_path(d)
    peak_ev = max(pts, key=lambda p: p[1])
    peak_grid = max(grid, key=lambda r: sum(r["debt_wei"]))
    out = {"samples": len(grid), "first_ts": grid[0]["ts"], "last_ts": grid[-1]["ts"], "last_block": grid[-1]["block"],
           "share_price_ge1": sum(r["price_wei"] >= E18 for r in grid) / len(grid),
           "runs_ge1_any": len(runs), "runs_ge1_2plus_samples": len(long_runs),
           "run_list": [[iso_pair(r)] for r in long_runs], "last_ge1_sample_ts": last_ge1,
           "last_long_run_end_ts": long_runs[-1][-1]["ts"] if long_runs else None,
           "peak_total_events": peak_ev[1] / E18, "peak_total_events_ts": peak_ev[0],
           "peak_total_sampled": sum(peak_grid["debt_wei"]) / E18, "peak_total_sampled_ts": peak_grid["ts"]}
    out["per_pk"] = {}
    for k, n in enumerate(L.NAMES):
        nz = [r for r in grid if r["debt_wei"][k] > E18]
        path = L.debt_path(d, k)
        out["per_pk"][n] = {"samples_nonzero": len(nz), "max_sampled": max(r["debt"][k] for r in grid),
                            "max_after_events": max(p[2] for p in path) / E18,
                            "debt_at_oct13": L.debt_at(path, L.OCT13) / E18,
                            "last_nonzero_sample_ts": nz[-1]["ts"] if nz else None,
                            "zero_since_ts": zero_since(path)}
    return out


def iso_pair(run):
    return [L.iso(run[0]["ts"]), L.iso(run[-1]["ts"]), len(run)]


def zero_since(path):
    """Timestamp of the event after which debt stayed under 1 crvUSD to the end, or None if it never held debt."""
    last = None
    for blk, ts, debt, e in path:
        if debt >= E18:
            last = None
        elif last is None and e is not None:
            last = ts
    return last


# ---------------------------------------------------------------- events
def sums(d, k, since=L.START_TS):
    evs = [e for e in d["events"][L.NAMES[k]] if e["ts"] >= since]
    p = sum(e["wei"] for e in evs if e["type"] == "Provide")
    w = sum(e["wei"] for e in evs if e["type"] == "Withdraw")
    return {"n_provide": sum(e["type"] == "Provide" for e in evs), "n_withdraw": sum(e["type"] == "Withdraw" for e in evs),
            "provided": p / E18, "withdrawn": w / E18}


def usdt_drain(d, sm):
    """Peak, fall and Withdraw count for the USDT PegKeeper from its peak to zero, plus the days from first Withdraw."""
    path = L.debt_path(d, USDT)
    peak = max(path, key=lambda p: p[2])
    zero_ts = sm["per_pk"]["USDT"]["zero_since_ts"]
    after = [e for e in d["events"]["USDT"] if e["block"] > peak[0] and e["ts"] <= zero_ts]
    w = sum(e["wei"] for e in after if e["type"] == "Withdraw")
    p = sum(e["wei"] for e in after if e["type"] == "Provide")
    fall = peak[2] - 0
    first_w = next((e for e in d["events"]["USDT"] if e["ts"] > sm["last_ge1_sample_ts"] and e["type"] == "Withdraw"), None)
    return {"peak": peak[2] / E18, "peak_ts": peak[1], "fall": fall / E18, "n_withdraw_peak_to_zero":
            sum(e["type"] == "Withdraw" for e in after), "explained_share": (w - p) / fall if fall else None,
            "first_withdraw_after_last_ge1_ts": first_w["ts"] if first_w else None,
            "days_first_withdraw_to_zero": (zero_ts - first_w["ts"]) / 86400 if first_w else None}


def event_prices(d):
    """Provide events with the aggregator price read at the block before. Needs r2_extra.json."""
    if not d["extra"]:
        return []
    return [{"pk": x["pk"], "block": x["block"], "price": L.hx(x["reads"][0]) / E18,
             "ts": next(e["ts"] for e in d["events"][x["pk"]] if e["block"] == x["block"])}
            for x in d["extra"]["events"] if x["type"] == "Provide"]


def event_metrics(d, sm):
    out = {"per_pk": {n: sums(d, k) for k, n in enumerate(L.NAMES)}, "usdt_drain": usdt_drain(d, sm)}
    others = [k for k in range(5) if k != USDT]
    out["other_four_never_nonzero"] = sum(sm["per_pk"][L.NAMES[k]]["samples_nonzero"] == 0 for k in others)
    out["other_four_provided_since_sep"] = sum(sums(d, k)["provided"] for k in others)
    pv = event_prices(d)
    out["provides_with_price"] = len(pv)
    out["provides_at_price_below_1"] = sum(p["price"] < 1 for p in pv)
    days = {L.iso(p["ts"])[:10] for p in pv if p["price"] >= 1 and p["ts"] < L.OCT13 + 86400}
    out["provide_days_at_price_ge1_before_oct14"] = sorted(days)
    out["gaps_over_3_days_while_stuck"] = stuck_gaps(d)
    return out


def stuck_gaps(d):
    """Samples with debt above 1 crvUSD, no event in the previous 3 days, price below 1 and the pool on the
    withdraw side. A debt that sat unchanged under these conditions would be a hold the balance test cannot explain."""
    from r2_checks import reads_of
    found = []
    for k, n in enumerate(L.NAMES):
        evts = [e["ts"] for e in d["events"][n]]
        for r in d["grid"]:
            if r["debt_wei"][k] <= E18 or r["price_wei"] >= E18:
                continue
            if any(r["ts"] - 3 * 86400 < t <= r["ts"] for t in evts):
                continue
            key = f"{r['block']}:{k}"
            if key in d["tier2"] and not pk_state(d, k, reads_of(d, key))["provide_side"]:
                found.append([n, L.iso(r["ts"])])
    return found


# ---------------------------------------------------------------- decomposition
HOLD = ["a_provide_side", "e_withdraw_paused", "d_outside_band", "bc_allowed_no_landing"]


def classify(d, k, i, key, deviation):
    """One state per sampled block with debt above 1 crvUSD and price below 1, in the order fixed in the addendum."""
    from r2_checks import reads_of
    rd = reads_of(d, key)
    st = pk_state(d, k, rd)
    nxt = d["grid"][i + 1]["debt_wei"][k] if i + 1 < len(d["grid"]) else None
    if nxt is not None and nxt < d["grid"][i]["debt_wei"][k]:
        state = "g_drained_next_sample"
    elif st["provide_side"]:
        state = "a_provide_side"
    elif (rd["killed"] or 0) & 2:
        state = "e_withdraw_paused"
    elif rd["withdraw_allowed"] == 0:
        state = "d_outside_band"
    else:
        state = "bc_allowed_no_landing"
    sim = "not simulated" if rd["sim"] is None else L.sim_outcome(rd["sim"])
    return state, st, rd, sim


def deviation_at(d, ts):
    """price_deviation from the daily Regulator reads, the latest read at or before ts."""
    best = None
    for b, v in sorted(d["daily"].items(), key=lambda t: int(t[0])):
        best = L.hx(v["price_deviation()"])
    return best


def decomposition(d, write_csv):
    idx = {r["block"]: i for i, r in enumerate(d["grid"])}
    rows, groups = [], collections.defaultdict(collections.Counter)
    sim_in_bc = collections.Counter()
    dev = deviation_at(d, 0)
    for key in sorted(d["tier2"], key=lambda s: (int(s.split(":")[0]), int(s.split(":")[1]))):
        b, k = map(int, key.split(":"))
        i = idx[b]
        state, st, rd, sim = classify(d, k, i, key, dev)
        r = d["grid"][i]
        in_band = st["gap"] is not None and st["gap"] <= dev
        rows.append([b, r["ts"], L.NAMES[k], r["price"], r["debt"][k], int(st["provide_side"]), rd["killed"],
                     rd["withdraw_allowed"] == L.hx("0x" + "f" * 64), int(in_band),
                     int(st["gap"] is not None and st["gap"] > 5 * 10 ** 14), state, sim])
        for g in group_names(L.NAMES[k], r):
            groups[g][state] += 1
        if state == "bc_allowed_no_landing":
            sim_in_bc[sim] += 1
    write_csv("r2_decomposition.csv", ["block", "ts", "pegkeeper", "agg_price", "debt", "provide_side", "killed",
                                       "withdraw_allowed_max", "spot_in_band", "spot_outside_default_0005", "state",
                                       "simulated_update"], rows)
    return {"groups": {g: summarize(c) for g, c in groups.items()}, "sim_inside_bc": dict(sim_in_bc),
            "price_deviation_on_chain": dev,
            "provide_side_share_usdt_drain": provide_share(rows, "usdt_drain"),
            "outside_default_band_share_usdt_drain": band_share(rows),
            "outside_actual_band_share_usdt_drain": actual_outside_share(rows)}


def group_names(name, r):
    g = ["all"]
    if name == "USDT":
        g.append("usdt_all")
        if r["ts"] >= L.OCT13 and r["debt"][USDT] > 1e6:
            g.append("usdt_drain")
    return g


def summarize(c):
    n = sum(c.values())
    holds = sum(c[s] for s in HOLD)
    out = {"n": n, "counts": dict(c), "shares_all_six": {s: c[s] / n for s in list(HOLD) + ["g_drained_next_sample"]}}
    out["shares_of_holds"] = {s: (c[s] / holds if holds else None) for s in HOLD}
    out["n_holds"] = holds
    return out


def drain_rows(rows):
    return [r for r in rows if r[2] == "USDT" and r[1] >= L.OCT13 and r[4] > 1e6]


def provide_share(rows, _g):
    dr = drain_rows(rows)
    return sum(r[5] for r in dr) / len(dr) if dr else None


def band_share(rows):
    dr = drain_rows(rows)
    return sum(r[9] for r in dr) / len(dr) if dr else None


# ---------------------------------------------------------------- governance and latest state
def governance(d):
    reg = [(L.iso_ts(x["block_timestamp"]), x["block_number"], (x.get("decoded") or {}).get("method_call", "raw"))
           for x in d["bs_reg"]]
    since = [r for r in reg if r[0] >= L.START_TS]
    param = [r for r in reg if r[2].split("(")[0] in ("PriceDeviation", "WorstPriceThreshold", "DebtParameters",
                                                      "SetAggregator", "SetKilled")]
    agg = [(L.iso_ts(x["block_timestamp"]), (x.get("decoded") or {}).get("method_call", "raw")) for x in d["bs_agg"]]
    daily = {}
    for name in ("alpha()", "beta()", "price_deviation()", "worst_price_threshold()", "aggregator()", "is_killed()"):
        daily[name] = sorted({v[name] for v in d["daily"].values()})
    ceil = {}
    if d["extra"]:
        for n in L.NAMES:
            seq = [(int(b), L.hx(v[n][0]), L.hx(v[n][1])) for b, v in sorted(d["extra"]["ceilings"].items(),
                                                                          key=lambda t: int(t[0]))]
            ceil[n] = {"ceiling_values": sorted({c / E18 for _, c, _ in seq}),
                       "held_min": min(h for _, _, h in seq) / E18, "held_max": max(h for _, _, h in seq) / E18,
                       "ceiling_first": seq[0][1] / E18, "ceiling_last": seq[-1][1] / E18}
    return {"regulator_events_total": len(reg), "regulator_events_since_sep": [[L.iso(r[0]), r[2]] for r in since],
            "regulator_param_events_all_time": [[L.iso(r[0]), r[2]] for r in param],
            "aggregator_events_since_sep": [[L.iso(t), c] for t, c in agg if t >= L.START_TS],
            "aggregator_pair_events_2026": [[L.iso(t), c] for t, c in agg if t >= 1767225600],
            "daily_distinct_values": daily, "factory_ceilings_daily": ceil,
            "pegkeeper_count_at_head": len(d["discover"]["regulator_peg_keepers_raw"])}


def latest_state(d):
    f = d["final"]
    if not f:
        return {"note": "r2_final.json missing"}
    return f["summary"] if "summary" in f else f


def write_series_csv(d, write_csv):
    rows = [[r["block"], r["ts"], L.iso(r["ts"]), f"{r['price']:.9f}"] + [f"{x:.2f}" for x in r["debt"]]
            for r in d["grid"]]
    write_csv("r2_series.csv", ["block", "ts", "utc", "agg_price"] + [f"debt_{n}" for n in L.NAMES], rows)
    ev = [[n, e["block"], e["ts"], L.iso(e["ts"]), e["type"], f"{e['wei'] / E18:.6f}", e["tx"]]
          for n in L.NAMES for e in d["events"][n] if e["ts"] >= L.START_TS]
    write_csv("r2_events.csv", ["pegkeeper", "block", "ts", "utc", "type", "amount", "tx"], sorted(ev, key=lambda r: r[1]))


def check_sums(sums):
    """Compare the r2_ output hashes with data/R2_SHA256SUMS. WRITE_R2_SUMS=1 writes the file instead."""
    path = os.path.join(L.ROOT, "data", "R2_SHA256SUMS")
    if os.environ.get("WRITE_R2_SUMS") == "1":
        open(path, "w").write("\n".join(sums) + "\n")
        return True
    if not os.path.exists(path):
        print("note: data/R2_SHA256SUMS not written yet")
        return True
    return open(path).read().split("\n")[:-1] == sums


def actual_outside_share(rows):
    dr = drain_rows(rows)
    return sum(1 - r[8] for r in dr) / len(dr) if dr else None


def fallback_kill(d, sm):
    """The fallback kill fixed in PREDICTIONS_R2.md: all five at zero within 48 hours of the last fall below 1."""
    t0 = next(r["ts"] for r in d["grid"] if r["ts"] > sm["last_ge1_sample_ts"])
    zero = {n: sm["per_pk"][n]["zero_since_ts"] for n in L.NAMES}
    late = {n: (z - t0) / 3600 for n, z in zero.items() if z is not None and z > t0}
    still = sorted(n for n in L.NAMES if (sm["per_pk"][n]["last_nonzero_sample_ts"] or 0) > t0)
    return {"first_sample_below_1_after_last_ge1": L.iso(t0), "hours_from_t0_to_zero": late,
            "pegkeepers_with_debt_after_t0": still, "met": (max(late.values()) <= 48) if late else True}


# ---------------------------------------------------------------- scoring
def hitmiss(ok):
    return "HIT" if ok else "MISS"


def score_predictions(d, res):
    sm, ev, dec, gov = res["series"], res["events"], res["decomposition"], res["governance"]
    ud, pk = ev["usdt_drain"], sm["per_pk"]
    out = []

    def add(i, ok, msg):
        out.append([i, ok if isinstance(ok, str) else hitmiss(ok), msg])
    peak = sm["peak_total_sampled"]
    add("R2-01", 30e6 <= peak <= 80e6, f"peak sampled total {peak:,.0f} at {L.iso(sm['peak_total_sampled_ts'])}; "
        f"after events {sm['peak_total_events']:,.0f}")
    o13 = pk["USDT"]["debt_at_oct13"]
    add("R2-02", 25e6 <= o13 <= 45e6, f"USDT debt at 13 Oct 00:00 UTC {o13:,.0f}")
    z = pk["USDT"]["zero_since_ts"]
    add("R2-03", "2026-10-22" <= L.iso(z)[:10] <= "2026-10-30", f"USDT debt fell under 1 at {L.iso(z)}")
    add("R2-04", ud["explained_share"] >= 0.95 and 20 <= ud["n_withdraw_peak_to_zero"] <= 3000,
        f"{ud['n_withdraw_peak_to_zero']} Withdraws from the peak ({ud['peak']:,.0f} at {L.iso(ud['peak_ts'])}) to zero; "
        f"events explain {ud['explained_share']:.4f} of the fall")
    dd = ud["days_first_withdraw_to_zero"]
    add("R2-05", dd is not None and 2 <= dd <= 15, f"{dd:.2f} days from the first Withdraw after "
        f"{L.iso(ud['first_withdraw_after_last_ge1_ts'])} to zero")
    add("R2-06", ev["other_four_never_nonzero"] >= 3 and ev["other_four_provided_since_sep"] < 2e6,
        f"{ev['other_four_never_nonzero']} of the other four never held debt; they provided "
        f"{ev['other_four_provided_since_sep']:,.0f} since 1 Sep")
    end = sm["last_long_run_end_ts"]
    add("R2-07", 1 <= sm["runs_ge1_2plus_samples"] <= 8 and "2026-10-12" <= L.iso(end)[:10] <= "2026-10-16",
        f"{sm['runs_ge1_2plus_samples']} stretches of 2+ samples at or above 1; last ends {L.iso(end)}")
    add("R2-08", 0.03 <= sm["share_price_ge1"] <= 0.30, f"share of samples at or above 1: {sm['share_price_ge1']:.4f}")
    if ev["provides_with_price"]:
        add("R2-09", ev["provides_at_price_below_1"] <= 2, f"{ev['provides_at_price_below_1']} of "
            f"{ev['provides_with_price']} Provide events had price below 1 at the block before")
    else:
        add("R2-09", "UNTESTABLE", "event price reads missing")
    ps = dec["provide_side_share_usdt_drain"]
    add("R2-10", ps is not None and 0.40 <= ps <= 0.90, f"provide side in {ps:.4f} of USDT drain samples")
    ob = dec["outside_actual_band_share_usdt_drain"]
    add("R2-11", ob is not None and ob < 0.10, f"outside the on-chain band {ob:.4f} (price_deviation is "
        f"{dec['price_deviation_on_chain'] / E18}); outside the 0.0005 default {dec['outside_default_band_share_usdt_drain']:.4f}")
    add("R2-12", len(gov["regulator_events_since_sep"]) == 0 and gov["pegkeeper_count_at_head"] == 5,
        f"{len(gov['regulator_events_since_sep'])} Regulator events since 1 Sep; {gov['pegkeeper_count_at_head']} PegKeepers listed")
    agg = d["discover"]["aggregator_address"]
    add("R2-13", agg.lower() == "0x18672b1b0c623a30089a280ed9256379fb0e4e62", f"regulator.aggregator() = {agg}")
    add_r14(d, add)
    add_latest(d, add)
    zs = {n: pk[n]["zero_since_ts"] for n in L.NAMES if pk[n]["zero_since_ts"]}
    span = (max(zs.values()) - min(zs.values())) / 86400 if zs else 0
    add("R2-18", span <= 7 and "2026-10-22" <= L.iso(max(zs.values()))[:10] <= "2026-10-30",
        "last time under 1 crvUSD: " + ", ".join(n + " " + L.iso(t)[:10] for n, t in zs.items()) + f"; span {span:.1f} days")
    sg = ev["gaps_over_3_days_while_stuck"]
    add("R2-19", len(sg) == 0, f"{len(sg)} samples with debt unchanged for 3 days, price below 1, withdraw side")
    pdays = ev["provide_days_at_price_ge1_before_oct14"]
    add("R2-20", (len(pdays) >= 2) if ev["provides_with_price"] else "UNTESTABLE",
        f"{len(pdays)} days with a Provide at price at or above 1 before 14 Oct")
    return sorted(out, key=lambda r: r[0])


def add_r14(d, add):
    if not d["extra"]:
        add("R2-14", "UNTESTABLE", "pre block reads missing")
        return
    pre = d["extra"]["pre"]
    tot = sum(L.hx(v[0]) for v in pre["per_pk"].values()) / E18
    ceil = d["extra"]["ceilings"]
    first = ceil[sorted(ceil, key=int)[0]]
    csum = sum(L.hx(v[0]) for v in first.values()) / E18
    add("R2-14", 250e6 <= tot <= 400e6 and abs(tot - 324e6) <= 0.05 * 324e6,
        f"sum of provide_allowed() at block {pre['block']} is {tot:,.0f} (price {L.hx(pre['aggregator_price']) / E18:.6f}, "
        f"below 1, so every allowance is 0). Factory debt ceilings sum at 1 Sep: {csum:,.0f}")


def add_latest(d, add):
    f = d["final"]
    if not f:
        for i in ("R2-15", "R2-16", "R2-17"):
            add(i, "UNTESTABLE", "final read missing")
        return
    price = f["agg_price_wei"] / E18
    add("R2-15", all(x < E18 for x in f["debt_wei"]),
        f"block {f['block']} at {L.iso(f['ts'])} UTC, debts {[round(x / E18, 2) for x in f['debt_wei']]}")
    add("R2-16", 0.9970 <= price <= 0.9995, f"aggregator price {price:.6f} at block {f['block']}, {L.iso(f['ts'])} UTC")
    api = f["api"]["body"]["data"]["usd_price"]
    add("R2-17", abs(api - price) <= 0.001,
        f"API {api:.6f} (updated {f['api']['body']['data']['last_updated']}) vs on-chain {price:.6f}")


# ---------------------------------------------------------------- rebuild conditions
def rebuild(d):
    """For hours with price at or above 1 and for the final block: which of the other provide conditions held."""
    rb = d.get("rebuild")
    if not rb:
        return {"note": "r2_rebuild.json missing"}
    out = {"hours_price_ge1": len(rb["blocks"]) - 1, "per_pk": {}, "final": {}}
    for k, n in enumerate(L.NAMES):
        mul = 10 ** (18 - d["pks"][k]["coin_decimals"][0])
        rows = []
        for b in rb["blocks"]:
            r = rb["reads"][str(b)][n]
            rows.append((b, L.hx(r[0]) * mul > L.hx(r[1]), L.hx(r[2]), L.hx(r[3]), L.hx(r[1]) / (L.hx(r[0]) * mul + L.hx(r[1])),
                         (L.hx(r[1]) - L.hx(r[0]) * mul) / 2))
        hist, fin = rows[:-1], rows[-1]
        # provide_allowed() reverts with empty data when debt exceeds the ratio cap (the subtraction underflows)
        out["per_pk"][n] = {"provide_side": sum(r[1] for r in hist),
                            "allowance_positive": sum((r[2] or 0) > 0 for r in hist),
                            "allowance_reverts": sum(r[2] is None for r in hist),
                            "provide_side_and_allowed": sum(r[1] and (r[2] or 0) > 0 for r in hist),
                            "holds_no_crvusd": sum(r[3] == 0 for r in hist)}
        out["final"][n] = {"provide_side": fin[1], "provide_allowed": (fin[2] or 0) / E18, "crvusd_held": fin[3] / E18,
                           "crvusd_share_of_pool": fin[4],
                           "crvusd_to_remove_to_reach_provide_side": max(0, fin[5]) / E18}
    return out


def withdraw_event_states(d):
    """State at the block before every Withdraw event (condition 3 in PREREG_R2_ADDENDUM.md)."""
    if not d["extra"]:
        return {"note": "r2_extra.json missing"}
    import statistics
    ts_of = {(n, e["block"]): e["ts"] for n in L.NAMES for e in d["events"][n]}
    groups = collections.defaultdict(list)
    for x in d["extra"]["events"]:
        if x["type"] != "Withdraw" or (x["pk"], x["block"]) not in ts_of:
            continue
        k = L.NAMES.index(x["pk"])
        mul = 10 ** (18 - d["pks"][k]["coin_decimals"][0])
        r = x["reads"]
        rec = {"price": L.hx(r[0]) / E18, "provide_side": L.hx(r[1]) * mul > L.hx(r[2]),
               "crv_share": L.hx(r[2]) / (L.hx(r[1]) * mul + L.hx(r[2])), "allowed": L.hx(r[5]) > 0}
        groups["all_pegkeepers"].append(rec)
        if x["pk"] == "USDT" and ts_of[(x["pk"], x["block"])] >= L.OCT13:
            groups["usdt_13oct_to_zero"].append(rec)
    out = {}
    for g, recs in groups.items():
        sh = [r["crv_share"] for r in recs]
        out[g] = {"n": len(recs), "provide_side": sum(r["provide_side"] for r in recs),
                  "withdraw_allowed_zero": sum(not r["allowed"] for r in recs),
                  "price_ge1": sum(r["price"] >= 1 for r in recs),
                  "crvusd_share_min": min(sh), "crvusd_share_median": statistics.median(sh), "crvusd_share_max": max(sh),
                  "price_min": min(r["price"] for r in recs), "price_max": max(r["price"] for r in recs)}
    return out


def threshold_evidence(d):
    """Pool share of crvUSD and pool price of crvUSD (get_p) at withdraw-side samples, by simulated update() outcome,
    for the USDT PegKeeper. The 53% boundary is read from here. It is observed, not derived from the contract."""
    import statistics
    from r2_checks import reads_of
    groups = collections.defaultdict(list)
    for key in d["tier2"]:
        b, k = map(int, key.split(":"))
        rd = reads_of(d, key)
        if k != USDT or rd["sim"] is None or pk_state(d, k, rd)["provide_side"]:
            continue
        outcome = L.sim_outcome(rd["sim"])
        mul = 10 ** (18 - d["pks"][k]["coin_decimals"][0])
        share = rd["bal_crv"] / (rd["bal_other"] * mul + rd["bal_crv"])
        groups[outcome].append((share, rd["get_p"] / E18))
    out = {}
    for o, v in groups.items():
        sh, pr = [x[0] for x in v], [x[1] for x in v]
        out[o] = {"n": len(v), "share_min": min(sh), "share_median": statistics.median(sh), "share_max": max(sh),
                  "pool_price_min": min(pr), "pool_price_median": statistics.median(pr), "pool_price_max": max(pr)}
    return out

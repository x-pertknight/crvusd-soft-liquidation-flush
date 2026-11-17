"""Release 2 review checks (addendum 2): how long a withdrawal opening lasts, how many independent stretches the
USDT evidence has, one USDT provide-side figure, whether worst_price_threshold bound, and the price at the event
block for events that saw the other side of 1 at the block before. Standard library only."""
import collections
import statistics

import r2_lib as L

E18 = 10 ** 18


def window_stats(d):
    """Per withdrawal: simulated update() outcome at every block from 20 before to 10 after the event block.
    An opening is a run of consecutive blocks whose simulated call does not revert 'peg unprofitable' (returns more
    than 0, or returns 0 because the 12-second action delay follows a withdrawal). Each withdrawal sets off the
    delay, so a run of 'ok' blocks broken by 'returned 0' blocks is one opening. A run that touches the first or
    last block read is censored: its true length is longer than shown."""
    w = d.get("windows")
    if not w:
        return {"note": "r2_windows.json missing"}
    ev = collections.defaultdict(dict)
    for key, v in w.items():
        eb, b = map(int, key.split(":"))
        ev[eb][b] = L.sim_outcome(v[2])
    rows = []
    for eb in sorted(ev):
        blocks = sorted(ev[eb])
        seq = [ev[eb][b] for b in blocks]
        runs, start = [], None
        for i, st in enumerate(seq + ["peg unprofitable"]):
            if st != "peg unprofitable" and start is None:
                start = i
            elif st == "peg unprofitable" and start is not None:
                runs.append({"blocks": i - start, "ok_blocks": sum(x == "ok" for x in seq[start:i]),
                             "censored_start": start == 0, "censored_end": i == len(seq)})
                start = None
        rows.append({"event_block": eb, "blocks_read": len(seq), "open_blocks": sum(r["blocks"] for r in runs),
                     "openings": runs, "outcomes": dict(collections.Counter(seq)), "at_block_before": ev[eb][eb - 1]})
    withdr = [r for r in rows if r["openings"]]
    cens = [r for r in withdr if any(o["censored_start"] or o["censored_end"] for o in r["openings"])]
    full = [r for r in withdr if any(o["censored_start"] and o["censored_end"] for o in r["openings"])]
    return {"events": rows, "n_events": len(rows), "events_with_opening_in_read": len(withdr),
            "events_opening_reaches_edge_of_read": len(cens), "events_opening_fills_all_blocks_read": len(full),
            "events_ok_at_block_before": sum(r["at_block_before"] == "ok" for r in rows),
            "events_closed_within_read": [r["event_block"] for r in withdr if r not in cens],
            "closed_opening_lengths_blocks": sorted(o["blocks"] for r in withdr if r not in cens for o in r["openings"])}


def drained_split(rows):
    """Of the readings labelled 'drained by the next sample', how did the simulation at that reading come out."""
    g = [r for r in rows if r["state"] == "g_drained_next_sample"]
    return {"n": len(g), "by_sim": dict(collections.Counter(r["simulated_update"] for r in g))}


def run_stats(rows):
    """USDT readings in time order. A stretch ends when the state changes or a hourly reading is missing between
    two readings. Reports stretches by pool side (balance test) and by labelled state."""
    u = [r for r in rows if r["pegkeeper"] == "USDT"]
    out = {"usdt_readings": len(u), "other_pegkeepers": len(rows) - len(u)}
    for name, keyf in (("by_pool_side", lambda r: r["provide_side"]), ("by_state", lambda r: r["state"])):
        runs, prev = [], None
        for r in u:
            b = int(r["block"])
            if prev and prev[0] + 300 <= b <= prev[0] + 300 + 96 and prev[1] == keyf(r):
                runs[-1][1] += 1
            else:
                runs.append([keyf(r), 1])
            prev = (b, keyf(r))
        provide = [n for s, n in runs if s in ("1", "a_provide_side")]
        out[name] = {"stretches": len(runs), "provide_side_stretches": len(provide),
                     "longest_provide_stretch": max(provide) if provide else None}
    return out


def provide_share_reconciled(rows):
    """One USDT provide-side figure for 13 October to zero: pool on the provide side by the balance test, over
    readings with debt above 1M and price below 1. The addendum's state share is lower because readings followed
    by a fall in debt are labelled 'drained' whatever the side."""
    dr = [r for r in rows if r["pegkeeper"] == "USDT" and int(r["ts"]) >= L.OCT13 and float(r["debt"]) > 1e6]
    side = sum(r["provide_side"] == "1" for r in dr)
    st = collections.Counter(r["state"] for r in dr)
    return {"readings": len(dr), "pool_on_provide_side": side, "share_pool_provide_side": side / len(dr),
            "state_a_count": st["a_provide_side"], "share_state_a": st["a_provide_side"] / len(dr),
            "drained_label_but_provide_side": side - st["a_provide_side"]}


def wpt_check(d):
    """worst_price_threshold: the Regulator refuses a deposit if the largest price_oracle among the other pools is
    below this pool's by more than the threshold (0.0003). Computed at every hourly reading with price at or above 1."""
    w = d.get("wpt")
    if not w:
        return {"note": "r2_wpt.json missing"}
    thr = L.hx(next(iter(d["daily"].values()))["worst_price_threshold()"])
    out = {"threshold": thr / E18, "per_pk": {}}
    for k, n in enumerate(L.NAMES):
        blocked, margin = 0, []
        for b, rd in w.items():
            p = []
            for j, r in enumerate(rd):
                v = L.hx(r)
                p.append(None if v is None else (10 ** 36 // v if d["pks"][j]["is_inverse"] else v))
            others = [x for j, x in enumerate(p) if j != k and x is not None]
            if p[k] is None or not others:
                continue
            gap = p[k] - max(others)  # positive when this pool is above the best other pool
            margin.append(gap)
            blocked += gap > thr
        out["per_pk"][n] = {"hours": len(margin), "blocked_by_worst_price": blocked,
                            "max_gap": max(margin) / E18 if margin else None}
    return out


def price_exceptions(d):
    """Provides at price below 1 and Withdraws at price above 1 at the block before: price at the event block."""
    px = d.get("price_exceptions")
    if not px:
        return {"note": "r2_price_exceptions.json missing"}
    res = {"Provide": [0, 0], "Withdraw": [0, 0]}  # [events, right side of 1 at the event block]
    for e in d["extra"]["events"]:
        pr = L.hx(e["reads"][0])
        if e["type"] == "Provide" and pr < E18 or e["type"] == "Withdraw" and pr > E18:
            at = L.hx(px[str(e["block"])])
            res[e["type"]][0] += 1
            res[e["type"]][1] += (at >= E18) if e["type"] == "Provide" else (at <= E18)
    return {k: {"events_on_other_side_before": v[0], "price_on_gate_side_at_event_block": v[1]} for k, v in res.items()}


def price_levels(d):
    """Share of hourly readings at or above 1 and at or above 0.9999, by month: one 78-day stretch that trended down."""
    g = d["grid"]
    by = collections.defaultdict(lambda: [0, 0, 0])
    for r in g:
        m = L.iso(r["ts"])[:7]
        by[m][0] += 1
        by[m][1] += r["price_wei"] >= E18
        by[m][2] += r["price_wei"] >= E18 - 10 ** 14
    n = len(g)
    return {"readings": n, "at_or_above_1": sum(v[1] for v in by.values()), "at_or_above_0_9999": sum(v[2] for v in by.values()),
            "share_at_or_above_1": sum(v[1] for v in by.values()) / n,
            "share_at_or_above_0_9999": sum(v[2] for v in by.values()) / n,
            "by_month": {m: {"readings": v[0], "at_or_above_1": v[1], "at_or_above_0_9999": v[2]} for m, v in sorted(by.items())}}


def sim_coverage(rows):
    """How many snapshots were simulated, by pool side (balance test)."""
    c = collections.Counter((r["provide_side"], r["simulated_update"] == "not simulated") for r in rows)
    return {"snapshots": len(rows), "simulated": c[("0", False)] + c[("1", False)],
            "deposit_branch_side": c[("1", False)] + c[("1", True)], "deposit_branch_simulated": c[("1", False)],
            "withdrawal_side": c[("0", False)] + c[("0", True)], "withdrawal_side_simulated": c[("0", False)],
            "not_simulated": c[("0", True)] + c[("1", True)],
            "withdrawal_side_returned_more_than_0": sum(r["simulated_update"] == "ok" and r["provide_side"] == "0" for r in rows)}


def usdt_period_splits(rows, first_withdraw_ts):
    """USDT snapshots with debt above 1M, split by state for 13 to 29 October and for 13 October up to the first
    withdrawal of the drain (the part of the flat stretch with the price below 1)."""
    u = [r for r in rows if r["pegkeeper"] == "USDT" and float(r["debt"]) > 1e6 and int(r["ts"]) >= L.OCT13]

    def split(sel):
        c = collections.Counter(r["state"] for r in sel)
        n = len(sel)
        return {"snapshots": n, "pool_short_of_crvusd": c["a_provide_side"], "withdrawal_side_not_drained": c["bc_allowed_no_landing"],
                "debt_fell_within_hour": c["g_drained_next_sample"],
                "shares": {k: v / n for k, v in c.items()}}
    return {"13_oct_to_29_oct": split(u), "13_oct_to_first_withdrawal": split([r for r in u if int(r["ts"]) < first_withdraw_ts])}


def withdrawal_minimum_by_group(d):
    """Minimum crvUSD share of the pool at the block before a Withdraw: all PegKeepers and USDT only."""
    w = L.withdraw_event_states(d)
    return {g: {"n": v["n"], "crvusd_share_min": v["crvusd_share_min"]} for g, v in w.items()}


def deposits_without_adjacent_reading(d):
    """Provides with no hourly reading at or above 1 immediately before or after the event."""
    import bisect
    g = d["grid"]
    ts = [r["ts"] for r in g]
    ev = [e for n in L.NAMES for e in d["events"][n] if e["type"] == "Provide" and e["ts"] >= L.START_TS]
    miss = 0
    for e in ev:
        i = bisect.bisect_right(ts, e["ts"])
        near = [g[j]["price_wei"] for j in (i - 1, i) if 0 <= j < len(g)]
        miss += not any(p >= E18 for p in near)
    return {"provides": len(ev), "no_adjacent_hourly_reading_at_or_above_1": miss}


def flat_stretch(d, rows):
    """USDT hourly readings from the last deposit to the first withdrawal of the drain (the flat stretch): how many,
    how many had price at or above 1, and in how many the pool was short of crvUSD (balance test). Readings with the
    price below 1 come from the decomposition rows, readings at or above 1 from the rebuild reads."""
    ev = d["events"]["USDT"]
    start = max(e["ts"] for e in ev if e["type"] == "Provide")
    end = min(e["ts"] for e in ev if e["type"] == "Withdraw" and e["ts"] >= L.OCT13)
    win = [r for r in d["grid"] if start <= r["ts"] < end]
    short_lt1 = sum(1 for r in rows if r["pegkeeper"] == "USDT" and start <= int(r["ts"]) < end and r["provide_side"] == "1")
    lt1 = sum(1 for r in rows if r["pegkeeper"] == "USDT" and start <= int(r["ts"]) < end)
    ge1 = [r for r in win if r["price_wei"] >= E18]
    rb = d["rebuild"]
    usdt = L.NAMES.index("USDT")
    mul = 10 ** (18 - d["pks"][usdt]["coin_decimals"][0])
    short_ge1 = 0
    for r in ge1:
        x = rb["reads"][str(r["block"])]["USDT"]
        short_ge1 += L.hx(x[0]) * mul > L.hx(x[1])
    n = len(win)
    return {"readings": n, "price_at_or_above_1": len(ge1), "price_below_1_with_debt": lt1,
            "pool_short_of_crvusd": short_lt1 + short_ge1, "share_pool_short": (short_lt1 + short_ge1) / n,
            "start_ts": start, "end_ts": end}

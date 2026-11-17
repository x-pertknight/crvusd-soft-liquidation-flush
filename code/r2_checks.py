"""Release 2 mechanical checks and the failed-call count. Standard library only."""
import collections

import r2_lib as L


def run_checks(d, check):
    """Every check the script fails on. Returns a dict of counts for the results file."""
    out = {}
    grid = d["grid"]
    gaps = [grid[i + 1]["ts"] - grid[i]["ts"] for i in range(len(grid) - 1)]
    check("grid spacing is 3600 to 3700 s", min(gaps) >= 3600 and max(gaps) <= 3700, f"{min(gaps)} to {max(gaps)}")
    check("tier 1 has no failed reads", all(r["price_wei"] is not None and None not in r["debt_wei"] for r in grid))
    out["reconcile_samples"] = check_reconcile(d, check)
    out["event_sources"] = check_event_sources(d, check)
    check("Blockscout scans complete", all(v[1] for v in d["bs_status"].values()),
          str({k: v[0] for k, v in d["bs_status"].items()}))
    check("tier 2 covers every sample with debt above 1 crvUSD and price below 1", tier2_complete(d),
          f"{len(d['tier2'])} jobs")
    out["sim_consistency"] = check_sim(d, check)
    check("last grid debt equals the debt read at the discover block for every PegKeeper", last_debt_ok(d))
    return out


def tier2_jobs(d):
    jobs = []
    for r in d["grid"]:
        if r["price_wei"] >= L.E18:
            continue
        jobs += [(r["block"], k) for k in range(5) if r["debt_wei"][k] > L.E18]
    return jobs


def tier2_complete(d):
    return all(f"{b}:{k}" in d["tier2"] for b, k in tier2_jobs(d))


def check_reconcile(d, check):
    """Debt(b1) - debt(b0) must equal the exact sum of Provide minus Withdraw wei in (b0, b1], for every PegKeeper."""
    grid, bad, n = d["grid"], 0, 0
    for k, name in enumerate(L.NAMES):
        evs = d["events"][name]
        j = 0
        for i in range(len(grid) - 1):
            b0, b1 = grid[i]["block"], grid[i + 1]["block"]
            net = 0
            while j < len(evs) and evs[j]["block"] <= b1:
                if evs[j]["block"] > b0:
                    net += evs[j]["wei"] if evs[j]["type"] == "Provide" else -evs[j]["wei"]
                j += 1
            n += 1
            bad += net != grid[i + 1]["debt_wei"][k] - grid[i]["debt_wei"][k]
    check("PegKeeper debt reconciles from events to the wei between all consecutive samples", bad == 0,
          f"{bad} mismatches in {n} intervals")
    return n


def check_event_sources(d, check):
    """Blockscout events must equal the Curve API events (block, type, amount within 1e-6 relative)."""
    out, bad = {}, 0
    for name in L.NAMES:
        bs = {(e["block"], e["type"]): e["wei"] / L.E18 for e in d["events"][name] if e["ts"] >= L.START_TS}
        api = {(e["block_number"], e["action_type"]): e["amount"] for e in d["api_events"][name]
               if e["timestamp"] >= L.START_TS}
        miss = set(bs) ^ set(api)
        diff = [k for k in set(bs) & set(api) if abs(bs[k] - api[k]) > 1e-6 * max(1.0, bs[k])]
        bad += len(miss) + len(diff)
        out[name] = len(bs)
    check("Blockscout and Curve API list the same Provide and Withdraw events since 1 September", bad == 0,
          f"{bad} differences, counts {out}")
    return out


def killed_at(d, block):
    """Regulator is_killed from the latest daily read at or before the block (it never changed, see governance)."""
    best = None
    for b, v in sorted(d["daily"].items(), key=lambda t: int(t[0])):
        if int(b) <= block:
            best = L.hx(v["is_killed()"])
    return best if best is not None else 0


def reads_of(d, key):
    """Tier 2 record for 'block:pk' as ints (None for errors); sim is the simulated update() text or None."""
    r = d["tier2"][key]
    return {"bal_other": L.hx(r[0]), "bal_crv": L.hx(r[1]), "get_p": L.hx(r[2]), "p_oracle": L.hx(r[3]),
            "withdraw_allowed": L.hx(r[4]), "killed": killed_at(d, int(key.split(":")[0])), "sim": r[5]}


def check_sim(d, check):
    """A provide-side block must simulate to 'Regulator ban': it ties the balance test to the contract's own answer."""
    from r2_metrics import pk_state
    cnt = collections.Counter()
    for key in d["tier2"]:
        b, k = map(int, key.split(":"))
        rd = reads_of(d, key)
        side = "provide" if pk_state(d, k, rd)["provide_side"] else "withdraw"
        sim = rd["sim"]
        if sim is None:
            continue
        out = L.sim_outcome(sim)
        cnt[(side, out)] += 1
    wrong = cnt[("provide", "ok")] + cnt[("provide", "returned 0")] + cnt[("provide", "peg unprofitable")] + cnt[("provide", "other revert")]
    check("every provide-side block simulates update() as a 'Regulator ban' revert", wrong == 0,
          f"{wrong} exceptions; counts {dict(cnt)}")
    return {f"{a}:{b}": v for (a, b), v in cnt.items()}


def last_debt_ok(d):
    disc = d["discover"]["pegkeepers"]
    return all(L.hx(disc[n]["debt()"]) == d["grid"][-1]["debt_wei"][k] for k, n in enumerate(L.NAMES)) \
        or all(L.hx(disc[n]["debt()"]) == 0 for n in L.NAMES)


def failed_calls(d):
    """Direct transactions to each PegKeeper since 1 September, by method and status, with revert reasons."""
    out = {}
    ev_tx = {e["tx"] for n in L.NAMES for e in d["events"][n] if e["ts"] >= L.START_TS}
    out["events_with_tx_hash"] = sum(bool(e["tx"]) for n in L.NAMES for e in d["events"][n] if e["ts"] >= L.START_TS)
    for name in L.NAMES:
        txs = [t for t in d["bs_tx"][name] if L.iso_ts(t["timestamp"]) >= L.START_TS]
        reasons = collections.Counter()
        for t in txs:
            if t["status"] != "ok":
                raw = (t.get("revert_reason") or {}).get("raw", "") or ""
                reasons[bytes.fromhex(raw[10 + 128:]).rstrip(b"\x00").decode(errors="replace") if len(raw) > 138
                        else "no reason"] += 1
        out[name] = {"direct_txs": len(txs), "failed": sum(t["status"] != "ok" for t in txs),
                     "ok": sum(t["status"] == "ok" for t in txs), "reasons": dict(reasons)}
    out["events_via_direct_calls"] = len(ev_tx & {t["hash"] for n in L.NAMES for t in d["bs_tx"][n]})
    out["events_total"] = len(ev_tx)
    return out

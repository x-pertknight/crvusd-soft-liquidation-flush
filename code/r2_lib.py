"""Release 2 loading, checks and metrics. Used by recompute_r2.py. Standard library only.
Sources: code/raw/r2_hour_blocks.json (sample grid), r2_series/ (RPC reads), r2_blockscout/ (events with exact wei,
transactions), r2_api/ (Curve prices API), r2_extra.json, r2_discover.json, r2_final.json."""
import datetime as dt
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "code", "raw")
E18 = 10 ** 18
START_TS = 1788220800  # 2026-09-01 00:00 UTC
NAMES = ["USDC", "USDT", "pyUSD", "frxUSD", "GHO"]
OCT13 = int(dt.datetime(2026, 10, 13, tzinfo=dt.timezone.utc).timestamp())


def jload(*parts):
    p = os.path.join(RAW, *parts)
    return json.load(open(p)) if os.path.exists(p) else None


def hx(x):
    """Hex answer to int, or None for an error string."""
    return int(x, 16) if isinstance(x, str) and x.startswith("0x") and len(x) > 2 else None


def iso(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def iso_ts(s):
    return int(dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())


def revert_reason(s):
    """Plain text reason from an 'ERR {...}' answer of a reverted eth_call."""
    if not isinstance(s, str) or not s.startswith("ERR"):
        return None
    for key in ("Regulator ban", "peg unprofitable"):
        if key in s:
            return key
    return "other revert"


def sim_outcome(s):
    """Label of a simulated update(): a revert reason, 'ok' only if it returned more than 0, 'returned 0' if it did
    nothing (for example an unmet action delay), 'other' if undecodable."""
    r = revert_reason(s)
    if r:
        return r
    v = hx(s)
    if v is None:
        return "other"
    return "ok" if v > 0 else "returned 0"


# ---------------------------------------------------------------- loading
def load_events():
    """Provide and Withdraw events per PegKeeper from Blockscout logs (exact wei), sorted by block."""
    out = {}
    for n in NAMES:
        evs = []
        for x in jload("r2_blockscout", f"{n}_logs.json")["items"]:
            call = (x.get("decoded") or {}).get("method_call", "")
            kind = call.split("(")[0]
            if kind in ("Provide", "Withdraw") and iso_ts(x["block_timestamp"]) >= START_TS - 7 * 86400:
                evs.append({"block": x["block_number"], "ts": iso_ts(x["block_timestamp"]), "type": kind,
                            "wei": int(x["decoded"]["parameters"][0]["value"]), "tx": x["transaction_hash"],
                            "idx": x["index"]})
        out[n] = sorted(evs, key=lambda e: (e["block"], e["idx"]))
    return out


def load_api_events():
    out = {}
    for n in NAMES:
        ev = jload("r2_api", f"events_{n}.json")["events"]
        out[n] = [e for e in ev if e["action_type"] in ("Provide", "Withdraw")]
    return out


def load_grid():
    g = jload("r2_hour_blocks.json")
    t1 = jload("r2_series", "tier1.json")
    rows = []
    for ts, b, _ in g["hours"]:
        r = t1[str(b)]
        wei = [hx(x) for x in r[:5]]
        rows.append({"ts": ts, "block": b, "debt_wei": wei, "debt": [w / E18 for w in wei],
                     "price": hx(r[5]) / E18, "price_wei": hx(r[5])})
    return rows


def load_all():
    d = {"grid": load_grid(), "events": load_events(), "api_events": load_api_events(),
         "tier2": jload("r2_series", "tier2.json") or {}, "daily": jload("r2_series", "daily.json"),
         "extra": jload("r2_extra.json"), "discover": jload("r2_discover.json"),
         "final": jload("r2_final.json"), "rebuild": jload("r2_rebuild.json"), "windows": jload("r2_windows.json"),
         "wpt": jload("r2_wpt.json"), "price_exceptions": jload("r2_price_exceptions.json"), "contracts": jload("..", "contracts.json"),
         "bs_status": jload("r2_blockscout", "status.json"),
         "bs_reg": jload("r2_blockscout", "Regulator_logs.json")["items"],
         "bs_agg": jload("r2_blockscout", "Aggregator_logs.json")["items"],
         "bs_tx": {n: jload("r2_blockscout", f"{n}_transactions.json")["items"] for n in NAMES},
         "api_price": jload("r2_api", "usd_price.json")}
    d["pks"] = d["contracts"]["pegkeepers"]
    d["last_block"] = d["grid"][-1]["block"]
    fill_tx_hashes(d)
    for n in NAMES:  # events after the last grid block are outside the analysis window
        d["events"][n] = [e for e in d["events"][n] if e["block"] <= d["last_block"]]
        d["api_events"][n] = [e for e in d["api_events"][n] if e["block_number"] <= d["last_block"]]
    return d


def fill_tx_hashes(d):
    """Blockscout's log list has no transaction hash. The Curve API has it, keyed here by block, type and amount."""
    for n in NAMES:
        by = {(e["block_number"], e["action_type"], round(e["amount"], 4)): e["transaction_hash"] for e in d["api_events"][n]}
        for e in d["events"][n]:
            e["tx"] = by.get((e["block"], e["type"], round(e["wei"] / E18, 4)), "")


# ---------------------------------------------------------------- reconstruction
def debt_path(d, k):
    """Exact debt in wei after every event of PegKeeper k, starting from the RPC read at the first grid block."""
    g0 = d["grid"][0]
    debt = g0["debt_wei"][k]
    path = [(g0["block"], g0["ts"], debt, None)]
    for e in d["events"][NAMES[k]]:
        if e["block"] <= g0["block"]:
            continue
        debt += e["wei"] if e["type"] == "Provide" else -e["wei"]
        path.append((e["block"], e["ts"], debt, e))
    return path


def debt_at(path, ts):
    """Debt in wei at a time, from the event path."""
    cur = path[0][2]
    for _, t, debt, _ in path:
        if t > ts:
            break
        cur = debt
    return cur


from r2_checks import run_checks, failed_calls  # noqa: E402,F401
from r2_metrics import (series_metrics, event_metrics, decomposition, governance,  # noqa: E402,F401
                        latest_state, write_series_csv, score_predictions, check_sums, fallback_kill, rebuild, withdraw_event_states, threshold_evidence)

from r2_review import (window_stats, drained_split, run_stats, provide_share_reconciled,  # noqa: E402,F401
                       wpt_check, price_exceptions, price_levels, sim_coverage, usdt_period_splits, withdrawal_minimum_by_group,
                       deposits_without_adjacent_reading, flat_stretch)

"""Release 2 recompute. Standard library only. Reads the raw files in code/raw/ (r2_*), checks them, computes every
release 2 number, scores PREDICTIONS_R2.md and writes data/r2_*.  Exits non-zero if any check fails.
Run:  python3 -I code/recompute_r2.py"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r2_lib as L  # noqa: E402

ROOT = L.ROOT
DATA = os.path.join(ROOT, "data")
FAILS = []


def check(name, ok, detail=""):
    """Record a mechanical check. Any failure makes the script exit non-zero."""
    print(("PASS " if ok else "FAIL ") + name + (" | " + detail if detail else ""))
    if not ok:
        FAILS.append(name)


def write_csv(name, header, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    os.makedirs(DATA, exist_ok=True)
    d = L.load_all()
    res = {}
    res["checks"] = L.run_checks(d, check)
    res["series"] = L.series_metrics(d)
    res["events"] = L.event_metrics(d, res["series"])
    res["decomposition"] = L.decomposition(d, write_csv)
    res["governance"] = L.governance(d)
    res["fallback_kill"] = L.fallback_kill(d, res["series"])
    res["latest"] = L.latest_state(d)
    res["rebuild"] = L.rebuild(d)
    res["withdraw_event_states"] = L.withdraw_event_states(d)
    res["threshold_evidence"] = L.threshold_evidence(d)
    res["failed_calls"] = L.failed_calls(d)
    rows = list(csv.DictReader(open(os.path.join(DATA, "r2_decomposition.csv"))))
    res["review"] = {"windows": L.window_stats(d), "drained_by_sim": L.drained_split(rows), "stretches": L.run_stats(rows),
                     "usdt_provide_share": L.provide_share_reconciled(rows), "worst_price_threshold": L.wpt_check(d),
                     "price_exceptions": L.price_exceptions(d), "price_levels": L.price_levels(d),
                     "sim_coverage": L.sim_coverage(rows),
                     "usdt_period_splits": L.usdt_period_splits(rows, min(e["ts"] for e in d["events"]["USDT"] if e["type"] == "Withdraw" and e["ts"] >= L.OCT13)),
                     "withdrawal_minimum_by_group": L.withdrawal_minimum_by_group(d),
                     "deposits_adjacent_reading": L.deposits_without_adjacent_reading(d),
                     "flat_stretch": L.flat_stretch(d, rows)}
    L.write_series_csv(d, write_csv)
    scored = L.score_predictions(d, res)
    write_csv("r2_predictions_scored.csv", ["id", "result", "measured"], scored)
    res["predictions"] = {r[0]: {"result": r[1], "measured": r[2]} for r in scored}
    res["checks_failed"] = FAILS
    with open(os.path.join(DATA, "r2_results.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
        f.write("\n")
    sums = []
    for n in sorted(os.listdir(DATA)):
        if n.startswith("r2_"):
            sums.append(hashlib.sha256(open(os.path.join(DATA, n), "rb").read()).hexdigest() + "  " + n)
    check("r2 outputs match data/R2_SHA256SUMS", L.check_sums(sums), "")
    print("failed checks:", FAILS or "none")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())

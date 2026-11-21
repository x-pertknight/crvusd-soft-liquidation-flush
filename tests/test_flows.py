"""Tests for the release 1 flow accounting (code/flows.py) and for published outputs in data/.
Standard library only. Run: python3 -I -m unittest discover -s tests"""
import csv
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "code"))
from flows import agg_class, build_rows, flows_match_balance, yb  # noqa: E402

DATA = os.path.join(ROOT, "data")


def row(tx, cls, net_in, pool="USDC"):
    return {"tx": tx, "class": cls, "net_in": net_in, "pool": pool}


SYNTH = [row("a", "yb_curve_pool_leg", 100.0), row("a", "yb_curve_pool_leg", -30.0, "USDT"),
         row("b", "yb_levamm_leg", -20.0), row("c", "yb_curve_pool_leg", 50.0, "pyUSD"),
         row("d", "other", 70.0), row("d", "other", -10.0, "USDT"), row("a", "other", 5.0, "GHO")]


class SyntheticAccounting(unittest.TestCase):
    def test_net_is_sold_minus_bought(self):
        for c, o in agg_class(SYNTH).items():
            self.assertAlmostEqual(o["net_in"], o["sold"] - o["bought"], msg=c)

    def test_tx_counted_once_per_class(self):
        out = agg_class(SYNTH)
        self.assertEqual(out["yb_curve_pool_leg"]["n_tx"], 2)  # a (two pools) and c
        self.assertEqual(out["other"]["n_tx"], 2)  # d (two pools) and a, counted in its own class too
        self.assertEqual(out["pegkeeper"]["n_tx"], 0)

    def test_v0_is_sum_of_yield_basis_classes(self):
        out = agg_class(SYNTH)
        self.assertAlmostEqual(yb(SYNTH), out["yb_curve_pool_leg"]["net_in"] + out["yb_levamm_leg"]["net_in"])
        self.assertAlmostEqual(yb(SYNTH), 100.0)

    def test_v2_counts_only_positive_legs(self):
        self.assertAlmostEqual(yb(SYNTH, gross=True), 150.0)
        self.assertGreaterEqual(yb(SYNTH, gross=True), yb(SYNTH))

    def test_v5_is_part_of_v0(self):
        v5 = yb(SYNTH, classes=("yb_curve_pool_leg",))
        levamm = yb(SYNTH, classes=("yb_levamm_leg",))
        self.assertAlmostEqual(v5 + levamm, yb(SYNTH))
        self.assertAlmostEqual(v5, 120.0)

    def test_pools_only_filter(self):
        self.assertAlmostEqual(yb(SYNTH, pools_only=("USDC", "USDT")), 50.0)

    def test_build_rows_classes(self):
        net = {"t1": {"p1": 10.0, "p2": -4.0}, "t2": {"p1": 3.0}, "t3": {"p2": -1.0}}
        pk_leg = {"t4": {"p1": 2.0, "p2": 0.0}}
        rules = {"t1": ["yb_levamm_leg", "yb_curve_pool_leg"], "t2": [], "t3": []}
        rows, multi = build_rows(net, pk_leg, {"t1": 1, "t2": 2, "t3": 3, "t4": 4},
                                 lambda h: rules[h], lambda h, p: "swap" if h == "t3" else "liquidity",
                                 {"t1": {"from": "0xAB", "to": None}}, {1: 11, 2: 12, 3: 13, 4: 14},
                                 {"p1": "USDC", "p2": "USDT"})
        cls = [(r["tx"], r["pool"], r["class"]) for r in rows]
        self.assertEqual(cls, [("t1", "USDC", "yb_levamm_leg"), ("t1", "USDT", "yb_levamm_leg"),
                               ("t2", "USDC", "liquidity_non_pk"), ("t3", "USDT", "other"),
                               ("t4", "USDC", "pegkeeper")])  # zero PegKeeper leg dropped
        self.assertEqual(rows[0]["from"], "0xab")
        self.assertEqual(rows[0]["to"], "")
        self.assertEqual(dict(multi), {"yb_levamm_leg+yb_curve_pool_leg": [1, 6.0]})
        self.assertAlmostEqual(sum(r["net_in"] for r in rows), 10.0)

    def test_balance_tolerance(self):
        self.assertTrue(flows_match_balance(1000.0, 0.0))
        self.assertFalse(flows_match_balance(1000.1, 0.0))
        self.assertTrue(flows_match_balance(1_002_000.0, 1_000_000.0))
        self.assertFalse(flows_match_balance(1_002_100.0, 1_000_000.0))


def read_csv(name):
    with open(os.path.join(DATA, name)) as f:
        return list(csv.DictReader(f))


class PublishedOutputs(unittest.TestCase):
    """Checks against the files recompute.py writes. Their hashes are pinned in data/SHA256SUMS."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DATA, "results.json")) as f:
            cls.res = json.load(f)
        cls.rows = [{"tx": i, "class": r["class"], "pool": r["pool"], "net_in": float(r["net_in_crvusd"]),
                     "utc": r["timestamp_utc"]} for i, r in enumerate(read_csv("flows_by_tx.csv"))]
        cls.main = [r for r in cls.rows if "2026-11-08 20:00:00" <= r["utc"] < "2026-11-09 04:00:00"]

    def test_flows_match_pool_balance(self):
        ck = self.res["checks"]
        self.assertTrue(flows_match_balance(ck["sum_flows"], ck["pool_balance_change"]))
        # the CSV rounds each row to 0.01, so allow 0.005 per row
        self.assertAlmostEqual(sum(r["net_in"] for r in self.rows), ck["sum_flows"], delta=0.005 * len(self.rows))

    def test_variants_recompute_from_csv(self):
        v = self.res["q3"]["variants"]
        tol = 0.005 * len(self.main)
        self.assertAlmostEqual(yb(self.main), v["V0_main_net_same_tx"], delta=tol)
        self.assertAlmostEqual(yb(self.main, gross=True), v["V2_gross_sells"], delta=tol)
        self.assertAlmostEqual(yb(self.main, pools_only=("USDC", "USDT")), v["V4_usdc_usdt_only"], delta=tol)
        self.assertAlmostEqual(yb(self.main, classes=("yb_curve_pool_leg",)), v["V5_curve_pool_leg_only"], delta=tol)
        self.assertAlmostEqual(v["V3_with_cross_tx"], v["V0_main_net_same_tx"] + self.res["q3"]["s1_moved_net_in"])

    def test_variants_match_readme_table(self):
        v = self.res["q3"]["variants"]
        got = {k: round(v[k] / 1e6, 2) for k in ("V0_main_net_same_tx", "V2_gross_sells", "V3_with_cross_tx",
                                                 "V4_usdc_usdt_only", "V5_curve_pool_leg_only")}
        self.assertEqual(got, {"V0_main_net_same_tx": 3.85, "V2_gross_sells": 4.59, "V3_with_cross_tx": 2.69,
                               "V4_usdc_usdt_only": 2.94, "V5_curve_pool_leg_only": 3.90})

    def test_pegkeeper_debt_reconciles(self):
        rows = read_csv("pegkeeper_debt.csv")
        self.assertEqual(sorted(r["pegkeeper"] for r in rows), ["GHO", "USDC", "USDT", "frxUSD", "pyUSD"])
        for r in rows:
            d = float(r["debt_start"]) + float(r["provided"]) - float(r["withdrawn"]) - float(r["debt_end"])
            self.assertLessEqual(abs(d), 1.0, r["pegkeeper"])

    def test_last_usdt_withdraw(self):
        w = [r for r in read_csv("r2_events.csv") if r["pegkeeper"] == "USDT" and r["type"] == "Withdraw"]
        last = max(w, key=lambda r: int(r["block"]))
        self.assertEqual((int(last["block"]), int(last["ts"])), (26301792, 1793317775))
        self.assertEqual(last["utc"], "2026-10-29 23:49:35")


if __name__ == "__main__":
    unittest.main()

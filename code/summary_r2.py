"""One summary image for a phone feed: charts/summary.png, 1080 x 1350 px, built from data/r2_series.csv and
data/r2_results.json. Layout in pixels, same design as the other studies' summary images.
Needs matplotlib. Writes out/charts/ unless UPDATE_CHARTS=1 (then charts/). Run: python3 code/summary_r2.py"""
import csv
import datetime as dt
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "charts" if os.environ.get("UPDATE_CHARTS") == "1" else os.path.join("out", "charts"))
os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1350
INK, GREY, SLATE, ORANGE, BLUE = "#1c1c1c", "#5a6470", "#4b5563", "#d9822b", "#2a6fb0"
NAMES = ["USDC", "USDT", "pyUSD", "frxUSD", "GHO"]
plt.rcParams["font.family"] = ["Helvetica", "Arial", "DejaVu Sans"]
PT = 72 / 100  # points per pixel at 100 dpi


def load():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "r2_series.csv"))))
    t = [dt.datetime.strptime(r["utc"], "%Y-%m-%d %H:%M:%S") for r in rows]
    total = [sum(float(r[f"debt_{n}"]) for n in NAMES) / 1e6 for r in rows]
    res = json.load(open(os.path.join(ROOT, "data", "r2_results.json")))
    return t, total, res


def figures(res):
    """The big figures, from the results, rounded as in post.md."""
    fin = res["rebuild"]["final"]
    sh = [v["crvusd_share_of_pool"] for v in fin.values()]
    flat = res["review"]["flat_stretch"]["share_pool_short"]
    return {"short": f"{round(flat * 10)} in 10", "ge1": f"{res['review']['price_levels']['share_at_or_above_1']:.0%}",
            "pool": f"{min(sh) * 100:.0f}–{max(sh):.0%}"}


class Canvas:
    """Text placed by pixel position (top-left origin); every text is checked to stay inside the margins."""

    def __init__(self):
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.texts = []

    def text(self, x, y, s, px, color=INK, bold=False, ha="left"):
        t = self.ax.text(x, y, s, fontsize=px * PT, color=color, fontweight="bold" if bold else "normal",
                         ha=ha, va="top", linespacing=1.18)
        self.texts.append(t)
        return t

    def check(self):
        self.fig.canvas.draw()
        r = self.fig.canvas.get_renderer()
        for t in self.texts:
            b = t.get_window_extent(r)
            assert b.x0 >= 40 and b.x1 <= W - 40, f"text out of margin: {t.get_text()!r} {b.x0:.0f}-{b.x1:.0f}"


def main():
    t, total, res = load()
    fg = figures(res)
    c = Canvas()
    c.text(60, 52, "With no debt, crvUSD's\nPegKeepers can't act below 1", 62, bold=True)
    c.text(60, 218, "Hourly readings, 1 September to 16 November 2026", 27, GREY)
    c.text(60, 296, "Nothing of theirs in the pools from 29 October (UTC)", 37, bold=True)
    c.text(60, 352, "Debt in the pools, million crvUSD", 24, GREY)
    h = 190
    a = c.fig.add_axes([60 / W, 1 - (410 + h) / H, 960 / W, h / H])
    a.fill_between(t, total, color=ORANGE, step="post", lw=0)
    a.set_xlim(t[0], t[-1])
    a.set_ylim(0, 50)
    a.axis("off")
    a.set_zorder(1)
    c.ax.plot([60, 1020], [600, 600], color=GREY, lw=1.5)
    span = (t[-1] - t[0]).total_seconds()
    for d, lab in [(dt.datetime(2026, 9, 1), "1 Sep"), (dt.datetime(2026, 10, 1), "1 Oct"), (dt.datetime(2026, 11, 1), "1 Nov")]:
        x = 60 + 960 * (d - t[0]).total_seconds() / span
        c.text(max(x, 62), 610, lab, 24, GREY)
    lab = c.text(832, 440, "zero from\n29 Oct (UTC)", 32, INK, bold=True)
    lab.set_zorder(10)
    c.ax.annotate("", xy=(60 + 960 * (dt.datetime(2026, 10, 30) - t[0]).total_seconds() / span + 8, 586), xytext=(846, 528),
                  arrowprops={"arrowstyle": "->", "color": INK, "lw": 2.5}, zorder=10)
    c.text(60, 684, "Why the largest one sat still", 43, bold=True)
    cols2 = [(60, "12 days", SLATE, "its debt of about 34M\nstayed flat"),
             (560, fg["short"], BLUE, "hourly readings in those 12 days\nhad its pool short of crvUSD")]
    for x, big, col, cap in cols2:
        c.text(x, 745, big, 96, col, bold=True)
        c.text(x, 858, cap, 27)
    c.text(60, 984, "What it would take", 43, bold=True)
    cols3 = [(60, fg["ge1"], ORANGE, "of hourly readings had the\nprice at or above 1"),
             (560, fg["pool"], ORANGE, "of each pool is crvUSD\nnow")]
    for x, big, col, cap in cols3:
        c.text(x, 1045, big, 96, col, bold=True)
        c.text(x, 1158, cap, 27)
    c.ax.plot([60, 1020], [1268, 1268], color="#d9d9d9", lw=1.5)
    c.text(60, 1292, "Marco Amendola · data and code: github.com/x-pertknight/crvusd-soft-liquidation-flush", 23, GREY)
    c.check()
    c.fig.savefig(os.path.join(OUT, "summary.png"), dpi=100, facecolor="white")
    print("wrote", os.path.join(OUT, "summary.png"), fg)


if __name__ == "__main__":
    main()

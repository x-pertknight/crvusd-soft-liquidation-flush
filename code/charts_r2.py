"""Release 2 charts from data/r2_*.csv. Needs matplotlib. Writes out/charts/ so a rerun never overwrites the
published charts/. UPDATE_CHARTS=1 writes charts/ instead. Run: python3 code/charts_r2.py"""
import csv
import datetime as dt
import os

import matplotlib
import matplotlib.dates as mdates
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "charts" if os.environ.get("UPDATE_CHARTS") == "1" else os.path.join("out", "charts"))
os.makedirs(OUT, exist_ok=True)
NAMES = ["USDC", "USDT", "pyUSD", "frxUSD", "GHO"]
COL = {"USDC": "#2a6fb0", "USDT": "#d9822b", "pyUSD": "#6b8e23", "frxUSD": "#8a5aa8", "GHO": "#8c8c8c"}
INK, GRID = "#222222", "#dddddd"
plt.rcParams.update({"font.size": 14, "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK, "ytick.color": INK, "svg.hashsalt": "r2", "axes.spines.top": False,
                     "axes.spines.right": False})


def rows(name):
    return list(csv.DictReader(open(os.path.join(ROOT, "data", name))))


def when(s):
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def save(fig, name):
    for ext in ("png", "svg"):
        kw = {"dpi": 150} if ext == "png" else {"metadata": {"Date": None}}
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), **kw)
    plt.close(fig)


def short_dates(ax, days):
    """Short date labels ('29 Oct') every `days` days so they do not collide at phone width."""
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=days))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-d %b"))


def chart_debt_price():
    s = rows("r2_series.csv")
    t = [when(r["utc"]) for r in s]
    fig, (a, b) = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    a.stackplot(t, *[[float(r[f"debt_{n}"]) / 1e6 for r in s] for n in NAMES], labels=NAMES,
                colors=[COL[n] for n in NAMES])
    a.set_ylabel("PegKeeper debt, million crvUSD")
    a.legend(loc="upper right", ncol=3, frameon=False, fontsize=12)
    a.set_title("PegKeeper debt has been zero since\n23:49 UTC on 29 October", loc="left", fontsize=15)
    p = [float(r["agg_price"]) for r in s]
    b.plot(t, p, color=INK, lw=1)
    b.axhline(1.0, color="#b03030", lw=1)
    b.fill_between(t, p, 1.0, where=[x >= 1 for x in p], color="#b03030", alpha=0.35, step="mid")
    b.set_ylabel("crvUSD price (USD)")
    b.text(t[2], 1.0004, "Deposits possible only at or above 1", color="#b03030", fontsize=12)
    b.set_ylim(0.993, 1.002)
    short_dates(b, 14)
    for ax in (a, b):
        ax.grid(axis="y", color=GRID)
    fig.tight_layout()
    save(fig, "R2_C1_debt_and_price")


def chart_usdt_drain():
    s = [r for r in rows("r2_series.csv") if "2026-10-08" <= r["utc"][:10] <= "2026-11-01"]
    ev = [e for e in rows("r2_events.csv") if e["pegkeeper"] == "USDT" and "2026-10-08" <= e["utc"][:10] <= "2026-11-01"]
    t = [when(r["utc"]) for r in s]
    fig, (a, b) = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    a.step(t, [float(r["debt_USDT"]) / 1e6 for r in s], where="post", color=COL["USDT"], lw=2)
    a.set_ylabel("USDT debt, million crvUSD", fontsize=13)
    a.set_title("USDT PegKeeper debt sat still for 12 days,\nthen fell to zero in six", loc="left", fontsize=15)
    for e in ev:
        a.axvline(when(e["utc"]), color="#555555", lw=0.5, alpha=0.5, ymax=0.08 if e["type"] == "Withdraw" else 0.0)
    b.plot(t, [float(r["agg_price"]) for r in s], color=INK, lw=1)
    b.axhline(1.0, color="#b03030", lw=1)
    b.set_ylabel("crvUSD price (USD)")
    short_dates(b, 5)
    a.text(0.02, 0.1, "Grey ticks: withdrawals", transform=a.transAxes, fontsize=12, color="#555555")
    for ax in (a, b):
        ax.grid(axis="y", color=GRID)
    fig.tight_layout()
    save(fig, "R2_C2_usdt_drain")


def chart_decomposition():
    d = rows("r2_decomposition.csv")
    groups = {"USDT, 13 to 29 October": [r for r in d if r["pegkeeper"] == "USDT" and r["ts"] >= "1791849600"
                                          and float(r["debt"]) > 1e6],
              "All five, 1 Sep to 16 Nov": d}
    parts = [("pool short of crvUSD: deposit not allowed", lambda r: r["state"] == "a_provide_side", "#2a6fb0"),
             ("withdrawal not profitable",
              lambda r: r["state"] == "bc_allowed_no_landing" and r["simulated_update"] == "peg unprofitable", "#d9822b"),
             ("withdrawal possible",
              lambda r: r["state"] == "bc_allowed_no_landing" and r["simulated_update"] == "ok", "#6b8e23"),
             ("debt fell within the hour", lambda r: r["state"] == "g_drained_next_sample", "#8c8c8c")]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for y, (label, g) in enumerate(groups.items()):
        left = 0
        for name, fn, color in parts:
            share = sum(1 for r in g if fn(r)) / len(g)
            ax.barh(y, share, left=left, color=color, label=name if y == 0 else None)
            if share > 0.04:
                ax.text(left + share / 2, y, f"{share:.0%}", ha="center", va="center", color="white", fontsize=15)
            left += share
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(list(groups))
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of hourly snapshots with debt outstanding and price below 1")
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=2, frameon=False, fontsize=12)
    ax.set_title("In most hourly snapshots the pool was short of crvUSD\nor a withdrawal would not have paid", loc="left", fontsize=15)
    fig.tight_layout()
    save(fig, "R2_C3_decomposition")


if __name__ == "__main__":
    chart_debt_price()
    chart_usdt_drain()
    chart_decomposition()
    print("charts written to", OUT)

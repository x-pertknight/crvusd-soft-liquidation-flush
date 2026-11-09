"""Publication charts. Reads only data/ outputs written by recompute.py and the raw context file.
Pinned dependency: matplotlib==3.9.2 (see requirements.txt)."""
import csv
import json
import os
import time
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

REPO_URL = "github.com/x-pertknight/crvusd-soft-liquidation-flush"
INK = "#1A1A1A"
MUTED = "#6B6B6B"
GRID = "#E4E4E4"
BG = "#FFFFFF"
BUY = "#0072B2"     # Okabe-Ito blue: crvUSD bought out of peg pools
SELL = "#D55E00"    # Okabe-Ito vermillion: crvUSD sold into peg pools
NEUTRAL = "#9A9A9A"
POOL_COLORS = {"USDC": "#56B4E9", "USDT": "#009E73", "pyUSD": "#CC79A7", "frxUSD": "#E69F00", "GHO": "#7F7F7F"}


def setup():
    fam = "DejaVu Sans"
    for f in font_manager.findSystemFonts():
        if os.path.basename(f) in ("Inter-Regular.otf", "Inter-Regular.ttf"):
            font_manager.fontManager.addfont(f)
            for g in ("Inter-Medium.otf", "Inter-SemiBold.otf"):
                p = os.path.join(os.path.dirname(f), g)
                if os.path.exists(p):
                    font_manager.fontManager.addfont(p)
            fam = "Inter"
    plt.rcParams.update({
        "font.family": fam, "font.size": 13, "text.color": INK, "axes.labelcolor": MUTED,
        "axes.edgecolor": GRID, "axes.linewidth": 0.8, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": BG, "axes.facecolor": BG,
        "svg.fonttype": "none", "legend.frameon": False, "svg.hashsalt": "crvusd-flush",
    })
    return fam


def fig16x9():
    return plt.figure(figsize=(12, 6.75), dpi=200)


import textwrap  # noqa: E402


def header(fig, title, subtitle, width=118, top=0.955):
    tl = textwrap.wrap(title, 86)
    fig.text(0.04, top, "\n".join(tl), fontsize=19, fontweight="semibold", va="top", ha="left", linespacing=1.15)
    fig.text(0.04, top - 0.062 - 0.045 * (len(tl) - 1), "\n".join(textwrap.wrap(subtitle, width, break_on_hyphens=False)), fontsize=12.5,
             color=MUTED, va="top", ha="left", linespacing=1.35)


def source(fig, extra="", width=150):
    s = "Source: Ethereum mainnet logs and archive state via public RPC. Window 2026-11-08 20:00 to 2026-11-09 04:00 UTC."
    if extra:
        s += " " + extra
    lines = textwrap.wrap(s, width, break_on_hyphens=False) + ["Data and code: " + REPO_URL]
    fig.text(0.04, 0.02, "\n".join(lines), fontsize=9.5, color=MUTED, va="bottom", ha="left", linespacing=1.35)


def spread(vals, gap):
    """Return label y positions, in the same order, at least gap apart."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    last = None
    for i in order:
        y = vals[i] if last is None else max(vals[i], last + gap)
        out[i] = y
        last = y
    shift = (sum(out) - sum(vals)) / len(vals)
    return [y - shift for y in out]


def save(fig, root, name):
    out = os.path.join(root, "charts")
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, name + ".png"), dpi=200, facecolor=BG)
    fig.savefig(os.path.join(out, name + ".svg"), facecolor=BG, metadata={"Date": None})
    plt.close(fig)


def dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def timeaxis(ax):
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))


def read_csv(root, name):
    with open(os.path.join(root, "data", name)) as f:
        return list(csv.DictReader(f))


def fmt_m(x):
    return f"{x / 1e6:.2f}M"


# ---------------------------------------------------------------- C1
def c1(root, R):
    rows = read_csv(root, "prices_by_block.csv")
    t = [dt(r["timestamp_utc"]) for r in rows]
    pools = ["USDC", "USDT", "pyUSD", "frxUSD", "GHO"]
    fig = fig16x9()
    ax = fig.add_axes([0.08, 0.40, 0.76, 0.42])
    ax2 = fig.add_axes([0.08, 0.15, 0.76, 0.19], sharex=ax)
    W = [float(r["W"]) for r in rows]
    ends = [float(rows[-1][p]) for p in pools] + [W[-1]]
    labs = spread(ends, 0.00052)
    for i, p in enumerate(pools):
        y = [float(r[p]) for r in rows]
        ax.step(t, y, where="post", color=POOL_COLORS[p], lw=1.0, alpha=0.9)
        ax.annotate(p, (t[-1], y[-1]), xytext=(t[-1] + (t[-1] - t[0]) * 0.015, labs[i]), color=POOL_COLORS[p],
                    fontsize=10.5, va="center", ha="left", annotation_clip=False)
    ax.step(t, W, where="post", color=INK, lw=2.0)
    ax.annotate("TVL weighted", (t[-1], W[-1]), xytext=(t[-1] + (t[-1] - t[0]) * 0.015, labs[-1]), color=INK,
                fontsize=10.5, fontweight="semibold", va="center", ha="left", annotation_clip=False)
    for lvl in (0.997, 0.995):
        ax.axhline(lvl, color=MUTED, lw=0.8, ls=(0, (3, 3)))
        ax.text(dt("2026-11-08 21:05:00"), lvl - 0.00008, f"{lvl}", color=MUTED, fontsize=10, va="top", ha="left")
    lo = min(min(float(r[p]) for r in rows) for p in pools)
    hi = max(max(float(r[p]) for r in rows) for p in pools)
    ax.set_ylim(min(lo, 0.994) - 0.0008, max(hi, 1.0) + 0.0005)
    ax.set_ylabel("crvUSD price in paired coin")
    plt.setp(ax.get_xticklabels(), visible=False)
    eth = [float(r["eth_usd"]) for r in rows]
    ax2.step(t, eth, where="post", color=INK, lw=1.4)
    ax2.set_ylabel("ETH/USD")
    timeaxis(ax2)
    for a in (ax, ax2):
        a.axvspan(dt("2026-11-08 22:30:00"), dt("2026-11-08 23:30:00"), color="#F2F2F2", zorder=0, lw=0)
    ax.text(dt("2026-11-08 22:31:00"), ax.get_ylim()[1], "pre-registered flush hour", fontsize=9.5, color=MUTED, va="top")
    q = R["q1"]
    title = (f"crvUSD was already below peg before the ETH drop and fell to {q['W']['min']:.4f}"
             if q["W_pre"] < 0.999 else f"crvUSD fell to {q['W']['min']:.4f} during the ETH drop")
    sub = (f"Block level spot price in the five PegKeeper pools. Weighted price {q['W_pre']:.4f} at 20:00 UTC, "
           f"lowest {q['W']['min']:.4f} at {q['W']['min_utc'][11:16]} UTC, still {q['W']['end']:.4f} at 04:00. "
           f"Below 0.997 for {q['W']['sec_below_0997'] / 3600:.1f} of 8 hours. Lowest single pool print {q['min_any_pool']:.4f} ({q['min_any_pool_name']}).")
    header(fig, title, sub)
    source(fig, "Times in UTC. ETH/USD from Chainlink, which updates on deviation or heartbeat. Paired stablecoins valued at 1 USD.")
    save(fig, root, "C1_price_path")


# ---------------------------------------------------------------- C2
def c2(root, R):
    ctx = json.load(open(os.path.join(root, "code", "raw", "context_pegkeepers_30d.json")))
    C = json.load(open(os.path.join(root, "code", "contracts.json")))
    names = {p["pegkeeper"].lower(): p["name"] for p in C["pegkeepers"]}
    bts = {int(k): int(v, 16) for k, v in ctx["block_timestamps"].items()}
    fig = fig16x9()
    ax = fig.add_axes([0.07, 0.17, 0.80, 0.58])
    wstart = datetime.fromtimestamp(1794168000, timezone.utc)
    wend = datetime.fromtimestamp(1794196800, timezone.utc)
    ends = []
    for pk, ser in ctx["debt"].items():
        bs = sorted(int(b) for b in ser)
        x = [datetime.fromtimestamp(bts[b], timezone.utc) for b in bs] + [wend]
        y = [int(ser[str(b)], 16) / 1e6 / 1e18 for b in bs]
        y = y + [R["q2"]["pegkeepers"][names[pk.lower()]]["debt_end"] / 1e6]
        ax.step(x, y, where="post", color=POOL_COLORS[names[pk.lower()]], lw=1.8 if max(y) > 0 else 1.2)
        ends.append((names[pk.lower()], max(y)))
    nz = [n for n, m in ends if m > 0]
    zero = [n for n, m in ends if m == 0]
    ax.text(datetime.fromtimestamp(1794000000, timezone.utc), 0.8, ", ".join(zero) + "\nPegKeepers at zero throughout",
            fontsize=10.5, color=MUTED, va="bottom", ha="right")
    for n in nz:
        ax.text(datetime.fromtimestamp(bts[ctx["start_block"]], timezone.utc), max(m for nn, m in ends if nn == n) * 1.02,
                f"{n} PegKeeper", color=POOL_COLORS[n], fontsize=10.5, va="bottom", ha="left", fontweight="semibold")
    ax.axvspan(wstart, wend, color="#E9E9E9", lw=0, zorder=0)
    ax.set_ylabel("PegKeeper debt, million crvUSD")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b", tz=timezone.utc))
    ax.set_ylim(-0.5, max(m for _, m in ends) * 1.15 + 1)
    header(fig, "PegKeepers held no crvUSD in their pools when the flush started",
           "Debt of each PegKeeper, sampled every 1,800 blocks (about 6 hours) over the 30 days before the window. "
           "Only the USDT PegKeeper held debt in that period, and it reached zero by 30 October. In the study window "
           f"total debt was {R['q2']['total_debt_start']:,.0f} crvUSD and there were {R['q2']['n_events']} Provide or Withdraw events.",
           width=124)
    source(fig, "Archive eth_call of PegKeeper debt(). The 30 day history is context outside the pre-registered measures. "
                "The gray band at the right edge is the 8 hour study window.")
    save(fig, root, "C2_pegkeeper_debt")


# ---------------------------------------------------------------- C3
CLASS_LABEL = {"yb_curve_pool_leg": "Yield Basis, Curve pool leg", "yb_levamm_leg": "Yield Basis, LEVAMM leg",
               "llamma_arbitrage": "LLAMMA soft liquidation arbitrage", "hard_liquidation": "Hard liquidations",
               "borrower_action": "Borrowers (borrow, repay)", "liquidity_non_pk": "Liquidity providers",
               "other": "Other (aggregators, MEV, plain swaps)", "pegkeeper": "PegKeepers"}


def c3(root, R, square=False, band=True):
    rows = read_csv(root, "flows_15m.csv")
    t = [dt(r["bucket_start_utc"]) for r in rows]
    main = R["q3"]["main"]
    panels = [("Curve pools, Yield Basis as LP", ["yb_curve_pool_leg"]),
              ("Yield Basis LEVAMM leg", ["yb_levamm_leg"]),
              ("Liquidity deposits and withdrawals", ["liquidity_non_pk"]),
              ("Other swaps", ["other"]),
              ("LLAMMA, liquidations, borrowers", ["llamma_arbitrage", "hard_liquidation", "borrower_action"]),
              ("PegKeepers", ["pegkeeper"])]
    fig = plt.figure(figsize=(12, 12) if square else (12, 6.75), dpi=200)
    top, bottom = (0.745, 0.11) if square else (0.715, 0.15)
    h = (top - bottom) / len(panels)
    vals_all = {name: [-sum(float(r[c]) for c in cls) / 1e6 for r in rows] for name, cls in panels}
    m = max(abs(v) for vs in vals_all.values() for v in vs)
    step = 1 if m <= 3 else 2
    ymax = (int(m / step) + 1) * step
    width = 0.0104 * 0.8
    axes = []
    for i, (name, cls) in enumerate(panels):
        ax = fig.add_axes([0.33, top - (i + 1) * h + 0.006, 0.62, h - 0.012], sharex=axes[0] if axes else None)
        vals = vals_all[name]
        neutral = cls in (["other"], ["liquidity_non_pk"])
        cols = [(NEUTRAL if neutral else (BUY if v >= 0 else SELL)) for v in vals]
        ax.bar(t, vals, width=width, color=cols, align="edge")
        ax.axhline(0, color=INK, lw=0.6)
        ax.set_ylim(-ymax, ymax)
        ax.set_yticks([-ymax / 2, 0, ymax / 2])
        ax.set_yticklabels([f"{-ymax / 2:g}", "0", f"+{ymax / 2:g}"], fontsize=9.5)
        if band:
            ax.axvspan(dt("2026-11-08 22:30:00"), dt("2026-11-08 23:30:00"), color="#F2F2F2", zorder=0, lw=0)
        net = sum(main[c]["net_in"] for c in cls)
        ntx = sum(main[c]["n_tx"] for c in cls)
        if ntx == 0:
            line = "no transactions"
        elif cls == ["liquidity_non_pk"]:
            nlegs = R["q3"]["liquidity_non_pk_detail"]["n_legs"]
            line = f"{'net deposited' if net > 0 else 'net withdrawn'} {abs(net) / 1e6:.2f}M, {nlegs} legs in {ntx} tx"
        else:
            line = f"{'net sold' if net > 0 else 'net bought'} {abs(net) / 1e6:.2f}M, {ntx} tx"
        yc = top - (i + 0.5) * h
        fig.text(0.04, yc + 0.002, name, fontsize=11.5, fontweight="semibold", va="bottom")
        fig.text(0.04, yc - 0.002, line, fontsize=10.5, color=MUTED, va="top")
        if i < len(panels) - 1:
            plt.setp(ax.get_xticklabels(), visible=False)
        axes.append(ax)
    timeaxis(axes[-1])
    q3 = R["q3"]
    ybn = q3["variants"]["V0_main_net_same_tx"]
    title = f"Selling through Curve crvUSD pools where Yield Basis is the LP, mostly BTC, put a net {ybn / 1e6:.2f}M crvUSD into the peg pools"
    v5 = q3["variants"]["V5_curve_pool_leg_only"]
    lev = q3["variants"]["levamm_leg_only"]
    btc = q3["yb_net_rollup"]["btc_markets_only"]
    sub = (f"{ybn / 1e6:.2f}M is {v5 / 1e6:.2f}M sold through the Curve pools minus {abs(lev) / 1e6:.2f}M bought through the LEVAMM leg, "
           f"{btc / 1e6:.2f}M of it through the BTC pools, most of it between 21:45 and 22:00 UTC. Net crvUSD flow in the five PegKeeper pools per 15 minutes, million crvUSD. "
           "Above zero (blue) is crvUSD bought out of the pools, below zero (vermillion) is crvUSD sold in. Other swaps and liquidity "
           "deposits in gray. Classes assigned per transaction by the pre-registered rules.")
    if square:
        tl = textwrap.wrap(title, 56)
        fig.text(0.04, 0.965, "\n".join(tl), fontsize=24, fontweight="semibold", va="top", linespacing=1.2)
        fig.text(0.04, 0.965 - 0.034 * len(tl) - 0.014, "\n".join(textwrap.wrap(sub, 110, break_on_hyphens=False)), fontsize=13,
                 color=MUTED, va="top", linespacing=1.35)
    else:
        header(fig, title, sub, width=124)
    note = ("Times in UTC. Shaded band is the pre-registered flush hour, which missed the actual drop at 21:41 to 21:56. Rules in PREREG_ADDENDUM.md."
            if band else "Times in UTC. Classification rules in PREREG_ADDENDUM.md.")
    source(fig, note, width=128 if square else 150)
    name = "C3_flows_by_class_square" if square else "C3_flows_by_class"
    if not band:
        name += "_post"
    save(fig, root, name)


# ---------------------------------------------------------------- C4
def c4(root, R, square=False):
    V = R["q3"]["variants"]
    claim = 4.10e6
    v5 = V["V5_curve_pool_leg_only"]
    v0 = V["V0_main_net_same_tx"]
    v3 = V["V3_with_cross_tx"]
    steps = [("YB Curve\npool leg,\nnet", v5, "total"),
             ("Net the\nLEVAMM leg", v0 - v5, "delta"),
             ("All YB\nroutes, net\n(V0, main)", v0, "total"),
             ("Link other\ntx by sender\nor contract", v3 - v0, "delta"),
             ("With\nlinkage (V3,\nupper bound)", v3, "total")]
    fig = plt.figure(figsize=(12, 12) if square else (12, 6.75), dpi=200)
    ax = fig.add_axes([0.08, 0.25 if not square else 0.20, 0.87, 0.49 if not square else 0.58])
    run = 0.0
    for i, (lab, val, kind) in enumerate(steps):
        if kind == "total":
            col = SELL if val > 0 else BUY
            ax.bar(i, val / 1e6, color=col, width=0.62, edgecolor="white")
            run = val
            ax.text(i, val / 1e6 - 0.12, f"{val / 1e6:.2f}M", ha="center", va="top", fontsize=13, fontweight="semibold", color="white")
        else:
            col = NEUTRAL if kind == "gap" else (SELL if val > 0 else BUY)
            ax.bar(i, val / 1e6, bottom=run / 1e6, color=col, width=0.62, alpha=0.45)
            y = (run + val) / 1e6
            ax.text(i + 0.34, (run + val / 2) / 1e6, f"{val / 1e6:+.2f}M", ha="left", va="center", fontsize=11, color=MUTED)
            ax.plot([i - 0.31, i + 0.31], [y, y], color=INK, lw=0.6)
        ax.text(i, ax.get_ylim()[0], "", ha="center")
    ax.axhline(0, color=INK, lw=0.7)
    ax.axhline(claim / 1e6, color=MUTED, lw=1.0, ls=(0, (4, 3)))
    ax.text(len(steps) - 0.5, claim / 1e6 + 0.05, "circulating claim 4.10M, definition unknown", ha="right", va="bottom", fontsize=10.5, color=MUTED)
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels([s[0] for s in steps], fontsize=10.5, linespacing=1.2)
    ax.set_ylabel("million crvUSD sold into peg pools (positive)")
    ymin, ymaxv = ax.get_ylim()
    ax.set_ylim(min(ymin, -0.3), ymaxv + 0.35)
    pct = 100 * (v0 - claim) / claim
    title = f"The main measure lands {abs(pct):.0f} percent below the circulating 4.10M figure"
    sub = (f"Net crvUSD sold into the five PegKeeper pools by transactions with a Yield Basis leg, 20:00 to 04:00 UTC. "
           f"Other full-window definitions give {min(V[k] for k in ('V2_gross_sells','V3_with_cross_tx','V4_usdc_usdt_only','V0_main_net_same_tx')) / 1e6:.2f}M to "
           f"{V['V2_gross_sells'] / 1e6:.2f}M, so a match does not tell which definition the claim used. Linking by sender alone moves only "
           f"{R['q3']['s1_from_only_moved_net_in'] / 1e6:+.2f}M. Most of the V3 change comes from shared router contracts.")
    if square:
        header(fig, "\n".join(textwrap.wrap(title, 52)), sub, width=88, top=0.965)
    else:
        header(fig, title, sub, width=124)
    source(fig, "No primary source for the claim was found. The pre-registered flush hour (22:30 to 23:30) missed the drop and gives "
                f"{V['V1_flush_hour'] / 1e6:+.2f}M. Rules in PREREG_ADDENDUM.md.")
    save(fig, root, "C4_claim_waterfall_square" if square else "C4_claim_waterfall")


# ---------------------------------------------------------------- C5
def c5(root, R):
    rows = [r for r in read_csv(root, "soft_liquidation_by_market.csv") if r["mint_market"] == "True" and float(r["converted_usd"]) > 0]
    rows.sort(key=lambda r: float(r["converted_usd"]))
    fig = fig16x9()
    axl = fig.add_axes([0.13, 0.25, 0.38, 0.46])
    axr = fig.add_axes([0.58, 0.25, 0.36, 0.46], sharey=axl)
    names = [f"{r['market']} ({r['n_exchanges']} trades)" for r in rows]
    conv = [float(r["converted_usd"]) / 1e3 for r in rows]
    loss = [float(r["loss_pct_of_converted"]) for r in rows]
    y = list(range(len(rows)))
    axl.barh(y, conv, color=INK, height=0.5)
    for i, v in enumerate(conv):
        axl.text(v, i, f"  {v:,.1f}k", va="center", fontsize=11)
    axl.set_yticks(y)
    axl.set_yticklabels(names, fontsize=11.5)
    axl.set_xlabel("collateral value converted to crvUSD, thousand USD")
    axl.set_xlim(0, max(conv) * 1.3)
    axr.barh(y, loss, color=[INK if v > 0 else NEUTRAL for v in loss], height=0.5)
    for i, v in enumerate(loss):
        axr.text(v, i, (f"  {v:.2f}%" if v >= 0 else f"{v:.2f}%  "), va="center", ha="left" if v >= 0 else "right", fontsize=11)
    ref8 = R["soft_liquidation"]["doc_reference_pct_8h"]
    axr.axvline(0, color=INK, lw=0.6)
    axr.set_xlabel("loss at oracle price, % of value converted")
    lo, hi = min(loss + [0]), max(loss + [0.1])
    axr.set_xlim(lo - 0.6, hi * 1.35)
    plt.setp(axr.get_yticklabels(), visible=False)
    s = R["soft_liquidation"]
    header(fig, f"Soft liquidation barely engaged. {s['mint_converted_usd'] / 1e3:,.0f}k USD of collateral was converted",
           f"crvUSD mint markets, 20:00 to 04:00 UTC, {sum(int(r['n_exchanges']) for r in rows)} trades, all between 22:02 and 23:05, almost all while the EMA oracle was still falling. "
           "Loss is measured at that lagging oracle, so its sign is not interpretable. A negative loss means the trades executed above the oracle. "
           f"{s['hard_liquidations_mint']} hard liquidations, one with 10.8k crvUSD of debt and two dust positions.",
           width=124)
    source(fig, "Loss = value leaving LLAMMA minus value entering it, both at price_oracle, over soft and de-liquidation trades.")
    save(fig, root, "C5_soft_liquidation")


# ---------------------------------------------------------------- C6
def c6(root, R):
    preds = {}
    with open(os.path.join(root, "PREDICTIONS.md")) as f:
        for line in f:
            if line.startswith("P") and ". " in line[:5]:
                pid, rest = line.split(". ", 1)
                txt = rest.split(" Confidence ")[0].strip()
                import re
                mm = re.search(r"Confidence (0\.\d+)", rest)
                conf = mm.group(1) if mm else ""
                preds[pid.strip()] = (txt, conf)
    P = R["predictions"]
    ids = sorted(P, key=lambda k: int(k[1:]))
    fig = plt.figure(figsize=(12, 16), dpi=200)
    fig.text(0.04, 0.975, "Pre-registered predictions and results", fontsize=19, fontweight="semibold", va="top")
    n = {k: sum(1 for i in ids if P[i]["result"] == k) for k in ("HIT", "MISS", "PARTIAL", "UNTESTABLE")}
    fig.text(0.04, 0.955, f"{n['HIT']} hit, {n['MISS']} missed, {n['UNTESTABLE']} untestable in release 1. Weak tests marked w and not counted as calibration evidence.",
             fontsize=12, color=MUTED, va="top")
    y = 0.925
    dy = 0.0225
    for k in ids:
        txt, conf = preds.get(k, ("", ""))
        if len(txt) > 100:
            txt = txt[:97].rsplit(" ", 1)[0] + " ..."
        res = P[k]["result"]
        col = {"HIT": BUY, "MISS": SELL}.get(res, NEUTRAL)
        fig.text(0.04, y, k, fontsize=10.5, fontweight="semibold", va="top")
        fig.text(0.09, y, txt, fontsize=10, va="top")
        fig.text(0.80, y, conf, fontsize=10, color=MUTED, va="top")
        fig.text(0.85, y, res + (" w" if P[k]["weak_test"] else ""), fontsize=10, color=col, fontweight="semibold", va="top")
        y -= dy
    fig.text(0.80, 0.94, "conf.", fontsize=9.5, color=MUTED)
    fig.text(0.85, 0.94, "result", fontsize=9.5, color=MUTED)
    fig.text(0.04, 0.012, "Predictions recorded 2026-11-09 10:16 UTC before any chain data. Scoring rules in PREREG_ADDENDUM.md. Data and code: " + REPO_URL,
             fontsize=9.5, color=MUTED)
    save(fig, root, "C6_predictions_scorecard")


def main(root):
    setup()
    R = json.load(open(os.path.join(root, "data", "results.json")))
    c1(root, R)
    if os.path.exists(os.path.join(root, "code", "raw", "context_pegkeepers_30d.json")):
        c2(root, R)
    c3(root, R)
    c3(root, R, square=True)
    c3(root, R, square=True, band=False)
    c4(root, R)
    c4(root, R, square=True)
    c5(root, R)
    c6(root, R)
    print("charts written")


if __name__ == "__main__":
    main(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

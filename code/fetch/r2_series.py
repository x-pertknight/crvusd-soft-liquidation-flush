"""Release 2 main series. Reads, at the first block of each hour since 2026-09-01:
  tier 1, every hour: debt() of the five PegKeepers and the aggregator price().
  tier 2, only hours where some PegKeeper has debt above 1 crvUSD and price is below 1, for that PegKeeper:
          pool balances, get_p, price_oracle, withdraw_allowed (phase A), then a simulated update() from a dummy
          address (phase B) for blocks not on the provide side and for every 10th provide-side block.
          is_killed is read daily and at every Provide or Withdraw event (r2_extra.py).
  daily: Regulator parameters (alpha, beta, price_deviation, worst_price_threshold, aggregator, is_killed).
Raw answers go to code/raw/r2_series/*.json. Rerunning skips what is already saved."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, REGULATOR, AGGREGATOR, batch_calls, selector, enc_addr  # noqa: E402

OUT = os.path.join(ROOT, "code", "raw", "r2_series")
os.makedirs(OUT, exist_ok=True)
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PKS = C["pegkeepers"]
HOURS = json.load(open(os.path.join(ROOT, "code", "raw", "r2_hour_blocks.json")))["hours"]
DUMMY = "0x000000000000000000000000000000000000dead"  # caller for simulated update()
ONE = 10 ** 18
SEL = {n: selector(n) for n in [
    "debt()", "price()", "balances(uint256)", "get_p()", "get_p(uint256)", "price_oracle()", "price_oracle(uint256)",
    "withdraw_allowed(address)", "provide_allowed(address)", "is_killed()", "last_change()",
    "estimate_caller_profit()", "update(address)", "alpha()", "beta()", "price_deviation()",
    "worst_price_threshold()", "aggregator()"]}


def save(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), "w"))


def load(name):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


def tier1():
    done = load("tier1.json") or {}
    todo = [b for _, b, _ in HOURS if str(b) not in done]
    for i in range(0, len(todo), 60):  # save every 60 hours
        part = todo[i:i + 60]
        calls = []
        for b in part:
            calls += [(p["pegkeeper"], SEL["debt()"], b) for p in PKS] + [(AGGREGATOR, SEL["price()"], b)]
        res = batch_calls(calls)
        for j, b in enumerate(part):
            done[str(b)] = res[j * 6:(j + 1) * 6]
        save("tier1.json", done)
        print("tier1", len(done), "of", len(HOURS), flush=True)
    return done


def hexint(x):
    return int(x, 16) if isinstance(x, str) and x.startswith("0x") and len(x) > 2 else None


def pk_calls(p, b):
    """Phase A reads for one PegKeeper at block b: both balances, spot, oracle, withdraw_allowed."""
    pk, pool = p["pegkeeper"], p["pool"]
    g = SEL["get_p(uint256)"] + "0" * 64 if p["include_index"] else SEL["get_p()"]
    o = SEL["price_oracle(uint256)"] + "0" * 64 if p["include_index"] else SEL["price_oracle()"]
    return [(pool, SEL["balances(uint256)"] + "0" * 64, b), (pool, SEL["balances(uint256)"] + "0" * 63 + "1", b),
            (pool, g, b), (pool, o, b), (REGULATOR, SEL["withdraw_allowed(address)"] + enc_addr(pk), b)]


def provide_side(k, reads):
    """Balance test of PegKeeperV2.update(): more of the other coin than crvUSD means the provide branch."""
    mul = 10 ** (18 - PKS[k]["coin_decimals"][0])
    return hexint(reads[0]) * mul > hexint(reads[1])


def tier2(t1):
    """Entries: 'block:pk' -> [bal_other, bal_crv, get_p, price_oracle, withdraw_allowed, simulated update() or None].
    The simulation runs for every block that is not on the provide side, and for every 10th provide-side block."""
    done = load("tier2.json") or {}
    for key, v in list(done.items()):  # entries from the first version of this script had 10 reads
        if len(v) == 10:
            done[key] = v[:5] + [v[9]]
    jobs = []
    for _, b, _ in HOURS:
        r = t1[str(b)]
        price = hexint(r[5])
        if price is None or price >= ONE:
            continue
        jobs += [(b, k) for k in range(5) if (hexint(r[k]) or 0) > ONE and f"{b}:{k}" not in done]
    print("tier2 jobs", len(jobs), flush=True)
    for i in range(0, len(jobs), 40):
        part = jobs[i:i + 40]
        res = batch_calls([c for b, k in part for c in pk_calls(PKS[k], b)])
        for j, (b, k) in enumerate(part):
            done[f"{b}:{k}"] = res[j * 5:(j + 1) * 5] + [None]
        save("tier2.json", done)
        print("tier2 A", len(done), flush=True)
    sims = [key for key, v in done.items() if v[5] is None and (
        not provide_side(int(key.split(":")[1]), v) or int(key.split(":")[0]) % 10 == 0)]
    # old entries with a simulation already stored are kept as they are
    print("tier2 sims", len(sims), flush=True)
    for i in range(0, len(sims), 40):
        part = sims[i:i + 40]
        calls = [(PKS[int(k.split(":")[1])]["pegkeeper"], SEL["update(address)"] + enc_addr(DUMMY),
                  int(k.split(":")[0]), DUMMY) for k in part]
        for key, r in zip(part, batch_calls(calls)):
            done[key][5] = r
        save("tier2.json", done)
        print("tier2 B", i + len(part), flush=True)
    return done


def daily():
    done = load("daily.json") or {}
    blocks = [b for n, (_, b, _) in enumerate(HOURS) if n % 24 == 0] + [HOURS[-1][1]]
    todo = [b for b in blocks if str(b) not in done]
    names = ["alpha()", "beta()", "price_deviation()", "worst_price_threshold()", "aggregator()", "is_killed()"]
    for b in todo:
        res = batch_calls([(REGULATOR, SEL[n], b) for n in names])
        done[str(b)] = dict(zip(names, res))
    save("daily.json", done)
    print("daily", len(done), flush=True)


if __name__ == "__main__":
    t1 = tier1()
    daily()
    tier2(t1)
    print("series done")

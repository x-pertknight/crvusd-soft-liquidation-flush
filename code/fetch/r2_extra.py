"""Release 2 extra reads, run after r2_series.py:
  events:  state at the block BEFORE every Provide and Withdraw event since 2026-09-01 (from the API event lists):
           aggregator price, both pool balances, get_p, price_oracle, withdraw_allowed, provide_allowed, is_killed.
  pre:     provide_allowed, withdraw_allowed, debt and crvUSD held for each PegKeeper at block 26,372,407
           (the release 1 window start), for the debt limit check (R2-14).
  pairs:   the aggregator's price_pairs(i) at the latest block.
  ceilings: ControllerFactory.debt_ceiling(pegkeeper) and the crvUSD each PegKeeper holds, daily and at the
           latest block. Release 1's "324M" is the sum of these factory ceilings, not a Regulator limit.
Writes code/raw/r2_extra.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, REGULATOR, AGGREGATOR, batch_calls, selector, enc_addr, rpc  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PKS = C["pegkeepers"]
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
PRE = C["window"]["pre_block"]
S = {n: selector(n) for n in ["price()", "balances(uint256)", "get_p()", "get_p(uint256)", "price_oracle()",
                              "price_oracle(uint256)", "withdraw_allowed(address)", "provide_allowed(address)",
                              "is_killed()", "debt()", "balanceOf(address)", "price_pairs(uint256)",
                              "debt_ceiling(address)"]}
FACTORY = "0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC"  # ControllerFactory, as in release 1


def pool_reads(p, b):
    """The seven reads used for one PegKeeper at block b, in a fixed order."""
    idx = "0" * 64
    g = S["get_p(uint256)"] + idx if p["include_index"] else S["get_p()"]
    o = S["price_oracle(uint256)"] + idx if p["include_index"] else S["price_oracle()"]
    return [(AGGREGATOR, S["price()"], b), (p["pool"], S["balances(uint256)"] + idx, b),
            (p["pool"], S["balances(uint256)"] + "0" * 63 + "1", b), (p["pool"], g, b), (p["pool"], o, b),
            (REGULATOR, S["withdraw_allowed(address)"] + enc_addr(p["pegkeeper"]), b),
            (REGULATOR, S["provide_allowed(address)"] + enc_addr(p["pegkeeper"]), b),
            (REGULATOR, S["is_killed()"], b)]


def event_reads():
    by_name = {p["name"]: p for p in PKS}
    jobs = []
    for name, p in by_name.items():
        ev = json.load(open(os.path.join(ROOT, "code", "raw", "r2_api", f"events_{name}.json")))["events"]
        jobs += [(name, e["block_number"], e["action_type"]) for e in ev
                 if e["action_type"] in ("Provide", "Withdraw") and e["timestamp"] >= 1788220800]
    calls = [c for name, b, _ in jobs for c in pool_reads(by_name[name], b - 1)]
    res = batch_calls(calls)
    return [{"pk": n, "block": b, "type": t, "reads": res[i * 8:(i + 1) * 8]} for i, (n, b, t) in enumerate(jobs)]


def pre_reads():
    calls = []
    for p in PKS:
        pk = p["pegkeeper"]
        calls += [(REGULATOR, S["provide_allowed(address)"] + enc_addr(pk), PRE),
                  (REGULATOR, S["withdraw_allowed(address)"] + enc_addr(pk), PRE),
                  (pk, S["debt()"], PRE), (CRVUSD, S["balanceOf(address)"] + enc_addr(pk), PRE)]
    calls.append((AGGREGATOR, S["price()"], PRE))
    res = batch_calls(calls)
    return {"block": PRE, "per_pk": {p["name"]: res[i * 4:(i + 1) * 4] for i, p in enumerate(PKS)},
            "aggregator_price": res[-1]}


def pairs_reads(head):
    res = batch_calls([(AGGREGATOR, S["price_pairs(uint256)"] + f"{i:064x}", head) for i in range(8)])
    return {"block": head, "price_pairs": res}


def ceiling_reads(head):
    hours = json.load(open(os.path.join(ROOT, "code", "raw", "r2_hour_blocks.json")))["hours"]
    blocks = [b for n, (_, b, _) in enumerate(hours) if n % 24 == 0] + [head]
    calls = []
    for b in blocks:
        for p in PKS:
            calls += [(FACTORY, S["debt_ceiling(address)"] + enc_addr(p["pegkeeper"]), b),
                      (CRVUSD, S["balanceOf(address)"] + enc_addr(p["pegkeeper"]), b)]
    res = batch_calls(calls)
    return {str(b): {p["name"]: res[(i * 5 + k) * 2:(i * 5 + k) * 2 + 2] for k, p in enumerate(PKS)}
            for i, b in enumerate(blocks)}


if __name__ == "__main__":
    head = int(rpc("eth_blockNumber", []), 16)
    out = {"pre": pre_reads(), "pairs": pairs_reads(head), "ceilings": ceiling_reads(head),
           "events": event_reads()}
    json.dump(out, open(os.path.join(ROOT, "code", "raw", "r2_extra.json"), "w"))
    print("events", len(out["events"]), "pairs", [x[:12] for x in out["pairs"]["price_pairs"]])

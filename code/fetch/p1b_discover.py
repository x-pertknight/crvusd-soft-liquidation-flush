"""Phase 1b step 1. Candidate pools for set S (PHASE_1B_ADDENDUM.md section 2), read at a fixed block."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import selector  # noqa: E402
from p1b_net import State, ROOT, RAW  # noqa: E402

REF = 26_378_000
FACTORIES = {"twocrypto_ng": ("0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F", 2),
             "tricrypto_ng": ("0x0c0e5f2fF0ff18a3be9b835635039256dC4B4963", 3)}
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
VOL = {"WBTC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", "cbBTC": "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf",
       "tBTC": "0x18084fba666a33d37592fa2633fd49a74dd93a88", "LBTC": "0x8236a87084f8b84306f72007f36f2618a5634494",
       "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "wstETH": "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"}
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
st = State("discovery_state")


def u(h):
    return int(h, 16)


def enc(x):
    return hex(x)[2:].rjust(64, "0") if isinstance(x, int) else x.lower()[2:].rjust(64, "0")


def addr_words(h):
    h = h[2:]
    return ["0x" + h[i + 24:i + 64] for i in range(0, len(h), 64)]


def text(h):
    b = bytes.fromhex(h[2:])
    if len(b) >= 96:
        n = int.from_bytes(b[32:64], "big")
        return b[64:64 + n].decode(errors="replace")
    return b.rstrip(b"\0").decode(errors="replace")


tokens = {}
for sym, a in VOL.items():
    s = text(st.call(a, selector("symbol()"), REF))
    d = u(st.call(a, selector("decimals()"), REF))
    tokens[a] = {"expected": sym, "symbol": s, "decimals": d}
    print(sym, s, d)
st.flush()

cands = []
for fname, (fac, ncoins) in FACTORIES.items():
    n = u(st.call(fac, selector("pool_count()"), REF))
    print(fname, n)
    for i in range(n):
        pool = addr_words(st.call(fac, selector("pool_list(uint256)") + enc(i), REF))[0]
        coins = addr_words(st.call(fac, selector("get_coins(address)") + enc(pool), REF))[:ncoins]
        if CRVUSD in coins and any(c in VOL.values() for c in coins):
            cands.append({"pool": pool, "factory": fname, "factory_index": i, "coins": coins})
        if i % 50 == 0:
            st.flush()
    st.flush()

yb_pools = sorted({m["pool"].lower() for m in C["yb_markets"]})
for p in yb_pools:
    coins = []
    for j in range(3):
        r = st.call(p, selector("coins(uint256)") + enc(j), REF)
        if r.startswith("ERR") or len(r) < 66:
            break
        coins.append(addr_words(r)[0])
    hit = [c for c in cands if c["pool"] == p]
    if hit:
        hit[0]["yield_basis"] = True
    else:
        cands.append({"pool": p, "factory": "yield_basis_contracts_json", "factory_index": None, "coins": coins,
                      "yield_basis": True, "pairing_ok": CRVUSD in coins and any(c in VOL.values() for c in coins)})
st.flush()
for c in cands:
    c.setdefault("yield_basis", c["pool"] in yb_pools)
out = {"reference_block": REF, "rule": "PHASE_1B_ADDENDUM.md section 2", "tokens": tokens,
       "candidates": sorted(cands, key=lambda c: (c["factory"], c["pool"]))}
json.dump(out, open(os.path.join(RAW, "s_candidates.json"), "w"), indent=1, sort_keys=True)
print("candidates", len(cands), "yield basis", sum(c["yield_basis"] for c in cands))

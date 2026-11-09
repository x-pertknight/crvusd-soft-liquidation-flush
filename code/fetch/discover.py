"""Read current protocol contract addresses from on-chain registries. No window data.
Writes code/raw/discovery_latest.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, word, addr_word, enc_uint, rpc  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CRVUSD = "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E"
FACTORY = "0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC"
REGULATOR = "0x36a04CAffc681fa179558B2Aaba30395CDdd855f"
CL_ETH_USD_PROXY = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"


def a(to, sig, *args):
    return addr_word(call(to, selector(sig) + "".join(enc_uint(x) for x in args)), 0)


def u(to, sig, *args):
    return word(call(to, selector(sig) + "".join(enc_uint(x) for x in args)), 0)


def uo(to, sig, *args):
    try:
        return u(to, sig, *args)
    except RuntimeError:
        return None


def sym(token):
    try:
        r = call(token, selector("symbol()"))
        h = r[2:]
        ln = int(h[64:128], 16)
        return bytes.fromhex(h[128:128 + 2 * ln]).decode()
    except Exception:
        return "?"


out = {"block": int(rpc("eth_blockNumber", []), 16)}

out["regulator_aggregator"] = a(REGULATOR, "aggregator()")
pks = []
for i in range(8):
    try:
        r = call(REGULATOR, selector("peg_keepers(uint256)") + enc_uint(i))
    except RuntimeError:
        break
    if r in ("0x", None) or len(r) < 66:
        break
    pk, pool = addr_word(r, 0), addr_word(r, 1)
    is_inverse, include_index = word(r, 2), word(r, 3)
    coins = [a(pool, "coins(uint256)", j) for j in range(2)]
    pks.append({
        "pegkeeper": pk, "pool": pool, "is_inverse": is_inverse, "include_index": include_index,
        "coins": coins, "coin_symbols": [sym(c) for c in coins],
        "debt_now": u(pk, "debt()"), "action_delay": uo(pk, "action_delay()"), "ACTION_DELAY": uo(pk, "ACTION_DELAY()"),
        "regulator": uo(pk, "regulator()") and a(pk, "regulator()"),
    })
out["pegkeepers"] = pks

n = u(FACTORY, "n_collaterals()")
mk = []
for i in range(n):
    ctrl = a(FACTORY, "controllers(uint256)", i)
    amm = a(FACTORY, "amms(uint256)", i)
    col = a(FACTORY, "collaterals(uint256)", i)
    mp = a(ctrl, "monetary_policy()")
    mk.append({"index": i, "collateral": col, "symbol": sym(col), "controller": ctrl, "amm": amm,
               "monetary_policy": mp, "n_loans_now": u(ctrl, "n_loans()"),
               "total_debt_now": u(ctrl, "total_debt()")})
out["mint_markets"] = mk
out["chainlink_eth_usd_proxy"] = CL_ETH_USD_PROXY
out["chainlink_eth_usd_aggregator_now"] = a(CL_ETH_USD_PROXY, "aggregator()")

path = os.path.join(ROOT, "code", "raw", "discovery_latest.json")
with open(path, "w") as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))

"""Fetch every log emitted by the study contracts in the main window, plus crvUSD transfers
touching PegKeeper pools. Raw JSON-RPC results are written unchanged to code/raw/logs/."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, addr_word, word, enc_uint, get_logs, k256  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "code", "raw")
W = json.load(open(os.path.join(RAW, "window_blocks.json")))
B0 = W["main_start"]["first_block_at_or_after"]
B1 = W["main_end"]["first_block_at_or_after"] - 1
PRE = B0 - 1

CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
REGULATOR = "0x36a04caffc681fa179558b2aaba30395cddd855f"
FACTORY = "0xc9332fdcb1c491dcc683bae86fe3cb70360738bc"
LL_FACTORY = "0xea6876dde9e3467564acbee1ed5bac88783205e0"
YB_FACTORY = "0x370a449febb9411c95bf897021377fe0b7d100c0"
CL_PROXY = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"


def a(to, sig, *args, block=PRE):
    return addr_word(call(to, selector(sig) + "".join(enc_uint(x) for x in args), block), 0)


def u(to, sig, *args, block=PRE):
    return word(call(to, selector(sig) + "".join(enc_uint(x) for x in args), block), 0)


c = {"window": {"pre_block": PRE, "first_block": B0, "last_block": B1}, "sources": {}}

# PegKeepers as registered at the block before the window
pks = []
for i in range(10):
    try:
        r = call(REGULATOR, selector("peg_keepers(uint256)") + enc_uint(i), PRE)
    except RuntimeError:
        break
    if len(r) < 66:
        break
    pks.append({"pegkeeper": addr_word(r, 0), "pool": addr_word(r, 1),
                "is_inverse": word(r, 2), "include_index": word(r, 3)})
c["pegkeepers"] = pks
c["sources"]["pegkeepers"] = "PegKeeperRegulator.peg_keepers(i) at pre_block; regulator address from docs.curve.finance/developer/deployments"

# Mint markets
n = u(FACTORY, "n_collaterals()")
c["mint_markets"] = [{"controller": a(FACTORY, "controllers(uint256)", i), "amm": a(FACTORY, "amms(uint256)", i),
                      "collateral": a(FACTORY, "collaterals(uint256)", i)} for i in range(n)]
c["sources"]["mint_markets"] = "ControllerFactory controllers/amms/collaterals at pre_block; factory from docs deployments"

# Llamalend v1 markets with crvUSD as the borrowed token
m = u(LL_FACTORY, "market_count()")
ll = []
for i in range(m):
    bt = a(LL_FACTORY, "borrowed_tokens(uint256)", i)
    if bt.lower() != CRVUSD:
        continue
    ll.append({"index": i, "controller": a(LL_FACTORY, "controllers(uint256)", i),
               "amm": a(LL_FACTORY, "amms(uint256)", i), "collateral": a(LL_FACTORY, "collateral_tokens(uint256)", i)})
c["llamalend_v1_markets"] = ll
c["sources"]["llamalend_v1_markets"] = "OneWayLendingFactory market_count/controllers/amms/borrowed_tokens at pre_block"

# Yield Basis markets, from docs list, confirmed with Factory.markets(i)
yb_docs = json.load(open(os.path.join(os.path.dirname(__file__), "yb_markets_docs.json")))
yb = []
for mkt in yb_docs:
    try:
        r = call(YB_FACTORY, selector("markets(uint256)") + enc_uint(mkt["market"]), PRE)
        words = [addr_word(r, j) for j in range(len(r[2:]) // 64)]
    except RuntimeError as e:
        words = [f"error {e}"]
    mkt["factory_markets_words"] = words
    mkt["confirmed"] = all(x.lower() in [w.lower() for w in words] for x in (mkt["levamm"], mkt["pool"]))
    yb.append(mkt)
c["yb_markets"] = yb
c["sources"]["yb_markets"] = "docs.yieldbasis.com/user/reference/contract-addresses, confirmed by Factory.markets(i) at pre_block"
c["chainlink_eth_usd_proxy"] = CL_PROXY
c["chainlink_eth_usd_aggregator"] = a(CL_PROXY, "aggregator()")
c["sources"]["chainlink"] = "EACAggregatorProxy.aggregator() at pre_block"
c["crvusd"] = CRVUSD
json.dump(c, open(os.path.join(ROOT, "code", "contracts.json"), "w"), indent=1)
print("contracts written", len(pks), len(c["mint_markets"]), len(ll), len(yb))

os.makedirs(os.path.join(RAW, "logs"), exist_ok=True)


def save(name, logs):
    json.dump(logs, open(os.path.join(RAW, "logs", name + ".json"), "w"))
    print(name, len(logs))


pools = [p["pool"] for p in pks]
T = k256("Transfer(address,address,uint256)")
pad = ["0x" + "0" * 24 + p[2:].lower() for p in pools]
save("crvusd_transfer_to_pools", get_logs(CRVUSD, B0, B1, [T, None, pad], chunk=200))
save("crvusd_transfer_from_pools", get_logs(CRVUSD, B0, B1, [T, pad], chunk=200))
save("pegkeeper_pools", get_logs(pools, B0, B1, chunk=200))
save("pegkeepers", get_logs([p["pegkeeper"] for p in pks], B0, B1, chunk=500))
mint_addrs = [x["controller"] for x in c["mint_markets"]] + [x["amm"] for x in c["mint_markets"]]
save("mint_markets", get_logs(mint_addrs, B0, B1, chunk=300))
ll_addrs = [x["controller"] for x in ll] + [x["amm"] for x in ll]
save("llamalend_v1", get_logs(ll_addrs, B0, B1, chunk=300) if ll_addrs else [])
yb_addrs = []
for x in yb:
    yb_addrs += [x["levamm"], x["pool"], x["virtual_pool"]]
save("yieldbasis", get_logs(yb_addrs, B0, B1, chunk=200))
save("chainlink_eth_usd", get_logs(c["chainlink_eth_usd_aggregator"], B0 - 400, B1, chunk=1000))

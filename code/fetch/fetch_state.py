"""Archive eth_call reads and transaction lookups needed by recompute.py.
Every raw hex result is stored unchanged in code/raw/state.json, keyed by "to|data|block"."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, enc_uint, rpc  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "code", "raw")
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PRE, B0, B1 = C["window"]["pre_block"], C["window"]["first_block"], C["window"]["last_block"]
WB = json.load(open(os.path.join(RAW, "window_blocks.json")))
F0 = WB["flush_start"]["first_block_at_or_after"]
F1 = WB["flush_end"]["first_block_at_or_after"] - 1
AGG = "0x18672b1b0c623a30089a280ed9256379fb0e4e62"

path = os.path.join(RAW, "state.json")
S = json.load(open(path)) if os.path.exists(path) else {}


def q(to, sig, args=(), block=PRE):
    data = selector(sig) + "".join(enc_uint(x) for x in args)
    key = f"{to.lower()}|{data}|{block}"
    if key in S:
        return
    try:
        S[key] = call(to, data, block)
    except RuntimeError as e:
        S[key] = "ERR " + str(e)[:80]


def logs(name):
    return json.load(open(os.path.join(RAW, "logs", name + ".json")))


def flush():
    json.dump(S, open(path, "w"))


# 1. PegKeeper pools: price at pre block and at every block with a pool log, balances and debt
pool_blocks = {}
for lg in logs("pegkeeper_pools"):
    pool_blocks.setdefault(lg["address"].lower(), set()).add(int(lg["blockNumber"], 16))
for pk in C["pegkeepers"]:
    pool = pk["pool"].lower()
    sig, args = ("get_p(uint256)", (0,)) if pk["include_index"] else ("get_p()", ())
    for b in [PRE, B1] + sorted(pool_blocks.get(pool, [])):
        q(pool, sig, args, b)
    for b in (PRE, B1):
        q(pool, "balances(uint256)", (0,), b)
        q(pool, "balances(uint256)", (1,), b)
        q(pk["pegkeeper"], "debt()", (), b)
    flush()
    print("pool done", pool)

# 2. Aggregator price, sampled every 10 blocks
for b in range(PRE, B1 + 1, 10):
    q(AGG, "price()", (), b)
flush()

# 3. LLAMMA price_oracle at every block with a TokenExchange, collateral decimals, WETH rate path
amm_ex = k_ex = None
from rpc import k256  # noqa: E402
TE_LLAMMA = k256("TokenExchange(address,uint256,uint256,uint256,uint256)")
for name, mk in (("mint_markets", C["mint_markets"]), ("llamalend_v1", C["llamalend_v1_markets"])):
    amms = {m["amm"].lower() for m in mk}
    for lg in logs(name):
        if lg["address"].lower() in amms and lg["topics"][0] == TE_LLAMMA:
            b = int(lg["blockNumber"], 16)
            q(lg["address"], "price_oracle()", (), b)
            q(lg["address"], "price_oracle()", (), b - 1)
    for m in mk:
        q(m["collateral"], "decimals()", (), PRE)
flush()
weth = [m for m in C["mint_markets"] if m["collateral"].lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"][0]
for b in range(PRE, B1 + 1, 25):
    q(weth["amm"], "rate()", (), b)
    q(weth["amm"], "price_oracle()", (), b)
flush()
print("llamma done")

# 4. Yield Basis LEVAMM state: every 50 blocks in the main window, every 5 in the flush hour, plus event blocks
lev_blocks = {}
for lg in logs("yieldbasis"):
    lev_blocks.setdefault(lg["address"].lower(), set()).add(int(lg["blockNumber"], 16))
for m in C["yb_markets"]:
    if m["status"] != "active":
        continue
    bl = set(range(PRE, B1 + 1, 50)) | set(range(F0, F1 + 1, 5)) | lev_blocks.get(m["levamm"].lower(), set()) | {B1}
    for b in sorted(bl):
        q(m["levamm"], "get_state()", (), b)
        q(m["lp_oracle"], "price()", (), b)
    flush()
    print("yb done", m["market"])

# 5. Transaction from/to for every transaction that moved crvUSD in or out of a PegKeeper pool
txs = {lg["transactionHash"] for n in ("crvusd_transfer_to_pools", "crvusd_transfer_from_pools") for lg in logs(n)}
tpath = os.path.join(RAW, "transactions.json")
T = json.load(open(tpath)) if os.path.exists(tpath) else {}
for i, h in enumerate(sorted(txs)):
    if h in T:
        continue
    t = rpc("eth_getTransactionByHash", [h])
    T[h] = {"from": t["from"], "to": t["to"], "blockNumber": t["blockNumber"], "transactionIndex": t["transactionIndex"]}
    if i % 100 == 0:
        json.dump(T, open(tpath, "w"))
json.dump(T, open(tpath, "w"))
print("tx done", len(T))

# 7. PegKeeper pool balances before and after every block with a liquidity event, and A() at the pre block
from rpc import k256 as _k  # noqa: E402
LIQ_TOPICS = {_k(x) for x in ("AddLiquidity(address,uint256[],uint256[],uint256,uint256)",
                              "AddLiquidity(address,uint256[2],uint256[2],uint256,uint256)",
                              "RemoveLiquidity(address,uint256[],uint256[],uint256)",
                              "RemoveLiquidity(address,uint256[2],uint256[2],uint256)",
                              "RemoveLiquidityOne(address,int128,uint256,uint256,uint256)",
                              "RemoveLiquidityOne(address,uint256,uint256,uint256)",
                              "RemoveLiquidityImbalance(address,uint256[],uint256[],uint256,uint256)",
                              "RemoveLiquidityImbalance(address,uint256[2],uint256[2],uint256,uint256)")}
for lg in logs("pegkeeper_pools"):
    if lg["topics"][0] in LIQ_TOPICS:
        b = int(lg["blockNumber"], 16)
        for blk in (b - 1, b):
            q(lg["address"], "balances(uint256)", (0,), blk)
            q(lg["address"], "balances(uint256)", (1,), blk)
for pk in C["pegkeepers"]:
    q(pk["pool"], "A()", (), PRE)
flush()
print("liquidity balances done")

# 6. Block timestamps for every block in the main window plus the pre block
bpath = os.path.join(RAW, "block_timestamps.json")
BT = json.load(open(bpath)) if os.path.exists(bpath) else {}
for b in range(PRE, B1 + 1):
    if str(b) in BT:
        continue
    BT[str(b)] = rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"]
    if b % 200 == 0:
        json.dump(BT, open(bpath, "w"))
json.dump(BT, open(bpath, "w"))
print("blocks done", len(BT))
flush()

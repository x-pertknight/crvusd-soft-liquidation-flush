"""Add names, coins and decimals to code/contracts.json and pin event topics and function
selectors in code/topics.json, so recompute.py needs no keccak implementation."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector, k256, addr_word, word, enc_uint  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = os.path.join(ROOT, "code", "contracts.json")
C = json.load(open(P))
PRE = C["window"]["pre_block"]


def sym(t):
    r = call(t, selector("symbol()"), PRE)[2:]
    ln = int(r[64:128], 16)
    return bytes.fromhex(r[128:128 + 2 * ln]).decode()


def dec(t):
    return word(call(t, selector("decimals()"), PRE), 0)


for p in C["pegkeepers"]:
    coins = [addr_word(call(p["pool"], selector("coins(uint256)") + enc_uint(j), PRE), 0) for j in range(2)]
    p["coins"] = coins
    p["coin_symbols"] = [sym(x) for x in coins]
    p["coin_decimals"] = [dec(x) for x in coins]
    p["name"] = {"PYUSD": "pyUSD"}.get(p["coin_symbols"][0], p["coin_symbols"][0])
for m in C["mint_markets"]:
    m["name"] = sym(m["collateral"])
seen = {}
for m in C["mint_markets"]:
    if m["name"] in seen:
        seen[m["name"]] += 1
        m["name"] = f"{m['name']} v{seen[m['name']]}"
    else:
        seen[m["name"]] = 1
for m in C["llamalend_v1_markets"]:
    try:
        m["name"] = f"{sym(m['collateral'])} #{m['index']}"
    except Exception:
        m["name"] = f"market #{m['index']}"
C["sources"]["names_decimals"] = "ERC20 symbol() and decimals() at pre_block"
json.dump(C, open(P, "w"), indent=1)

events = {
    "Transfer": "Transfer(address,address,uint256)",
    "TokenExchange_stableswap": "TokenExchange(address,int128,uint256,int128,uint256)",
    "TokenExchange_llamma": "TokenExchange(address,uint256,uint256,uint256,uint256)",
    "TokenExchange_twocrypto": "TokenExchange(address,uint256,uint256,uint256,uint256,uint256,uint256)",
    "Liquidate": "Liquidate(address,address,uint256,uint256,uint256)",
    "Borrow": "Borrow(address,uint256,uint256)",
    "Repay": "Repay(address,uint256,uint256)",
    "RemoveCollateral": "RemoveCollateral(address,uint256)",
    "Provide": "Provide(uint256)",
    "Withdraw_pk": "Withdraw(uint256)",
    "AnswerUpdated": "AnswerUpdated(int256,uint256,uint256)",
    "AddLiquidity_ng": "AddLiquidity(address,uint256[],uint256[],uint256,uint256)",
}
sels = ["get_p()", "get_p(uint256)", "balances(uint256)", "debt()", "price()", "price_oracle()", "rate()",
        "decimals()", "get_state()", "A()"]
out = {"event_signatures": events, "topics": {k: k256(v) for k, v in events.items()},
       "selectors": {s: selector(s) for s in sels},
       "aggregator": "0x18672b1b0c623a30089a280ed9256379fb0e4e62",
       "aggregator_source": "PegKeeperRegulator.aggregator(); listed as crvusd-price-aggregator-v3 on docs.curve.finance/developer/deployments",
       "signature_sources": "Event definitions in source shown on docs.curve.finance (AMM, Controller, PegKeeperV2) and Curve pool sources; each topic0 was observed in the cached logs"}
json.dump(out, open(os.path.join(ROOT, "code", "topics.json"), "w"), indent=1)
print(json.dumps({p["name"]: p["coin_decimals"] for p in C["pegkeepers"]}), [m["name"] for m in C["mint_markets"]])

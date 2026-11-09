"""Minimal JSON-RPC helpers for Ethereum mainnet. Network access lives only in code/fetch/."""
import json
import time
import urllib.request

from Crypto.Hash import keccak

RPC_URL = "https://eth.drpc.org"


def k256(text):
    h = keccak.new(digest_bits=256)
    h.update(text.encode())
    return "0x" + h.hexdigest()


def selector(sig):
    return k256(sig)[:10]


def rpc(method, params, retries=6):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC_URL, data=body, headers={"content-type": "application/json",
                                                                 "user-agent": "crvusd-flush-study/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                last = out["error"]
                if "revert" in str(last).lower():
                    raise RuntimeError(f"{method} reverted: {last}")
                time.sleep(1.5 * (attempt + 1))
                continue
            return out["result"]
        except RuntimeError:
            raise
        except Exception as e:  # network hiccup
            last = repr(e)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{method} failed: {last}")


def call(to, data, block="latest"):
    if isinstance(block, int):
        block = hex(block)
    return rpc("eth_call", [{"to": to, "data": data}, block])


def enc_uint(n):
    return hex(n)[2:].rjust(64, "0")


def enc_addr(a):
    return a.lower()[2:].rjust(64, "0")


def word(hexdata, i):
    h = hexdata[2:] if hexdata.startswith("0x") else hexdata
    return int(h[64 * i:64 * (i + 1)], 16)


def addr_word(hexdata, i):
    h = hexdata[2:] if hexdata.startswith("0x") else hexdata
    return "0x" + h[64 * i + 24:64 * (i + 1)]


def block_ts(n):
    b = rpc("eth_getBlockByNumber", [hex(n), False])
    return int(b["timestamp"], 16)


def first_block_at_or_after(ts):
    hi = int(rpc("eth_blockNumber", []), 16)
    lo = hi - 400_000
    while lo < hi:
        mid = (lo + hi) // 2
        if block_ts(mid) < ts:
            lo = mid + 1
        else:
            hi = mid
    return lo


def get_logs(address, from_block, to_block, topics=None, chunk=500):
    out = []
    b = from_block
    while b <= to_block:
        e = min(b + chunk - 1, to_block)
        params = {"fromBlock": hex(b), "toBlock": hex(e)}
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
        try:
            out.extend(rpc("eth_getLogs", [params]))
            b = e + 1
        except RuntimeError:
            if chunk <= 10:
                raise
            chunk //= 2
    return out

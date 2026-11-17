"""Release 2 helpers: batched JSON-RPC and block lookup by time. Network access lives only in code/fetch/."""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from rpc import RPC_URL, rpc, selector, word, addr_word, enc_uint, enc_addr  # noqa: E402,F401

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGULATOR = "0x36a04CAffc681fa179558B2Aaba30395CDdd855f"
AGGREGATOR = "0x18672b1b0c623a30089a280ed9256379fb0e4e62"
START_TS = 1788220800  # 2026-09-01 00:00:00 UTC


def post(payload, retries=8):
    """POST a JSON-RPC body (single or batch) and return the parsed answer, with retries."""
    body = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC_URL, data=body, headers={
                "content-type": "application/json", "user-agent": "crvusd-flush-study/0.1"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:  # network hiccup or throttle
            last = repr(e)
            time.sleep(4 * (attempt + 1))  # 429 means throttled, so back off harder
    raise RuntimeError(f"post failed: {last}")


WORKERS = 1  # more threads trigger HTTP 429 on the free plan
BATCH = 3  # the free plan refuses batches of more than 3 requests


def _run_chunks(fn, items):
    """Split items into chunks of BATCH, run fn(chunk) on a thread pool, keep the order."""
    chunks = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    with ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(fn, chunks))
    return [x for r in results for x in r]


def _post_batch(payload):
    for attempt in range(6):
        ans = post(payload)
        if isinstance(ans, list) and len(ans) == len(payload) and all("result" in a or "error" in a for a in ans):
            if not any(a.get("error", {}).get("code") in (29, 31, 35) for a in ans):  # rate or plan limits
                return ans
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"batch failed: {str(ans)[:200]}")


def batch_calls(calls):
    """calls: list of (to, data, block_int). Returns hex results, or 'ERR ...' for reverts."""
    def one(chunk):
        payload = []
        for i, c in enumerate(chunk):
            tx = {"to": c[0], "data": c[1]}
            if len(c) > 3:  # optional 4th item: the caller address
                tx["from"] = c[3]
            payload.append({"jsonrpc": "2.0", "id": i, "method": "eth_call", "params": [tx, hex(c[2])]})
        by_id = {a["id"]: a for a in _post_batch(payload)}
        return [by_id[i]["result"] if "result" in by_id[i] else "ERR " + json.dumps(by_id[i].get("error"))[:300]
                for i in range(len(chunk))]
    return _run_chunks(one, calls)


def batch_blocks(numbers):
    """Block timestamp (int) for each block number."""
    def one(chunk):
        payload = [{"jsonrpc": "2.0", "id": i, "method": "eth_getBlockByNumber",
                    "params": [hex(n), False]} for i, n in enumerate(chunk)]
        by_id = {a["id"]: a for a in _post_batch(payload)}
        return [int(by_id[i]["result"]["timestamp"], 16) for i in range(len(chunk))]
    return _run_chunks(one, numbers)

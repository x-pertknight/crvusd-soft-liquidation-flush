"""Phase 1b network access. Blockscout for logs and block numbers by time, the RPC for archive
eth_call and second-source logs. At most 2 requests per second to each source, retries on
429, 500 and timeouts. Every raw response is kept so recompute.py can work offline."""
import gzip
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "code", "raw", "phase1b")
os.makedirs(RAW, exist_ok=True)

BS_URL = "https://eth.blockscout.com/api"
RPC_URL = "https://eth.drpc.org"
UA = "crvusd-flush-study/0.1"
MIN_GAP = 0.5  # seconds between requests to one source
_last = {"bs": 0.0, "rpc": 0.0}
CAP = 1000


def _wait(src):
    d = time.time() - _last[src]
    if d < MIN_GAP:
        time.sleep(MIN_GAP - d)
    _last[src] = time.time()


def bs_get(params, tries=10):
    url = BS_URL + "?" + urllib.parse.urlencode(params)
    last = None
    for i in range(tries):
        _wait("bs")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
                return url, json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # timeout or reset
            last = repr(e)
        time.sleep(min(30, 2 * (i + 1)))
    raise RuntimeError(f"blockscout failed {last} {url}")


def rpc(method, params, tries=10):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    last = None
    for i in range(tries):
        _wait("rpc")
        try:
            req = urllib.request.Request(RPC_URL, data=body.encode(),
                                         headers={"content-type": "application/json", "user-agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read())
            if "error" in out:
                last = out["error"]
                if "revert" in str(last).lower() or "execution" in str(last).lower():
                    return body, {"error": last}
                time.sleep(min(30, 2 * (i + 1)))
                continue
            return body, out
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} {e.read()[:200]!r}"
        except Exception as e:
            last = repr(e)
        time.sleep(min(30, 2 * (i + 1)))
    raise RuntimeError(f"rpc failed {method} {last}")


def bs_logs(fb, tb, records, **flt):
    """All logs in [fb, tb] for the filter, splitting any range that returns CAP results."""
    p = {"module": "logs", "action": "getLogs", "fromBlock": fb, "toBlock": tb}
    p.update(flt)
    url, b = bs_get(p)
    res = b.get("result")
    if not isinstance(res, list):
        if b.get("message") == "No logs found" or res in (None, [], ""):
            res = []
        else:
            raise RuntimeError(f"unexpected blockscout reply {str(b)[:200]}")
    rec = {"source": url, "fromBlock": fb, "toBlock": tb, "n": len(res), "truncated": len(res) >= CAP, "response": b}
    records.append(rec)
    if len(res) >= CAP:
        if fb == tb:
            raise RuntimeError(f"single block {fb} returns {CAP} logs")
        m = (fb + tb) // 2
        return bs_logs(fb, m, records, **flt) + bs_logs(m + 1, tb, records, **flt)
    return res


def save(name, obj):
    path = os.path.join(RAW, name + ".json.gz")
    with gzip.open(path, "wt") as f:
        json.dump(obj, f, sort_keys=True)
    return path


def load(name, default=None):
    path = os.path.join(RAW, name + ".json.gz")
    if not os.path.exists(path):
        return default
    with gzip.open(path, "rt") as f:
        return json.load(f)


class State:
    """Archive eth_call cache, stored as raw hex keyed by to|data|block."""

    def __init__(self, name):
        self.name = name
        self.d = load(name, {"source": RPC_URL, "method": "eth_call", "calls": {}})

    def call(self, to, data, block):
        key = f"{to.lower()}|{data}|{block}"
        if key not in self.d["calls"]:
            _, out = rpc("eth_call", [{"to": to, "data": data}, hex(block) if isinstance(block, int) else block])
            self.d["calls"][key] = out.get("result") if "result" in out else "ERR " + str(out.get("error"))[:120]
        return self.d["calls"][key]

    def flush(self):
        save(self.name, self.d)

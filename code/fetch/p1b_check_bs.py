"""Phase 1b second source for the completeness checks (PHASE_1B_ADDENDUM_2.md): Blockscout logs of crvUSD
transfers into and out of each peg pool and TokenExchange logs of each member of S. Paced to stay inside
the Blockscout quota: on a long HTTP 429 the script waits for the reset time it is given."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import p1b_net  # noqa: E402
from p1b_net import save, load, ROOT, RAW, BS_URL, UA, CAP  # noqa: E402

TP = json.load(open(os.path.join(ROOT, "code", "topics.json")))["topics"]
MEM = json.load(open(os.path.join(RAW, "s_members.json")))["events"]
CRVUSD = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
GAP = 6.0
NOWAIT = os.environ.get("NOWAIT") == "1"  # VERIFICATION.md, phase 1b: report as not checked on HTTP 429


class Throttled(Exception):
    pass


def get(params):
    url = BS_URL + "?" + urllib.parse.urlencode(params)
    for i in range(200):
        time.sleep(GAP)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
                return url, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and NOWAIT:
                raise Throttled(url)
            reset = 30.0
            if e.code == 429:
                try:
                    reset = max(10.0, int(e.headers.get("x-ratelimit-reset", "60000")) / 1000)
                except ValueError:
                    pass
            print("http", e.code, "wait", round(min(reset, 2400)), flush=True)
            time.sleep(min(reset, 2400) + 5)
        except Exception as e:
            print("err", repr(e), flush=True)
            time.sleep(30)
    raise RuntimeError("blockscout gave up " + url)


def logs(fb, tb, rec, **flt):
    p = {"module": "logs", "action": "getLogs", "fromBlock": fb, "toBlock": tb}
    p.update(flt)
    url, b = get(p)
    res = b.get("result")
    if not isinstance(res, list):
        if b.get("message") == "No logs found" or res in (None, ""):
            res = []
        else:
            raise RuntimeError(f"unexpected reply {str(b)[:200]}")
    rec.append({"source": url, "fromBlock": fb, "toBlock": tb, "n": len(res), "truncated": len(res) >= CAP, "response": b})
    if len(res) >= CAP:
        m = (fb + tb) // 2
        logs(fb, m, rec, **flt)
        logs(m + 1, tb, rec, **flt)


def pad(a):
    return "0x" + "0" * 24 + a.lower()[2:]


def fetch_event(meta, b0, b1, rec):
    for pk in meta["pegkeepers"]:
        logs(b0, b1, rec["crvusd_to_pools"], address=CRVUSD, topic0=TP["Transfer"], topic2=pad(pk["pool"]), topic0_2_opr="and")
        logs(b0, b1, rec["crvusd_from_pools"], address=CRVUSD, topic0=TP["Transfer"], topic1=pad(pk["pool"]), topic0_1_opr="and")
    for mm in meta["members"]:
        logs(b0, b1, rec["s_swaps"], address=mm["pool"], topic0=TP["TokenExchange_twocrypto"])


for eid in sys.argv[1:] or sorted(MEM):
    if load(f"ev_{eid}_blockscout"):
        continue
    meta = load(f"ev_{eid}_done")
    if not meta:
        print(eid, "flows not fetched yet", flush=True)
        continue
    meta = meta["meta"]
    b0, b1 = meta["first_block"], meta["last_block"]
    rec = {"crvusd_to_pools": [], "crvusd_from_pools": [], "s_swaps": []}
    try:
        fetch_event(meta, b0, b1, rec)
    except Throttled as t:
        save(f"ev_{eid}_blockscout_not_checked", {"reason": "HTTP 429", "url": str(t)})
        print(eid, "not checked, HTTP 429", flush=True)
        continue
    save(f"ev_{eid}_blockscout", {"records": rec})
    print(eid, "blockscout check fetched", {k: len(v) for k, v in rec.items()}, flush=True)

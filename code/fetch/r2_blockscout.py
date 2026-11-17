"""Release 2. Transaction lists for each PegKeeper from Blockscout, failed transactions included, from
2026-09-01 to now. Two endpoints per address: /transactions (direct calls to the PegKeeper, failed ones
included) and /logs (every event the PegKeeper emitted, including calls made through other contracts).
/internal-transactions is not scanned: it lists every view call the monetary policy makes each block. Raw pages go to code/raw/r2_blockscout/<name>_<kind>.json.
Retries: at most 3 per page, with waits, as fixed in PREREG_R2_ADDENDUM.md section 4."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, START_TS, REGULATOR, AGGREGATOR  # noqa: E402

BASE = "https://eth.blockscout.com/api/v2/addresses"
OUT = os.path.join(ROOT, "code", "raw", "r2_blockscout")
os.makedirs(OUT, exist_ok=True)
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
START_ISO = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(START_TS))


def get(url):
    """One page, or None if refused after 3 retries (reported as not checked)."""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"user-agent": "crvusd-flush-study/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # 429 or network
            print("retry", attempt, repr(e)[:80], flush=True)
            time.sleep(10 * (attempt + 1))
    return None


def scan(addr, kind):
    items, params, complete = [], {}, False
    while True:
        url = f"{BASE}/{addr}/{kind}" + ("?" + urllib.parse.urlencode(params) if params else "")
        page = get(url)
        if page is None:
            return items, False, "refused after 3 retries"
        items += page["items"]
        last = page["items"][-1] if page["items"] else {}
        oldest = last.get("timestamp") or last.get("block_timestamp") or "0"
        nxt = page.get("next_page_params")
        if not nxt or oldest < START_ISO:
            return items, True, ""
        params = nxt
        time.sleep(0.5)


status = {}
targets = [(p["name"], p["pegkeeper"], ("transactions", "logs")) for p in C["pegkeepers"]]
# Regulator and aggregator: events only (parameter changes, pause flags, pool list changes)
targets += [("Regulator", REGULATOR, ("logs",)), ("Aggregator", AGGREGATOR, ("logs",))]
for name, addr, kinds in targets:
    for kind in kinds:
        items, ok, why = scan(addr, kind)
        json.dump({"complete": ok, "note": why, "items": items},
                  open(os.path.join(OUT, f"{name}_{kind}.json"), "w"))
        status[f"{name}_{kind}"] = [len(items), ok, why]
        print(name, kind, len(items), ok, why, flush=True)
json.dump(status, open(os.path.join(OUT, "status.json"), "w"), indent=1)

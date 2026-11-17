"""Release 2. Curve prices API: PegKeeper list, per-PegKeeper event history (with debt after each event) and the
crvUSD USD price, each saved raw with the time it was fetched. Writes code/raw/r2_api/."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT  # noqa: E402

BASE = "https://prices.curve.finance"
OUT = os.path.join(ROOT, "code", "raw", "r2_api")
os.makedirs(OUT, exist_ok=True)
C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))


def get(path):
    req = urllib.request.Request(BASE + path, headers={"user-agent": "crvusd-flush-study/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {"fetched_at": int(time.time()), "path": path, "body": json.loads(r.read())}


def save(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), "w"))


save("pegkeepers.json", get("/v1/crvusd/pegkeepers/ethereum"))
save("usd_price.json", get("/v1/usd_price/ethereum/0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E"))
START_TS = 1788220800  # 2026-09-01 00:00 UTC
for p in C["pegkeepers"]:
    events, page = [], 1
    while True:  # 10 events per page, newest first; stop when a page reaches before the window
        ans = get(f"/v1/crvusd/pegkeepers/ethereum/{p['pegkeeper']}?page={page}")
        ev = ans["body"]["events"]
        events += ev
        if not ev or ev[-1]["timestamp"] < START_TS - 86400 * 7 or page > 80:
            break
        page += 1
    save(f"events_{p['name']}.json", {"fetched_at": ans["fetched_at"], "pages": page, "events": events})
    print(p["name"], len(events), "pages", page, "oldest", events[-1]["timestamp"] if events else None, flush=True)

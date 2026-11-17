"""Release 2 window check (addendum 2): how long does a withdrawal opening last?
For ten USDT Withdraw events (every sixth of those from 23 to 29 October) read every block from 20 before to 10
after the event block: both pool balances and a simulated update() from a dummy caller (one worker, batches of 3).
Writes code/raw/r2_windows.json, keyed 'event_block:block'."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, batch_calls, selector, enc_addr  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PK = next(p for p in (C["pegkeepers"].values() if isinstance(C["pegkeepers"], dict) else C["pegkeepers"])
          if p["name"] == "USDT")
BAL, UPD = selector("balances(uint256)"), selector("update(address)")
DUMMY = "0x000000000000000000000000000000000000dead"
OUT = os.path.join(ROOT, "code", "raw", "r2_windows.json")
BEFORE, AFTER = 20, 10


def pick_events():
    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "data", "r2_events.csv")))
            if r["pegkeeper"] == "USDT" and r["type"] == "Withdraw" and 1792713600 <= int(r["ts"]) < 1793318400]
    blocks = sorted({int(r["block"]) for r in rows})
    return blocks[3::6][:10]


def main():
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for eb in pick_events():
        for b in range(eb - BEFORE, eb + AFTER + 1):
            key = f"{eb}:{b}"
            if key in done:
                continue
            done[key] = batch_calls([(PK["pool"], BAL + "0" * 64, b), (PK["pool"], BAL + "0" * 63 + "1", b),
                                     (PK["pegkeeper"], UPD + enc_addr(DUMMY), b, DUMMY)])
        json.dump(done, open(OUT, "w"))
        print("event", eb, "total", len(done), flush=True)


if __name__ == "__main__":
    main()

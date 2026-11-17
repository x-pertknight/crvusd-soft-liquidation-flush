"""Release 2 addendum 2: did worst_price_threshold bind? At every sampled hour with aggregator price at or above 1,
read price_oracle() of all five pools (the Regulator compares these). Writes code/raw/r2_wpt.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, batch_calls, selector  # noqa: E402

C = json.load(open(os.path.join(ROOT, "code", "contracts.json")))
PKS = C["pegkeepers"]
G = json.load(open(os.path.join(ROOT, "code", "raw", "r2_hour_blocks.json")))["hours"]
T1 = json.load(open(os.path.join(ROOT, "code", "raw", "r2_series", "tier1.json")))
OUT = os.path.join(ROOT, "code", "raw", "r2_wpt.json")


def oracle_call(p, b):
    if p["include_index"]:
        return (p["pool"], selector("price_oracle(uint256)") + "0" * 64, b)
    return (p["pool"], selector("price_oracle()"), b)


def main():
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    blocks = [b for _, b, _ in G if int(T1[str(b)][5], 16) >= 10 ** 18]
    for i in range(0, len(blocks), 6):
        part = [b for b in blocks[i:i + 6] if str(b) not in done]
        if not part:
            continue
        res = batch_calls([oracle_call(p, b) for b in part for p in PKS])
        for j, b in enumerate(part):
            done[str(b)] = res[j * 5:(j + 1) * 5]
        json.dump(done, open(OUT, "w"))
        print("wpt", len(done), flush=True)


def exceptions():
    """Aggregator price() at the event block itself, for every Provide with price below 1 and every Withdraw with
    price above 1 at the block before. Writes code/raw/r2_price_exceptions.json (key 'block')."""
    path = os.path.join(ROOT, "code", "raw", "r2_price_exceptions.json")
    done = json.load(open(path)) if os.path.exists(path) else {}
    agg = "0x18672b1b0c623a30089a280ed9256379fb0e4e62"
    todo = []
    for e in json.load(open(os.path.join(ROOT, "code", "raw", "r2_extra.json")))["events"]:
        pr = int(e["reads"][0], 16)
        if (e["type"] == "Provide" and pr < 10 ** 18) or (e["type"] == "Withdraw" and pr > 10 ** 18):
            if str(e["block"]) not in done and e["block"] not in todo:
                todo.append(e["block"])
    for i in range(0, len(todo), 6):
        part = todo[i:i + 6]
        for b, r in zip(part, batch_calls([(agg, selector("price()"), b) for b in part])):
            done[str(b)] = r
        json.dump(done, open(path, "w"))
    print("exceptions", len(done), flush=True)


if __name__ == "__main__":
    main()
    exceptions()

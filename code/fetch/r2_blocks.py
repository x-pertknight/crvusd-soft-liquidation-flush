"""Release 2. Sample blocks every 300 blocks (about one hour) back from the latest block to 2026-09-01.
Deviation from PREREG_R2_ADDENDUM.md section 3 ("first block at or after each hour"): the free RPC is too slow
for the exact search, so samples sit on a fixed 300 block grid and each keeps its own timestamp.
Writes code/raw/r2_hour_blocks.json as {"head": [block, ts], "hours": [[block_ts, block, block_ts], ...]},
oldest first."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from r2_common import ROOT, START_TS, batch_blocks, rpc  # noqa: E402

STEP = 300
head = int(rpc("eth_blockNumber", []), 16)
head_ts = batch_blocks([head])[0]
n = (head_ts - START_TS) // (STEP * 12) + 1  # grid points that reach back to the start date
blocks = [head - STEP * k for k in range(n, -1, -1)]
stamps = batch_blocks(blocks)
rows = [[t, b, t] for b, t in zip(blocks, stamps) if t >= START_TS - 3600]
out = {"head": [head, head_ts], "step": STEP, "hours": rows}
json.dump(out, open(os.path.join(ROOT, "code", "raw", "r2_hour_blocks.json"), "w"))
gaps = [rows[i + 1][0] - rows[i][0] for i in range(len(rows) - 1)]
print("hours", len(rows), "first", rows[0], "last", rows[-1], "gap min/max", min(gaps), max(gaps))

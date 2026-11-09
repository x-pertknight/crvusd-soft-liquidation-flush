"""Context only, outside the pre-registered measures: crvUSD aggregator price() sampled every
1,800 blocks (about 6 hours) over the 30 days before the window, by archive eth_call, on the
same blocks as fetch_context.py."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from rpc import call, selector  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGG = json.load(open(os.path.join(ROOT, "code", "topics.json")))["aggregator"]
ctx = json.load(open(os.path.join(ROOT, "code", "raw", "context_pegkeepers_30d.json")))
blocks = sorted(int(b) for b in ctx["block_timestamps"])
out = {"aggregator": AGG, "price": {str(b): call(AGG, selector("price()"), b) for b in blocks}}
json.dump(out, open(os.path.join(ROOT, "code", "raw", "context_aggregator_30d.json"), "w"))
print("written", len(blocks))

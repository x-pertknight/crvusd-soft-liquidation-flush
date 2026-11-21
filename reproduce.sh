#!/usr/bin/env bash
# Recompute every number offline from code/raw/, check the outputs against the pinned hashes, run the tests.
# Standard library only. Exits non-zero on any failed check, hash mismatch or failed test.
set -euo pipefail
cd "$(dirname "$0")"

# 1. The committed outputs must match the pins before anything is rewritten (the recompute overwrites data/).
python3 -I - <<'PY'
import hashlib, sys
bad = []
for pins in ("data/SHA256SUMS", "data/R2_SHA256SUMS"):
    for line in open(pins):
        digest, name = line.split()
        if hashlib.sha256(open("data/" + name, "rb").read()).hexdigest() != digest:
            bad.append(name)
print("committed outputs match the pinned hashes" if not bad else "FAIL committed outputs differ: " + ", ".join(bad))
sys.exit(1 if bad else 0)
PY

# 2. Recompute from raw; each script checks its rewritten outputs against the same pins.
SKIP_CHARTS=1 python3 -I code/recompute.py
python3 -I code/recompute_r2.py

# 3. Tests of the flow accounting and of the published outputs.
python3 -I -m unittest discover -s tests -v

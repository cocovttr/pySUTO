"""
init_crude_ore_feed.py
======================
Initialise the crude ore extraction DataFeed end-to-end.

This script is a thin driver.  All pipeline logic lives in feedpipe.py.

Steps (mirroring feedpipe.py)
------------------------------
A  Read metadata sidecar → DataFeedMetadata
B  Load raw data + concordance tables
C  Build ConcordanceTable → WeightMatrix          (via feedpipe step_B/C)
D  Build F_src vector + propagate uncertainty     (via feedpipe step_D)
E  Register + persist everything                  (via feedpipe.register_feed)
F  Diagnostics

═══════════════════════════════════════════════════════════
USER CONFIGURATION  ←  only section you ever edit
═══════════════════════════════════════════════════════════

INPUT (you provide these files):

  data/input/feed/<FEED_ID>/v<VERSION>/
      values.csv          ← copper crude ore extraction (from crude_ore_parse_feed.py)
      conc.xlsx           ← concordance mapping workbook
      meta.xlsx           ← pedigree / provenance sidecar

  data/proc/acc/<ACC_ID>/  ← accounting structure built by init_copper_acc.py

OUTPUT (written automatically via DataFeedRegistry):

  data/proc/
    registry/
      registry.json          ← master index across all feeds × versions
    feed/
      crude_ore/
        metadata.json        ← DataFeedMetadata (human-readable)
        crude_ore.pkl        ← WeightMatrix pickle
        result.npz           ← F_root, sigma_root, cv_root, cv_src
    diagnostics/
      crude_ore_v<VERSION>_feed.png

  logs/
      crude_ore_v<VERSION>_<timestamp>.log  ← full run log
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# USER CONFIGURATION
# ---------------------------------------------------------------------------
# The feed's policy (loaders, concordance tables, ROW region) is the copper case's
# CRUDE_ORE_FEED, pysuto.cases.copper; the acc id is config/config.yaml's
# pipeline.acc_id, read inside main().

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pysuto.cases.copper import CRUDE_ORE_FEED
from pysuto.feedpipe import run_feed
from pysuto.registry import stage_lock

FEED_ID = CRUDE_ORE_FEED.feed_id


def main() -> None:
    run_log = os.path.join("logs", f"{FEED_ID}_{datetime.now():%Y%m%d_%H%M%S}.log")
    run_feed(CRUDE_ORE_FEED, run_log=run_log)


if __name__ == "__main__":
    with stage_lock("crude_ore_feed"):   # registries have no locking (#101)
        main()

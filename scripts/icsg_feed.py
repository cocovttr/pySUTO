"""
init_icsg_feed.py
=================
Initialise the ICSG copper-flow DataFeed end-to-end.

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
      values.csv          ← raw flow data
      conc.xlsx           ← concordance mapping workbook
      meta.xlsx           ← pedigree / provenance sidecar

  data/proc/acc/<ACC_ID>/  ← accounting structure built by init_acc.py

OUTPUT (written automatically via DataFeedRegistry):

  data/proc/
    registry/
      registry.json          ← master index across all feeds × versions
    feed/
      icsg/
        metadata.json        ← DataFeedMetadata (human-readable)
        icsg.pkl             ← WeightMatrix pickle
        result.npz           ← F_root, sigma_root, cv_root, cv_src, observed_zero (#76)
    diagnostics/
      icsg_v<VERSION>_diagnostics.png
"""

from __future__ import annotations

import dataclasses
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# USER CONFIGURATION
# ---------------------------------------------------------------------------

FEED_ID = "icsg"

# #76: a weighted fan's domestic leg at trade-share weight 0 is an observed zero,
# covered at 0 with the net-stock seed's pricing (ADR 0040) on the usage U its fans
# distribute: σ = max(OBSERVED_ZERO_CV·|U|, OBSERVED_ZERO_FLOOR_KT). Mirrors
# collect_aggregate_impute's STOCK_SEED_CV / STOCK_SEED_ABS_FLOOR_KT: change both or
# neither.
OBSERVED_ZERO_CV       = 0.01
OBSERVED_ZERO_FLOOR_KT = 0.3
# The signed stock legs: their zero-weight domestic leg is a supply-mix share
# (ADR 0043) whose zero the net-stock seed prices (ADR 0040), not an observed zero.
STOCK_SECTORS_TO       = ("MESC", "USC")
# The products whose zero-weight domestic leg is an observed zero in a region that makes
# none of them, by its raw ICSG production (ADR 0024's bound): concentrate (#78) and
# cathode (#96). Anode is not stamped.
# #96's Cathode legs and the MF→Concentrate output zeros were measured and rejected (z² +37.8 %,
# opt_20261021_105350_b1fea245; ADR 0024 am.): they expose ICSG-usage gaps a zero cannot close.
OBSERVED_ZERO_SECTORS  = ("Concentrate",)
# The edges a region's own mine and SX-EW output leave on, as (process, product): the
# edges this feed books ICSG's Mining/Concentrate and SXEW/Cathode supply rows on. Where
# the region makes none of the product, the edge is an observed zero (#97, #31).
PRODUCTION_EDGES       = (("SXEW", "CSXEW"),)
# Regions whose zero is never a report: ROW is the sum of the members ICSG lists, with
# its "Others" rows among them.
AGGREGATE_REGIONS      = ("ROW",)
# Other registered inputs that report a mine or an SX-EW plant: where one does, ICSG's
# missing row is missing data (a small producer under "Others"), and the output edge is
# not stamped (ADR 0019). The crude-ore feed reports mining wherever its ore mass is
# > 0; an ore-grade row reports the product its from-sector names, by region-year.
CRUDE_ORE_ID           = "crude_ore"
ORE_GRADE_ID           = "ore_grade"
ORE_GRADE_ACTIVITY     = {"CO": "Concentrate", "SXEW": "CSXEW"}

sys.path.insert(0, os.path.dirname(__file__))

from pysuto.cases.copper import ICSG_FEED
from pysuto.conc     import ConcordanceTable
from pysuto.registry import stage_lock
from pysuto.input_registry import InputRegistries
from pysuto.feedpipe import run_feed
from build_baci_reexport import AGGREGATES_ID, icsg_aggregate_members
from build_trade_shares import _decoded_edges, check_parents, icsg_raw_production

# ACC_ID is config/config.yaml's pipeline.acc_id, read inside main() by run_feed.


def observed_zero_sigma(legs: pd.DataFrame, F_src: np.ndarray,
                        sigma_root: np.ndarray) -> np.ndarray:
    """σ of every observed zero, NaN on every other root edge (#76).

    ``legs`` lists the zero-weight domestic legs (``src_id``, ``edge_id``) of
    ``ConcordanceTable.zero_weight_domestic_legs``. Each edge is priced on the
    usage its fans distribute, ``U = Σ |F_src[src_id]|``: an aggregate region
    (ROW) fans each member country's row onto the same legs. A leg another fan
    feeds (``sigma_root > 0``) is a flow, not an observed zero.
    """
    edge = legs["edge_id"].to_numpy()
    usage = np.zeros(len(sigma_root))
    np.add.at(usage, edge, np.abs(F_src[legs["src_id"].to_numpy()]))
    out = np.full(len(sigma_root), np.nan)
    out[edge] = np.maximum(OBSERVED_ZERO_CV * usage[edge], OBSERVED_ZERO_FLOOR_KT)
    out[sigma_root > 0] = np.nan
    return out


def icsg_coverage(raw_df: pd.DataFrame, region_map_df: pd.DataFrame, years,
                  aggregate_of: dict) -> set[tuple[str, str]]:
    """The ``(region, year)`` pairs ICSG covers, where a missing production is a 0 (#97).

    A region is covered when any ICSG row maps to it, in any table and any year. ICSG's
    mine, smelter, refinery and SX-EW tables list every producing country by name, the
    small ones under "Others", so a region ICSG lists anywhere and not in a table that
    year produces none of that table's product. Years without any ICSG row for the region
    count too: Mauritania before 2006, Panama before 2019 and Botswana in 2019–20 had no
    mine. Not covered: ``AGGREGATE_REGIONS``, whose production is a sum of members; a root
    region no row maps to (Luxembourg, reported jointly with Belgium); and a region-year
    ICSG reports inside one of its own aggregate rows, ``aggregate_of``
    (``build_baci_reexport.icsg_aggregate_members``), a reporting gap (#67).
    """
    root = raw_df["Region"].map(dict(zip(region_map_df["src_region"],
                                         region_map_df["root_region"])))
    regions = set(root.dropna()) - set(AGGREGATE_REGIONS)
    return {(r, str(t)) for r in regions for t in years} - set(aggregate_of)


def reported_elsewhere(crude_ore_df: pd.DataFrame, crude_ore_region_map: pd.DataFrame,
                       ore_grade_df: pd.DataFrame) -> set[tuple[str, str, str]]:
    """``(product, region, year)`` where another registered input reports the output (#97).

    Mining (``Concentrate``) wherever the crude-ore feed's ore mass is > 0, and wherever
    an ore-grade row starts at ``CO``; SX-EW (``CSXEW``) wherever one starts at
    ``SXEW`` (``ORE_GRADE_ACTIVITY``). There ICSG's missing row is a gap, and a zero
    stamped on it would contradict that input (ADR 0019).
    """
    region = crude_ore_df["Region"].map(dict(zip(crude_ore_region_map["src_region"],
                                                 crude_ore_region_map["root_region"])))
    ore = crude_ore_df.assign(region=region, year=crude_ore_df["Year"].astype(str))
    ore = ore.groupby(["region", "year"])["Value"].sum()
    out = {("Concentrate", r, y) for (r, y), v in ore.items() if v > 0}
    rows = ore_grade_df[ore_grade_df["a_sector_from"].isin(list(ORE_GRADE_ACTIVITY))]
    out |= set(zip(rows["a_sector_from"].map(ORE_GRADE_ACTIVITY), rows["a_region_from"],
                   rows["a_time"].astype(str)))
    return out


def raw_production(edges: pd.DataFrame) -> pd.DataFrame:
    """Raw ICSG production, CC, of every product the observed zeros test (#96, #97).

    ``build_trade_shares.icsg_raw_production`` reads it by ADR 0027's definitions, the
    ADR 0024 bound's own (cathode = refined + SX-EW, CSXEW = SX-EW supply), with an
    explicit 0 for every product in every region-year of ``edges``, so a row never
    depends on which edges the frame holds. Keyed ``root_sector_from`` = product.
    """
    products = sorted(set(OBSERVED_ZERO_SECTORS) | {p for _, p in PRODUCTION_EDGES})
    region_years = edges[["root_region_to", "root_time"]].drop_duplicates()
    grid = pd.concat([region_years.assign(root_sector_from=p) for p in products],
                     ignore_index=True)
    return icsg_raw_production(products, grid)


def _produces_none(product, region, time, production: pd.DataFrame,
                   covered: set) -> np.ndarray:
    """True where a covered region-year's ICSG production of ``product`` is 0.

    "A non-producer must say zero, not nothing" (ADR 0024). A missing production row is 0.
    """
    p = production.set_index(["root_sector_from", "root_region_to",
                              "root_time"])["production_cc"]
    key = pd.MultiIndex.from_arrays([np.asarray(product), np.asarray(region),
                                     np.asarray(time)])
    own = p.reindex(key).fillna(0.0).to_numpy()
    seen = pd.MultiIndex.from_arrays([np.asarray(region), np.asarray(time)]).isin(covered)
    return seen & (own == 0.0)


def non_producer_mask(edges: pd.DataFrame, production: pd.DataFrame, covered: set,
                      n_edges: int) -> np.ndarray:
    """Per root edge: True where a fan's zero-weight domestic leg may be an observed zero.

    The edge carries a product in ``OBSERVED_ZERO_SECTORS`` into a covered region-year
    that produces none of it (#78, #96). A zero-weight domestic leg anywhere else stays
    open to the imputer: in a producer it is the fan's residual where imports exceed
    usage, not an observation.

    ``edges``: ``edge_id, root_sector_from, root_region_to, root_time``; ``production``:
    ``raw_production``; ``covered``: ``icsg_coverage``.
    """
    none = _produces_none(edges["root_sector_from"], edges["root_region_to"],
                          edges["root_time"], production, covered)
    mask = np.zeros(n_edges, dtype=bool)
    mask[edges["edge_id"].to_numpy()] = (edges["root_sector_from"]
                                         .isin(OBSERVED_ZERO_SECTORS).to_numpy() & none)
    return mask


def production_zero_mask(edges: pd.DataFrame, production: pd.DataFrame, covered: set,
                         n_edges: int, elsewhere: set) -> np.ndarray:
    """Per root edge: True on a covered non-producer's mine or SX-EW output (#97, #31).

    The edge is a ``PRODUCTION_EDGES`` pair in CC, the valuation ICSG reports, in a
    covered region-year that produces none of the product, and no other input reports
    that output there (``elsewhere``, from ``reported_elsewhere``). Only the output edge is
    stamped; hard rows carry the zero up the chain. The efficiency bands (output ≥
    eff_min · input) hold Ore→MF and Ore→SXEW at the output's zero, and the mass
    balances follow: MF's and SXEW's own leave their tailings nothing, the Ore node's
    takes Mining→Ore, Mining's takes CO→Mining, and CSXEW's takes CSXEW→CP. The conc
    relations take the Mass twins. Stamping any of these edges as well would price the
    same zero twice.

    ``edges``: ``edge_id, root_sector_from, root_sector_to, root_region_to, root_time,
    valuation``; ``production``: ``raw_production``; ``covered``: ``icsg_coverage``.
    """
    pair = pd.MultiIndex.from_frame(edges[["root_sector_from", "root_sector_to"]])
    out = edges[pair.isin(PRODUCTION_EDGES) & (edges["valuation"] == "CC").to_numpy()]
    key = [out["root_sector_to"], out["root_region_to"], out["root_time"]]
    mask = np.zeros(n_edges, dtype=bool)
    mask[out["edge_id"].to_numpy()] = (
        _produces_none(*key, production, covered)
        & ~pd.MultiIndex.from_arrays([k.to_numpy() for k in key]).isin(elsewhere))
    return mask


def stamp_observed_zeros(ct: ConcordanceTable, F_src: np.ndarray, result,
                         non_producer: np.ndarray, production_zero: np.ndarray) -> int:
    """Mark the feed's observed zeros on ``result`` and give them their σ (#76–#97).

    Two kinds: the zero-weight domestic legs ``non_producer`` allows, priced on their fans'
    usage (``observed_zero_sigma``), and the output edges ``production_zero`` marks. No fan
    distributes usage onto an output edge, so #78's rule leaves it the floor,
    ``OBSERVED_ZERO_FLOOR_KT``, the resolution ICSG reports at (ADR 0025). An edge the
    feed fills (``sigma_root > 0``) is a flow, never an observed zero. Sets
    ``result.observed_zero`` and overwrites ``result.sigma_root`` there, after
    propagation, so no per-edge CV multiplier reaches them. Returns their count.
    """
    legs = ct.zero_weight_domestic_legs(STOCK_SECTORS_TO)
    legs = legs[non_producer[legs["edge_id"].to_numpy()]]
    sigma0 = observed_zero_sigma(legs, F_src, result.sigma_root)
    sigma0[production_zero & ~(result.sigma_root > 0)] = OBSERVED_ZERO_FLOOR_KT
    result.observed_zero = ~np.isnan(sigma0)
    result.sigma_root[result.observed_zero] = sigma0[result.observed_zero]
    return int(result.observed_zero.sum())



# Params id holding the BACI-trade-share producer weights (ADR 0002 option D).
TRADE_SHARES_ID = "trade_shares"


def load_trade_shares(inputs: InputRegistries):
    """Load the optional BACI-trade-share weights as user_weights_df.

    Returns (df, entry) or (None, None) when the artifact is not registered, so
    the ICSG build falls back to the uniform producer fan (unchanged behaviour).
    Raises ValueError when the weights were built from another BACI feed run or
    other input versions than those in force (#53). Run
    scripts/build_trade_shares.py to (re)generate it.
    """
    if TRADE_SHARES_ID not in inputs.params.ids():
        print(f"   trade_shares : not registered — uniform fan")
        return None, None
    version_dir = inputs.params.resolve(TRADE_SHARES_ID)
    check_parents(version_dir, inputs)
    df = pd.read_csv(version_dir / "params.csv")
    entry = inputs.params.entry(TRADE_SHARES_ID)
    print(f"   trade_shares : {TRADE_SHARES_ID} v{entry['version']} "
          f"(code={entry['code']}, {len(df):,} weight rows)")
    return df, entry


def _trade_share_weights(build):
    """``FeedSpec.user_weights``: the BACI-trade-share weights and, when registered, the
    input entry they are recorded under in the run's parents."""
    df, entry = load_trade_shares(build.inputs)
    return df, ({} if entry is None else {TRADE_SHARES_ID: entry})


def _stamp_feed_observed_zeros(build) -> None:
    """``FeedSpec.post_propagate``: the observed zeros (#76–#97), after propagation."""
    acc, raw_df, tables = build.acc, build.raw_df, build.tables
    ct, F_src, result, input_ref = build.ct, build.F_src, build.result, build.input_ref
    edges      = _decoded_edges(acc)
    reader     = InputRegistries.load(root=build.input_root)
    ore_dir    = reader.feed.resolve(CRUDE_ORE_ID)
    input_ref[AGGREGATES_ID] = reader.params.entry(AGGREGATES_ID)
    input_ref[CRUDE_ORE_ID]  = reader.feed.entry(CRUDE_ORE_ID)
    input_ref[ORE_GRADE_ID]  = reader.params.entry(ORE_GRADE_ID)
    covered    = icsg_coverage(
        raw_df, tables["region_map"], sorted(edges["root_time"].unique()),
        icsg_aggregate_members(reader.params.resolve(AGGREGATES_ID) / "params.csv"))
    elsewhere  = reported_elsewhere(
        pd.read_csv(ore_dir / "values.csv"),
        pd.read_excel(ore_dir / "conc.xlsx", sheet_name="region_map"),
        pd.read_csv(reader.params.resolve(ORE_GRADE_ID) / "params.csv",
                    sep=None, engine="python", dtype=str))
    production = raw_production(edges)
    non_producer    = non_producer_mask(edges, production, covered, len(result.F_root))
    production_zero = production_zero_mask(edges, production, covered, len(result.F_root),
                                           elsewhere)
    n_zero = stamp_observed_zeros(ct, F_src, result, non_producer, production_zero)
    n_out  = int((result.observed_zero & production_zero).sum())
    print(f"   observed zeros: {n_zero:,} in region-years ICSG covers that produce none of "
          f"the product: {n_zero - n_out:,} domestic legs at trade-share weight 0 (#76, "
          f"#78, #96), {n_out:,} mine and SX-EW output edges (#97, #31)")


# The copper ICSG feed (pysuto.cases.copper.ICSG_FEED) with the two hooks that need this
# script's helpers: build_trade_shares and build_baci_reexport are scripts.
SPEC = dataclasses.replace(ICSG_FEED, user_weights=_trade_share_weights,
                           post_propagate=_stamp_feed_observed_zeros)


def main() -> None:
    run_log = os.path.join("logs", f"{FEED_ID}_{datetime.now():%Y%m%d_%H%M%S}.log")
    run_feed(SPEC, run_log=run_log)


if __name__ == "__main__":
    with stage_lock("icsg_feed"):   # registries have no locking (#101)
        main()

"""
test_trade_edges.py
===================
Trade edges ``f(r) → f(s)`` between the flow nodes of two regions (ADR 0048): declared by
an Accounting pair ``Flow → Flow``, built for every tradable flow and ordered region pair,
balanced at both ends, classified as PSUT block ``T``, and traced to the producers by the
market-share PIOT.
"""

from __future__ import annotations

import copy
import os
import sys

import numpy as np
import pandas as pd
import pytest

from pysuto.acc import AccountingStructure
from pysuto.relation.balance import node_balance_relations

sys.path.insert(0, os.path.dirname(__file__))
from test_psut import ROLE_OF_SUB  # noqa: E402


# A regional pool per flow: Mining supplies Ore, Ore is traded between the pools, Smelting
# uses its own region's Ore and supplies Metal, Metal is traded and goes to final use.
SPEC = {
    "sectors": [
        {"name": "Mining",   "entity": "Process"},
        {"name": "Ore",      "entity": "Flow"},
        {"name": "Smelting", "entity": "Process"},
        {"name": "Metal",    "entity": "Flow"},
        {"name": "Slag",     "entity": "SB",      "role": "secondary"},
        {"name": "FU",       "entity": "SB",      "role": "final_demand"},
    ],
    "regions":    ["Montara", "Portua", "Isla"],
    "valuations": [{"name": "Mass", "role": "gross"}, {"name": "CC", "role": "content"}],
    "times":      ["2001"],
    "supply":     {"Mining": ["Ore"], "Smelting": ["Metal", "Slag"]},
    "use":        {"Ore": ["Smelting"], "Metal": ["FU"]},
    "tradable":   ["Ore", "Metal"],
    "accounting": [
        {"from": "Process", "to": "Flow",    "same_region": True},
        {"from": "Process", "to": "SB",      "same_region": True},
        {"from": "Flow",    "to": "Process", "same_region": True},
        {"from": "Flow",    "to": "SB",      "same_region": True},
        {"from": "Flow",    "to": "Flow",    "same_region": False},
    ],
}


@pytest.fixture(scope="module")
def acc():
    return AccountingStructure.from_spec(copy.deepcopy(SPEC), "trade")


def _pairs(acc, mask=None):
    em = acc.edge_meta if mask is None else acc.edge_meta[mask]
    em = em[em["valuation"] == "Mass"]
    return list(zip(em["from_sector"], em["from_region"], em["to_sector"], em["to_region"]))


def test_a_trade_edge_joins_two_regions_of_one_tradable_flow(acc):
    trade = _pairs(acc, acc.masks["trade"])
    assert len(trade) == 2 * 3 * 2                    # 2 tradable flows × 3 × 2 region pairs
    assert all(f == t and rf != rt for f, rf, t, rt in trade)
    assert set(f for f, _, _, _ in trade) == {"Ore", "Metal"}


def test_with_trade_edges_every_other_edge_stays_in_its_region(acc):
    other = _pairs(acc, ~acc.masks["trade"])
    assert all(rf == rt for _, rf, _, rt in other)
    assert np.array_equal(acc.masks["cross_region"], acc.masks["trade"])
    # 3 supply pairs + 2 use pairs, 3 regions each; 12 trade edges; × 2 valuations
    assert acc.n_edges == (5 * 3 + 12) * 2


def test_the_vectorised_build_admits_what_the_per_pair_predicates_admit(acc):
    keys  = list(acc.id_to_node.values())
    nodes = [dict(zip(["sector", "entity", "region"], k)) for k in keys]
    expected = [(i, j) for i, ni in enumerate(nodes) for j, nj in enumerate(nodes)
                if acc._edge_admissible(ni, nj, "2001", "Mass")]
    em = acc.edge_meta[acc.edge_meta["valuation"] == "Mass"]
    assert list(zip(em["from_id"], em["to_id"])) == expected


def test_without_the_flow_to_flow_pair_the_structure_is_unchanged():
    spec = copy.deepcopy(SPEC)
    spec["accounting"] = [r for r in spec["accounting"] if (r["from"], r["to"]) != ("Flow", "Flow")]
    acc = AccountingStructure.from_spec(spec, "no_trade")
    assert acc.ruleset.trade_pairs == set()
    assert not acc.masks["trade"].any() and not acc.masks["cross_region"].any()
    assert acc.n_edges == 5 * 3 * 2


def test_a_flow_node_balances_its_trade_in_and_out(acc):
    rels = {(r.meta["sector"], r.meta["region"]): r
            for r in node_balance_relations(acc, "Mass") if r.meta["entity"] == "Flow"}
    em = acc.edge_meta.set_index("edge_id")
    rel = rels[("Metal", "Portua")]
    inc = em.loc[rel.edges[rel.coefficients > 0]]
    out = em.loc[rel.edges[rel.coefficients < 0]]
    assert sorted(zip(inc["from_sector"], inc["from_region"])) == [
        ("Metal", "Isla"), ("Metal", "Montara"), ("Smelting", "Portua")]
    assert sorted(zip(out["to_sector"], out["to_region"])) == [
        ("FU", "Portua"), ("Metal", "Isla"), ("Metal", "Montara")]


def test_flow_node_balance_counts_trade_in_as_inflow(acc):
    from pysuto.flow_node_balance import flow_node_balance

    class _Agg:                                      # the one attribute it reads
        pass

    em = acc.edge_meta
    f = np.zeros(acc.n_edges)
    f[((em["from_sector"] == "Smelting") & (em["to_sector"] == "Metal")
       & (em["from_region"] == "Montara")).to_numpy()] = 10.0
    f[((em["from_sector"] == "Metal") & (em["to_sector"] == "Metal")
       & (em["from_region"] == "Montara") & (em["to_region"] == "Portua")).to_numpy()] = 6.0
    agg = _Agg()
    agg.f_agg = f
    bal = flow_node_balance(acc, agg, valuation="CC").set_index(["sector", "region"])
    assert bal.loc[("Metal", "Portua"), "inflow"] == 6.0
    assert bal.loc[("Metal", "Montara"), ("inflow", "outflow")].tolist() == [10.0, 6.0]


def test_trade_edges_are_psut_block_t(acc):
    from pysuto.psut import classify_blocks
    block = classify_blocks(acc.edge_meta, acc.boundary_roles)
    assert block.notna().all()
    assert np.array_equal((block == "T").to_numpy(), acc.masks["trade"])


def _hand_psut(rows, nodes):
    from pysuto.psut import PSUT
    table = pd.DataFrame(rows, columns=["period", "valuation", "block", "edge_id",
                                        "from_region", "from_sector", "from_entity",
                                        "to_region", "to_sector", "to_entity", "val"])
    nodes = pd.DataFrame(nodes, columns=["sector", "entity", "region", "entity_sub"])
    nodes["role"] = nodes["entity_sub"].map(ROLE_OF_SUB)
    return PSUT(table, nodes, valuations=["CC"], primary="CC", acc_id="hand")


def test_the_piot_traces_traded_goods_to_their_producers():
    # A smelts 10 and sends 6 to B; B smelts 2; B's 8 go to final use, A keeps 4.
    rows = [
        ("2001", "CC", "S", 0, "A", "Smelting", "Process", "A", "Metal",    "Flow",    10.0),
        ("2001", "CC", "S", 1, "B", "Smelting", "Process", "B", "Metal",    "Flow",     2.0),
        ("2001", "CC", "T", 2, "A", "Metal",    "Flow",    "B", "Metal",    "Flow",     6.0),
        ("2001", "CC", "Y", 3, "A", "Metal",    "Flow",    "A", "FU",       "SB",       4.0),
        ("2001", "CC", "Y", 4, "B", "Metal",    "Flow",    "B", "FU",       "SB",       8.0),
    ]
    nodes = [("Smelting", "Process", r, None) for r in "AB"] + \
            [("Metal", "Flow", r, None) for r in "AB"] + [("FU", "SB", r, "FD") for r in "AB"]
    piot = _hand_psut(rows, nodes).to_piot("market_share", level="Z")
    D = piot.shares.set_index(["region", "commodity_region"])["share"]
    assert D[("A", "A")] == pytest.approx(1.0)
    assert D[("A", "B")] == pytest.approx(0.75)       # 6 of B's 8 come from A
    assert D[("B", "B")] == pytest.approx(0.25)
    y = piot.table[piot.table["block"] == "Y"].groupby(["from_region", "to_region"])["val"].sum()
    assert y.to_dict() == pytest.approx({("A", "A"): 4.0, ("A", "B"): 6.0, ("B", "B"): 2.0})
    assert "T" not in set(piot.table["block"])        # no process-network edge of its own

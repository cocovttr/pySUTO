"""
test_acc_vectorised.py
======================
The RuleSet path builds its node mask, tensor and edge index from the rule pairs, not
from a loop over every node pair. Here the vectorised build is checked against the loop
it replaces — the per-pair predicates ``_node_pair_admissible`` and ``_edge_admissible``
applied to every node pair, period and valuation — on a toy with domestic, cross-region
(tradable use) and system-boundary edges.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from pysuto.acc import AccountingStructure


SPEC = {
    "sectors": [
        {"name": "Mining",   "entity": "Process"},
        {"name": "Ore",      "entity": "Flow"},
        {"name": "WR",       "entity": "SB",      "role": "secondary"},
        {"name": "Smelting", "entity": "Process"},
        {"name": "Metal",    "entity": "Flow"},
        {"name": "Slag",     "entity": "SB",      "role": "secondary"},
        {"name": "FU",       "entity": "SB",      "role": "final_demand"},
    ],
    "regions":    ["Montara", "Portua", "Isla"],
    "valuations": [{"name": "Mass", "role": "gross"}, {"name": "CC", "role": "content"}],
    "times":      ["2001", "2002"],
    "supply":     {"Mining": ["Ore", "WR"], "Smelting": ["Metal", "Slag"]},
    "use":        {"Ore": ["Smelting"], "Metal": ["FU", "Smelting"]},
    "tradable":   ["Ore"],
    "accounting": [
        {"from": "Process", "to": "Flow",    "same_region": True},
        {"from": "Process", "to": "SB",      "same_region": True},
        {"from": "Flow",    "to": "Process", "same_region": False},
        {"from": "Flow",    "to": "SB",      "same_region": False},
    ],
}


def _loop_reference(acc: AccountingStructure) -> tuple:
    """The node pairs and edges the node-pair loops admit, in their order."""
    keys  = list(acc.id_to_node.values())
    nodes = [dict(zip(["sector", "entity", "region"], k)) for k in keys]
    node_pairs, edges = [], []
    for i, ni in enumerate(nodes):
        for j, nj in enumerate(nodes):
            if not acc._node_pair_admissible(ni, nj):
                continue
            node_pairs.append((i, j))
            for t_idx, t in enumerate(acc.time_range):
                for v_idx, v in enumerate(acc.valuation):
                    if acc._edge_admissible(ni, nj, t, v):
                        edges.append((i, j, t_idx, v_idx, t, v))
    return node_pairs, edges


@pytest.fixture(scope="module")
def acc():
    return AccountingStructure.from_spec(copy.deepcopy(SPEC), "toy")


def test_the_edge_index_is_the_loops_edge_index(acc):
    _, edges = _loop_reference(acc)
    expected = pd.DataFrame({
        "edge_id":   np.arange(len(edges), dtype=np.int64),
        "from_id":   np.array([e[0] for e in edges], dtype=np.int64),
        "to_id":     np.array([e[1] for e in edges], dtype=np.int64),
        "time":      [e[4] for e in edges],
        "valuation": [e[5] for e in edges],
    })
    pd.testing.assert_frame_equal(acc.edge_index, expected, check_dtype=False)
    assert acc.n_edges == len(edges)


def test_the_tensor_holds_the_loops_edges_in_edge_id_order(acc):
    _, edges = _loop_reference(acc)
    expected = np.array([e[:4] for e in edges], dtype=np.int64).T
    np.testing.assert_array_equal(acc.A.coords, expected)
    assert acc.A.nnz == acc.n_edges


def test_the_node_mask_is_the_loops_node_mask(acc):
    node_pairs, _ = _loop_reference(acc)
    got = sorted(zip(*acc.A_nodes.nonzero()))
    assert got == sorted(node_pairs)


def test_cross_region_edges_are_the_tradable_use_edges_only(acc):
    ei = acc.edge_index
    region = acc.node_index["region"].to_numpy()
    sector = acc.node_index["sector"].to_numpy()
    cross = region[ei["from_id"]] != region[ei["to_id"]]
    pairs = set(zip(sector[ei["from_id"][cross]], sector[ei["to_id"][cross]]))
    assert pairs == {("Ore", "Smelting")}
    # 3 × 3 region pairs for Ore → Smelting, 3 for every other pair, × 2 periods × 2 valuations
    n_pairs = sum(len(v) for v in SPEC["supply"].values()) + sum(len(v) for v in SPEC["use"].values())
    assert acc.n_edges == (9 + 3 * (n_pairs - 1)) * 2 * 2


def test_every_node_pair_is_counted_without_being_listed(acc):
    assert acc.n_edges_all == acc.n_nodes ** 2 * 2 * 2
    assert "edge_index_all" not in acc.__dict__          # built on demand only
    full = acc.edge_index_all
    assert len(full) == acc.n_edges_all
    np.testing.assert_array_equal(full["edge_id"].to_numpy(), np.arange(acc.n_edges_all))
    first = full.iloc[: 2 * 2]
    assert list(first["to_id"]) == [0] * 4 and list(first["time"]) == ["2001", "2001", "2002", "2002"]


def test_save_and_load_keep_the_structure_without_the_full_edge_list(acc, tmp_path):
    acc.storage_dir = str(tmp_path)
    acc.save()
    assert not (tmp_path / "toy" / "edge_index_all.csv").exists()
    loaded = AccountingStructure.load("toy", storage_dir=str(tmp_path))
    assert loaded.n_edges_all == acc.n_edges_all
    pd.testing.assert_frame_equal(loaded.edge_index, acc.edge_index, check_dtype=False)
    assert len(loaded.edge_index_all) == acc.n_edges_all

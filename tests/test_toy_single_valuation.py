"""
test_toy_single_valuation.py
============================
A structure with one valuation (ADR 0034 amendment): the toy case run through all six
stages with only its ``Gross`` valuation. The structure binds ``Gross`` to both roles, the
synthetic feeds keep their ``Gross`` rows, and the params rows that name ``Content`` match
no edge. The checks: every year solves, the hard rows close, and the PSUT built with
``primary="Gross"`` balances per node.
"""

from __future__ import annotations

import numpy as np
import pytest

from pysuto.acc import AccountingStructure, ValuationRoles
from pysuto.psut import PSUT
from pysuto.registry import ConstraintRunRegistry, OptimRunRegistry
from pysuto.tutorial import toy

from test_toy_case import _node_balance


def _gross_only(make_feeds):
    """``make_feeds`` with each feed cut to its ``Gross`` rows; a feed left empty is
    dropped."""
    def make(*args, **kwargs):
        out = {}
        for feed_id, feed in make_feeds(*args, **kwargs).items():
            vmap  = feed.maps["valuation_map_df"]
            units = set(vmap.loc[vmap["root_valuation"].eq(toy.GROSS), "src_valuation"])
            raw   = feed.raw[feed.raw["Unit"].isin(units)].reset_index(drop=True)
            if raw.empty:
                continue
            feed.raw = raw
            feed.maps["valuation_map_df"] = vmap[vmap["root_valuation"].eq(toy.GROSS)]
            out[feed_id] = feed
        return out
    return make


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """Stages 1-5 of the toy case with one valuation, and its PSUT in ``Gross``."""
    root = tmp_path_factory.mktemp("toy_gross")
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(toy.ACC_SPEC, "valuations",
                   [v for v in toy.ACC_SPEC["valuations"] if v["name"] == toy.GROSS])
        mp.setattr(toy, "make_feeds", _gross_only(toy.make_feeds))
        ids = {"feed": toy.run_stage1(root)}
        ids["imp"]     = toy.run_stage2(root, ids["feed"])
        ids["const"]   = toy.run_stage3(root, ids["imp"])
        ids["opt"]     = toy.run_stage4(root, ids["const"])
        ids["uncprop"] = toy.run_stage5(root, ids["opt"])
        tree = toy._tree(root)
        psut = PSUT.from_opt_run(ids["opt"], primary=toy.GROSS, opt_dir=str(tree["opt"]),
                                 const_dir=str(tree["const"]), acc_dir=str(tree["acc"]))
        acc  = AccountingStructure.load(toy.ACC_ID, storage_dir=str(root / "proc" / "acc"))
    return {"root": root, "ids": ids, "psut": psut, "acc": acc}


def test_the_structure_has_one_valuation_bound_to_both_roles(chain):
    acc = chain["acc"]
    assert acc.valuation == [toy.GROSS]
    assert acc.valuation_roles == ValuationRoles(content=toy.GROSS, gross=toy.GROSS)
    assert acc.n_edges == 210                    # half of the two-valuation toy's 420


def test_every_year_solves_and_every_hard_row_closes_to_1e_10(chain):
    root, ids = chain["root"], chain["ids"]
    const = ConstraintRunRegistry(str(root / "proc" / "const")).load(ids["const"])
    hard  = const.row_meta["is_hard"].to_numpy().astype(bool)
    assert hard.sum() > 0
    results = OptimRunRegistry(str(root / "proc" / "opt")).load(ids["opt"])
    assert sorted(results) == list(toy.YEARS)
    for t, res in results.items():
        assert res.solver_status == "solved"
        assert np.abs(res.residuals[hard[res.rows_t]]).max() <= 1e-10, t


def test_the_gross_psut_balances_per_node(chain):
    psut, acc = chain["psut"], chain["acc"]
    table  = psut.table
    assert set(table["valuation"]) == {toy.GROSS}
    scoped = table[acc.masks["massbal_scope"][table["edge_id"].to_numpy()]]
    nodes  = _node_balance(scoped.rename(columns={"period": "time"}), "val")
    assert len(nodes) == 90                      # 6 sectors × 3 regions × 5 years
    np.testing.assert_allclose(nodes["inflow"], nodes["outflow"], rtol=0.0, atol=1e-8)

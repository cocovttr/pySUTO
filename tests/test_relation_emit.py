"""
test_relation_emit.py
=====================
A :class:`~pysuto.relation.relation.Relation` is one object; ``emit`` turns it into rows of
a ``ConstraintBlock`` (G row, c, σ_c, ``constraint_id``, ``row_meta``).
"""

from __future__ import annotations

import numpy as np
import pytest

from pysuto.constraints.emit import emit, ratio_scale_index, ratio_sigma_c
from pysuto.constraints.naming import ROW_META_COLS
from pysuto.constraints.sum import SIGMA_C_INACTIVE
from pysuto.relation.relation import Relation


def _balance(hard: bool = True, sigma: float = 0.0) -> Relation:
    return Relation(
        edges        = np.array([3, 1, 7], dtype=np.int64),
        coefficients = np.array([1.0, 1.0, -1.0]),
        type         = "massbal",
        variant      = "massbal",
        specs        = ("Ore", "A", "Mass"),
        time         = "2020",
        valuation    = "Mass",
        rhs          = 0.0,
        sense        = "eq",
        hard         = hard,
        sigma        = sigma,
        meta         = {"sector": "Ore", "region": "A", "entity": "Flow"},
    )


def _ratio(r: float, sigma_r: float, time: str = "2020") -> Relation:
    return Relation(
        edges        = np.array([5, 2], dtype=np.int64),
        coefficients = np.array([1.0, -r]),
        type         = "ratio",
        variant      = "conc",
        specs        = ("a.A-b.A", "c.A-d.A", "Mass", "Mass"),
        time         = time,
        valuation    = "Mass",
        hard         = False,
        sigma        = sigma_r,
        n_num        = 1,
    )


class TestEmit:

    def test_relation_emits_row_c_sigma_and_id(self):
        block = emit([_balance()], n_edges=10)
        assert block.G_rows.shape == (1, 10)
        row = block.G_rows.toarray()[0]
        np.testing.assert_array_equal(row[[1, 3, 7]], [1.0, 1.0, -1.0])
        assert block.G_rows.nnz == 3
        assert block.c.tolist() == [0.0]
        assert block.sigma_c.tolist() == [0.0]
        rm = block.row_meta
        assert list(rm.columns) == ROW_META_COLS
        assert rm.loc[0, "constraint_id"] == "massbal_massbal_Ore_A_Mass_2020"
        assert rm.loc[0, "type"] == "massbal"
        assert bool(rm.loc[0, "is_hard"]) and rm.loc[0, "sense"] == "eq"
        assert rm.loc[0, "time"] == "2020" and rm.loc[0, "valuation"] == "Mass"
        assert rm.loc[0, "entity"] == "Flow" and rm.loc[0, "entity_sub"] is None

    def test_soft_row_carries_sigma_and_rhs(self):
        rel = _balance(hard=False, sigma=2.5)
        rel.rhs = 4.0
        block = emit([rel], n_edges=10)
        assert block.c.tolist() == [4.0] and block.sigma_c.tolist() == [2.5]
        assert not bool(block.row_meta.loc[0, "is_hard"])

    def test_hard_row_has_zero_sigma_whatever_sigma_says(self):
        block = emit([_balance(hard=True, sigma=9.0)], n_edges=10)
        assert block.sigma_c.tolist() == [0.0]

    def test_le_sense_is_carried_to_row_meta(self):
        rel = _balance()
        rel.sense = "le"
        assert emit([rel], n_edges=10).row_meta.loc[0, "sense"] == "le"

    def test_empty_is_an_empty_block(self):
        block = emit([], n_edges=10)
        assert block.G_rows.shape == (0, 10)
        assert list(block.row_meta.columns) == ROW_META_COLS

    def test_row_order_follows_relation_order(self):
        block = emit([_ratio(0.5, 0.1, "2021"), _ratio(0.5, 0.1, "2020")], n_edges=10)
        assert block.row_meta["time"].tolist() == ["2021", "2020"]

    def test_unknown_sense_raises(self):
        rel = _balance()
        rel.sense = "ge"
        with pytest.raises(ValueError):
            emit([rel], n_edges=10)


class TestRatioSigma:

    def test_symmetric_scale_and_year_deactivation(self):
        rels = [_ratio(0.5, 0.1), _ratio(0.5, 0.1, "2021")]
        static = emit(rels, n_edges=10)
        f = np.zeros(10)
        f[5], f[2] = 3.0, 10.0            # numerator 3, r·denominator 5 -> scale 5
        sig = ratio_sigma_c(ratio_scale_index(rels), static, f, "2020",
                            sigma_rel_floor=0.02, scale_abs_floor=1.0)
        assert sig[0] == pytest.approx(0.1 * 5.0, rel=1e-12)
        assert sig[1] == SIGMA_C_INACTIVE

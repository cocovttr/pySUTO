"""
mass_balance.py
===============
``MassBalanceBuilder`` — Type-1 hard equality rows: Σ inflows − Σ outflows = 0
per (balanced node × timestep). The rows are :class:`~pysuto.relation.relation.Relation`
objects built from :func:`pysuto.relation.structure.node_balances` and emitted by
:func:`pysuto.constraints.emit.emit`.
"""

from __future__ import annotations

import numpy as np

from pysuto.logging import get_logger
from pysuto.relation.relation import Relation
from pysuto.relation.structure import node_balances

from .base import BaseConstraintBuilder, ConstraintBlock
from .emit import emit
from .naming import TYPE_MASSBAL

_log = get_logger(__name__)


class MassBalanceBuilder(BaseConstraintBuilder):
    """
    Hard zero-cone constraint: Σ supply_edges − Σ use_edges = 0
    for every (Flow | Process) node that has ≥1 supply edge AND ≥1 use edge,
    per timestep.

    SB nodes are open-boundary endpoints and are excluded.
    G is time-invariant: one row per (balanced_node, time) pair.
    """

    def __init__(self, mask: str | None = None):
        """
        Parameters
        ----------
        mask : str | None
            If set, restrict mass-balance summation to edges where
            ``acc_struct.masks[mask] == True``. Nodes that no longer have at
            least one incoming AND one outgoing in-scope edge are skipped.
            Raises ``ValueError`` at build time if the mask is not present
            in ``acc_struct.masks``.
        """
        self._mask_name = mask

    def build_static(self, acc_struct) -> ConstraintBlock:
        n_edges  = acc_struct.n_edges
        node_idx = acc_struct.node_index

        if self._mask_name is not None:
            if self._mask_name not in acc_struct.masks:
                raise ValueError(
                    f"MassBalanceBuilder(mask={self._mask_name!r}): "
                    f"mask not in acc_struct.masks. "
                    f"Available: {sorted(acc_struct.masks)}"
                )
            scope_mask = acc_struct.masks[self._mask_name]
        else:
            scope_mask = np.ones(n_edges, dtype=bool)

        # One relation per (time, valuation, node). Splitting by valuation keeps each
        # emitted row unit-coherent (no Mass+CC mixing in G). ``node_balances`` sorts by
        # (node, time), so regroup by time in the structure's period order, nodes
        # ascending within a period.
        by_valuation = {}
        for valuation in acc_struct.valuation:
            by_time = {}
            for bal in node_balances(acc_struct, valuation):
                by_time.setdefault(bal.time, []).append(bal)
            by_valuation[valuation] = by_time

        relations = []
        for time in acc_struct.time_range:
            for valuation in acc_struct.valuation:
                for bal in by_valuation[valuation].get(str(time), ()):
                    inc = [e for e in bal.incoming if scope_mask[e]]
                    out = [e for e in bal.outgoing if scope_mask[e]]
                    if not inc or not out:
                        continue
                    n_row  = node_idx.loc[bal.node_id]
                    sector = str(n_row["sector"])
                    region = str(n_row["region"])
                    relations.append(Relation(
                        edges        = np.array(inc + out, dtype=np.int64),
                        coefficients = np.array([1.0] * len(inc) + [-1.0] * len(out)),
                        type         = TYPE_MASSBAL,
                        variant      = "massbal",
                        specs        = (sector, region, valuation),
                        time         = str(time),
                        valuation    = valuation,
                        meta         = {
                            "sector":     sector,
                            "region":     region,
                            "entity":     str(n_row["entity"]),
                            "entity_sub": (str(n_row.get("entity_sub", ""))
                                           if "entity_sub" in node_idx.columns else None),
                        },
                        source       = "massbal",
                    ))

        _log.info("MassBalanceBuilder.build_static: %d rows", len(relations))
        return emit(relations, n_edges)


# =============================================================================
# SumConstraintBuilder
# =============================================================================

"""
balance.py
==========
Node balances as :class:`~pysuto.relation.relation.Relation` objects — the one source of
a Flow / Process node's conservation row, read by Stage 3 (``MassBalanceBuilder``, which
emits them hard into ``G``) and by the NetworkImputer (which solves each for a lone
unknown, :func:`pysuto.relation.prior.solve_lone_unknown`).

Public API
----------
node_balance_relations(acc, valuation, scope_mask, entities)   One relation per node-period
"""

from __future__ import annotations

import numpy as np

from .relation import TYPE_MASSBAL, Relation
from .structure import node_balances


def node_balance_relations(acc, valuation: str, scope_mask=None,
                           entities=None) -> list[Relation]:
    """Σ incoming − Σ outgoing = 0 of every node-period of ``valuation``.

    One relation per :func:`~pysuto.relation.structure.node_balances` entry, in its
    ``(node, time)`` order: incoming edges first at ``+1``, outgoing at ``−1``, hard,
    ``type = "massbal"``, the node's ``sector`` / ``region`` / ``entity`` /
    ``entity_sub`` in ``meta``. ``scope_mask`` (bool per edge) keeps only the edges
    inside it and drops a node left without an incoming or an outgoing edge;
    ``entities`` (e.g. ``{"Flow"}``) keeps only nodes of those entity kinds.
    """
    node_idx = acc.node_index
    relations = []
    for bal in node_balances(acc, valuation):
        if entities is not None and bal.entity not in entities:
            continue
        if scope_mask is None:
            inc, out = list(bal.incoming), list(bal.outgoing)
        else:
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
            time         = str(bal.time),
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
    return relations

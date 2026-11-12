"""
toy_coproduct.py
================
The **toy case with a co-product** (#130, #26 §2 item 5): the toy world of
:mod:`pysuto.cases.toy`, plus a second content-bearing Flow out of the smelter.

Smelting now supplies ``Metal``, ``Dust`` and ``Slag``. ``Dust`` is a Flow product, a
fume-capture by-product at grade 0.20 that a ``Use`` edge consumes, so the smelter has two
products and its recovery closes by their sum, ``Σ (Metal + Dust) = eff · Σ inputs``, the
pooled ``agg`` row ``effsmelting`` (product ``*``, every Flow output of Smelting). The
truth keeps the toy's 0.97 pooled recovery and puts a quarter of the product content in
the dust.

What the case exercises: the Bureau reports ``Metal`` and never ``Dust``, so in a
published region-year ``NetworkImputer`` finds exactly one unknown product and fills it as
the sum's remainder (``network_forward``); in the two region-years the Bureau did not
publish both products are unknown and stay NaN for the time and flat-prior fillers, as
ADR 0004's rejected option E (a fabricated split) would otherwise have to invent one.
Stage 3's agg eff row pools both products.

Run it as ``python -m pysuto run --case toy_coproduct --data-dir <dir>``; the module is
the toy's with ``coproduct=True``: ``CASE`` is :data:`pysuto.cases.toy.CASE` under another
id and acc id, and the Stage 1 hook of the toy's generator.
"""

from __future__ import annotations

from dataclasses import replace

from pysuto.cases import toy

CASE = replace(
    toy.CASE,
    id     = "toy_coproduct",
    acc_id = toy.ACC_ID_COPRODUCT,
    stage1 = lambda data_dir: toy.run_stage1(data_dir, coproduct=True),
)

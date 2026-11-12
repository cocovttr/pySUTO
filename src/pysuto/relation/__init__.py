"""
relation
========
Params-driven relations between edge sets (ADR 0011).

* :mod:`pysuto.relation.params`         — the one params reader: typed :class:`ParamRow`
                                          records, each consumer's declared ``param_type`` set.
* :mod:`pysuto.relation.param_relation` — the A→B edge resolver over an accounting structure.
* :mod:`pysuto.relation.relation`       — the :class:`Relation` record: edges, coefficients, sense, σ.

Import direction: ``acc → relation → impute → constraints``.
"""

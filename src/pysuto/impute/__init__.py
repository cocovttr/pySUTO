"""
impute — Stage 2c imputation pipeline.

Public surface (re-exported here so call sites can keep using
``from pysuto.impute import X``):

* :class:`BaseImputer`         — abstract base
* :class:`ImputationEngine`    — orchestrator
* :class:`ImputationLog`       — per-edge fill provenance table
* :class:`ImputationMetadata`  — run-level per-step summary
* :class:`PriorLedger`         — the one write path: no-overwrite + writer scope
* :class:`ScopeError`          — raised on an out-of-scope write under ``strict_scope``

Imputers (run order is up to the engine's registration sequence):
* :class:`FillImputer`         — one fill rule of the params relation source (trade seed,
                                 conc, ore grade)
* :class:`NetworkImputer`      — process-recipe traversal (mass closure on CC)
* :class:`ParametricImputer`   — CSV bidirectional pairs + λ directed relations
* :class:`FormulaImputer`      — multi-source balance equations
* :class:`TimeImputer`         — temporal interpolation / extrapolation
* :class:`FlatPriorImputer`    — final fallback (f=0, large σ)

Supporting dataclasses (used in :class:`ParametricImputer` /
:class:`FormulaImputer` constructors):
* :class:`ParametricRelation`, :class:`FormulaRelation`, :class:`ParamRef`,
  :class:`SourceTerm`
"""

from .base       import BaseImputer
from .engine     import ImputationEngine, ImputationLog, ImputationMetadata
from .ledger     import PriorLedger, ScopeError, run_imputer
from .parametric import ParametricImputer, ParametricRelation, _reg_sensitivity
from .formula    import FormulaImputer, FormulaRelation, ParamRef, SourceTerm
from .network    import NetworkImputer
from .fill       import FillImputer
from .time       import TimeImputer, time_interp_scope
from .screens    import damp_leg_sigma, screen_contradicted_nodes, screen_outlier_trade_legs
from .share      import ShareImputer, StockLeg
from .flat_prior import FlatPriorImputer

__all__ = [
    "BaseImputer",
    "ImputationEngine",
    "ImputationLog",
    "ImputationMetadata",
    "PriorLedger",
    "ScopeError",
    "run_imputer",
    "FillImputer",
    "NetworkImputer",
    "ParametricImputer",
    "ParametricRelation",
    "FormulaImputer",
    "FormulaRelation",
    "ParamRef",
    "SourceTerm",
    "TimeImputer",
    "ShareImputer",
    "StockLeg",
    "FlatPriorImputer",
    "time_interp_scope",
    "damp_leg_sigma",
    "screen_outlier_trade_legs",
    "screen_contradicted_nodes",
    "_reg_sensitivity",
]

"""
params.py
=========
The one reader of the params-template CSVs: typed rows, one parsing policy.

A params file states relations between an A edge set and a B edge set (ADR 0005):
selectors, a nominal value, an uncertainty rule. Every consumer used to read the
file its own way (five parsing policies, four swallowing excepts); now each declares
the ``param_type`` values it accepts and reads through :func:`read_params`, which
returns :class:`ParamRow` records. A row outside ``accepts`` is filtered and counted
in the log; a malformed accepted row raises.

Public API
----------
WILDCARD, A_FIELDS, B_FIELDS, SELECTOR_KEYS    Column schema constants
ParamRow                                       One typed params row
read_params(path, accepts)                     The reader
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from pysuto.logging import get_logger
from pysuto.unc import PedigreeScores

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Column schema
# ---------------------------------------------------------------------------

WILDCARD = {"*", "nan", "None", ""}

# A-selector field → (ei_exp column, counterpart column for "same" constraint)
A_FIELDS = [
    ("a_sector_from", "sector_from", "sector_to"),
    ("a_entity_from", "entity_from", "entity_to"),
    ("a_region_from", "region_from", "region_to"),
    ("a_sector_to",   "sector_to",   "sector_from"),
    ("a_entity_to",   "entity_to",   "entity_from"),
    ("a_region_to",   "region_to",   "region_from"),
    ("a_time",        "time",        None),
    ("a_valuation",   "valuation",   None),
]

# B-selector field → (ei_exp column, corresponding A-edge column for "same")
B_FIELDS = [
    ("b_sector_from", "sector_from", "sector_from"),
    ("b_entity_from", "entity_from", "entity_from"),
    ("b_region_from", "region_from", "region_from"),
    ("b_sector_to",   "sector_to",   "sector_to"),
    ("b_entity_to",   "entity_to",   "entity_to"),
    ("b_region_to",   "region_to",   "region_to"),
    ("b_time",        "time",        "time"),
    ("b_valuation",   "valuation",   "valuation"),
]

SELECTOR_KEYS = tuple(k for k, _, _ in A_FIELDS) + tuple(k for k, _, _ in B_FIELDS)

_A_SPEC_KEYS = tuple(k for k, _, _ in A_FIELDS)
_AGG_TRUE    = {"true", "1", "yes", "y", "t"}

# unc_type → the value columns its σ rule reads
_SIGMA_RULES = ("sd", "min_max", "pedigree")
_PEDIGREE_COLS = (
    "pedigree_reliability", "pedigree_completeness", "pedigree_temporal_correlation",
    "pedigree_geographical_correlation", "pedigree_other_correlation",
)


def _wildcards() -> dict:
    return dict.fromkeys(SELECTOR_KEYS, "*")


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParamRow:
    """One row of a params file, typed.

    selectors      All 16 ``a_*`` / ``b_*`` cells, stripped; a blank or ``nan`` cell
                   is the wildcard ``"*"``. ``"same"`` is kept as written.
    value_nominal  The ratio / concentration / efficiency; NaN where the cell is blank.
    value_sd, value_min, value_max
                   NaN where blank.
    epsilon        Relative model uncertainty; 0.0 where blank.
    pedigree       The five pedigree scores when ``unc_type == "pedigree"``, else ``None``.
    unc_type       ``"sd"``, ``"min_max"``, ``"pedigree"`` or ``""`` (no σ rule).
    agg            ``agg`` cell as a bool (a pooled, set-scoped relation).
    """

    param_id:      str   = ""
    param_type:    str   = ""
    agg:           bool  = False
    description:   str   = ""
    selectors:     dict  = field(default_factory=_wildcards)
    value_nominal: float = np.nan
    unc_type:      str   = ""
    value_sd:      float = np.nan
    value_min:     float = np.nan
    value_max:     float = np.nan
    pedigree:      "tuple | None" = None
    epsilon:       float = 0.0

    @property
    def specificity(self) -> int:
        """Count of A-selector fields that are not wildcards (higher = more specific)."""
        return sum(self.selectors[k] not in WILDCARD for k in _A_SPEC_KEYS)

    def require_nominal(self) -> float:
        """``value_nominal``, or ``ValueError`` where the cell is blank."""
        if np.isnan(self.value_nominal):
            raise ValueError(f"param {self.param_id!r}: value_nominal is empty")
        return self.value_nominal

    def sigma(self) -> float:
        """σ in the units of ``value_nominal`` (ratio units for a ratio).

        ``sd`` → ``value_sd``; ``min_max`` → ``(value_max − value_min) / 4``;
        ``pedigree`` → ``value_nominal · PedigreeScores(...).total_cv()`` (Laner et al.
        2016). Raises ``ValueError`` on a row with no σ rule (``unc_type`` empty).
        """
        if self.unc_type == "sd":
            return self.value_sd
        if self.unc_type == "min_max":
            return (self.value_max - self.value_min) / 4.0
        if self.unc_type == "pedigree":
            ps = PedigreeScores(*self.pedigree)
            return ps.total_cv() * self.value_nominal
        raise ValueError(
            f"param {self.param_id!r} ({self.param_type}): no σ rule — unc_type is empty"
        )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _text(cell) -> str:
    """A cell as stripped text; a blank / NaN cell is ``""``."""
    s = str(cell).strip()
    return "" if s in ("nan", "None") else s


def _number(cell, column: str, param_id: str, default: float = np.nan) -> float:
    """A numeric cell; ``default`` where it is blank or a wildcard. Raises otherwise."""
    s = str(cell).strip()
    if not s or s in WILDCARD:
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(
            f"param {param_id!r}: {column} = {s!r} is not a number"
        ) from None


def _parse_row(rec: dict) -> ParamRow:
    pid = _text(rec.get("param_id", ""))
    selectors = {}
    for k in SELECTOR_KEYS:
        v = str(rec.get(k, "*")).strip()
        selectors[k] = "*" if v in WILDCARD else v

    unc = str(rec.get("unc_type", "")).strip()
    unc = "" if unc in WILDCARD else unc
    nominal = _number(rec.get("value_nominal", ""), "value_nominal", pid)
    sd      = _number(rec.get("value_sd", ""),      "value_sd",      pid)
    vmin    = _number(rec.get("value_min", ""),     "value_min",     pid)
    vmax    = _number(rec.get("value_max", ""),     "value_max",     pid)
    eps     = _number(rec.get("epsilon", ""),       "epsilon",       pid, default=0.0)

    pedigree = None
    if unc == "sd":
        if np.isnan(sd):
            raise ValueError(f"param {pid!r}: unc_type 'sd' needs value_sd")
    elif unc == "min_max":
        if np.isnan(vmin) or np.isnan(vmax):
            raise ValueError(f"param {pid!r}: unc_type 'min_max' needs value_min and value_max")
    elif unc == "pedigree":
        if np.isnan(nominal):
            raise ValueError(f"param {pid!r}: unc_type 'pedigree' needs value_nominal")
        cells = [str(rec.get(c, "")).strip() for c in _PEDIGREE_COLS]
        try:
            pedigree = tuple(int(c) for c in cells)
        except ValueError:
            raise ValueError(
                f"param {pid!r}: pedigree scores {cells} are not five integers"
            ) from None
    elif unc:
        raise ValueError(
            f"param {pid!r}: unc_type {unc!r} is not one of {list(_SIGMA_RULES)}"
        )

    return ParamRow(
        param_id      = pid,
        param_type    = _text(rec.get("param_type", "")),
        agg           = str(rec.get("agg", "")).strip().lower() in _AGG_TRUE,
        description   = _text(rec.get("description", "")),
        selectors     = selectors,
        value_nominal = nominal,
        unc_type      = unc,
        value_sd      = sd,
        value_min     = vmin,
        value_max     = vmax,
        pedigree      = pedigree,
        epsilon       = eps,
    )


def read_params(path, accepts) -> list:
    """Read a params CSV into typed rows, keeping the ``param_type`` values in ``accepts``.

    The one parsing policy: delimiter sniffed (``;`` and ``,`` files alike), every cell
    read as text, ``#`` starts a comment, rows with a blank ``param_id`` are skipped.
    Rows whose ``param_type`` is not in ``accepts`` are dropped and counted in the log.
    A malformed accepted row raises ``ValueError`` — nothing is clipped, coerced or
    filled — as does a file without a ``param_id`` or ``param_type`` column.

    Parameters
    ----------
    path : str or Path
    accepts : collection of str
        The consumer's declared ``param_type`` values.

    Returns
    -------
    list of ParamRow, in file order.
    """
    df = pd.read_csv(path, sep=None, engine="python", comment="#", dtype=str)
    for col in ("param_id", "param_type"):
        if col not in df.columns:
            raise ValueError(f"params file {path}: no {col!r} column")
    df = df.dropna(subset=["param_id"])
    accepts = set(accepts)

    rows, filtered = [], {}
    for rec in df.to_dict("records"):
        ptype = _text(rec["param_type"])
        if ptype not in accepts:
            filtered[ptype] = filtered.get(ptype, 0) + 1
            continue
        rows.append(_parse_row(rec))
    logger.info("read_params %s: %d rows accepted %s, %d filtered %s",
                path, len(rows), sorted(accepts), sum(filtered.values()),
                dict(sorted(filtered.items())))
    return rows

"""
qp.py
=====
The neutral QP of Stage 4 and the contract of a QP backend (ADR 0042).

The Stage-4 orchestrator (:class:`pysuto.solver.Solver`) owns the model: per period it
builds one standard-form QP over ``x = [a; ε]`` and hands it to a **QP backend**, which
knows nothing of edges, rows, σ or periods. Nothing here imports a numerical solver.

.. math::

    \\min_x \\; \\tfrac12 x^\\top P x + q^\\top x
    \\quad\\text{s.t.}\\quad A_{eq}\\,x = b_{eq},\\;\\; A_{le}\\,x \\le b_{le}

Public API
----------
- :class:`QPProblem` — one period's standard-form QP
- :class:`QPResult` — what a backend returns
- :class:`QPBackend` — ``solve(problem, reuse, verbose)``, ``name``, ``settings``
- :data:`SOLVED`, :data:`SOLVED_INACCURATE`, :data:`FAILED` — the neutral statuses
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np
import scipy.sparse as sp

# Neutral status of a solve. The orchestrator accepts the first two and raises on
# FAILED, quoting the backend's raw status.
SOLVED             = "solved"
SOLVED_INACCURATE  = "solved_inaccurate"
FAILED             = "failed"
STATUSES           = (SOLVED, SOLVED_INACCURATE, FAILED)


@dataclass
class QPProblem:
    """One period's QP over ``x = [a; ε]`` (``n_a`` flows, then ``n_eps`` slacks).

    ``P`` is sparse and symmetric (``n × n``, ``n = n_a + n_eps``); ``A_eq`` and
    ``A_le`` are sparse with ``n`` columns. Row order is the orchestrator's and is
    kept: soft rows (with their slack), hard equalities, then the ``≤`` rows.
    ``feasibility_only`` marks a probe, where only a yes/no answer is wanted and a
    backend may relax its tolerances.
    """
    P:      sp.spmatrix
    q:      np.ndarray
    A_eq:   sp.spmatrix
    b_eq:   np.ndarray
    A_le:   sp.spmatrix
    b_le:   np.ndarray
    n_a:    int
    n_eps:  int
    feasibility_only: bool = False

    @property
    def n(self) -> int:
        return self.n_a + self.n_eps


@dataclass
class QPResult:
    """A backend's answer. ``status`` is neutral; ``raw_status`` is the backend's own
    string. ``info`` (JSON-safe scalars) and ``iter_history`` (a structured array
    whose dtype the backend owns) are optional backend telemetry."""
    x:             np.ndarray
    status:        str
    raw_status:    str
    iterations:    int
    solve_time_s:  float
    objective:     float
    info:          Optional[dict]       = None
    iter_history:  Optional[np.ndarray] = None


class QPBackend(Protocol):
    """Solves a :class:`QPProblem`. ``name`` and ``settings`` (JSON-safe) are recorded
    in the opt sidecar. With ``reuse`` true a backend may continue from what it
    factorised on its previous call when the new problem has the same structure; with
    ``reuse`` false it starts afresh. Reuse is for one caller at a time, never for
    concurrent calls. ``verbose`` asks for the backend's own log of this solve."""

    name: str

    @property
    def settings(self) -> dict: ...

    def solve(self, problem: QPProblem, reuse: bool = False,
              verbose: bool = False) -> QPResult: ...

"""
cases
=====
Case modules (GLOSSARY.md "Case", #26 §3): ``pysuto.cases.<id>`` declares one metal's
case, wired through the six stages. A Stage 2 and 3 case is a
:class:`pysuto.case.CaseSpec` named ``CASE``.

* :mod:`pysuto.cases.copper` — the **copper case** (#120): the Stage 2 and 3 model of
  the copper application.
* :mod:`pysuto.cases.toy` — the **toy case** (#59): a synthetic three-region orium case
  generated from a planted ground truth.
* :mod:`pysuto.cases.toy_coproduct` — the toy whose smelter has a second Flow product
  (``Dust``), the co-product case (#130).

Import direction: ``cases`` sits at the top of the stack, beside the stage drivers and the
``python -m pysuto`` entry point. It imports the library; the library never imports it.
"""

from __future__ import annotations

import pkgutil

from pysuto.case import resolve_case


def case_ids() -> list:
    """The ids of the case modules of this package, sorted."""
    return sorted(m.name for m in pkgutil.iter_modules(__path__)
                  if not m.name.startswith("_"))


def load_case(case_id: str):
    """The :class:`pysuto.case.CaseSpec` ``--case <case_id>`` names, as
    :func:`pysuto.case.resolve_case` resolves it: a bundled alias, a dotted module or a
    file path.

    Raises
    ------
    ValueError
        Nothing of that name is found, or the module declares no ``CASE``.
    """
    return resolve_case(case_id)


def add_case_arg(parser) -> None:
    """Add ``--case <reference>`` (default ``copper``) to a stage driver's parser."""
    parser.add_argument("--case", default="copper",
                        help="Case: a bundled alias, a dotted module or a file path "
                             "(default copper).")


def case_from_args(parser, args):
    """The case ``--case`` names; an unknown reference ends the driver through
    ``parser.error`` (exit 2, naming what was tried)."""
    try:
        return load_case(args.case)
    except ValueError as exc:
        parser.error(str(exc))

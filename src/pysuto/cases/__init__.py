"""
cases
=====
Formerly the bundled case modules (GLOSSARY.md "Case", #26 §3). It declares no case any
more: pySUTO ships no study case (ADR 0047), the toy cases live in :mod:`pysuto.tutorial`
(#188) and copper is ``scripts/copper.py`` in the repository (#189). What is left are the
two helpers :func:`case_ids` and :func:`load_case`; #191 removes the package.

Import direction: ``cases`` sits at the top of the stack, beside the stage drivers and the
``python -m pysuto`` entry point. It imports the library; the library never imports it.
"""

from __future__ import annotations

from pysuto.case import ALIASES, resolve_case


def case_ids() -> list:
    """The bundled case aliases (:data:`pysuto.case.ALIASES`), sorted."""
    return sorted(ALIASES)


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


def add_case_arg(parser, default: str | None = None) -> None:
    """Add ``--case <reference>`` to a driver's parser: ``default`` is the case it runs
    without the option; ``None`` makes the option required, which
    :func:`case_from_args` enforces (exit 2, listing the aliases)."""
    parser.add_argument("--case", default=default, metavar="CASE",
                        help="Case: a bundled alias (" + ", ".join(sorted(ALIASES))
                             + "), a dotted module or a file path"
                             + (" (required)." if default is None
                                else f" (default {default})."))


def case_from_args(parser, args):
    """The case ``--case`` names; an unknown reference ends the driver through
    ``parser.error`` (exit 2, naming what was tried)."""
    if args.case is None:
        parser.error("--case is required: a bundled alias (" + ", ".join(sorted(ALIASES))
                     + "), a dotted module or a file path")
    try:
        return load_case(args.case)
    except ValueError as exc:
        parser.error(str(exc))

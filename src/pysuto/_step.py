"""
_step.py
========
The child of a pipeline step (#186): ``python -m pysuto._step <spec.json>`` runs one stage
of :mod:`pysuto.stages` on the case a reference names, then exits, so its memory returns
to the system (ADR 0045). Private: :class:`pysuto.pipeline.Pipeline` writes the spec and
launches it; nothing else calls it.

The spec is a JSON object::

    step, case, label, upstream, data_dir, config, dirs, knobs, run_id_file

``upstream`` is the feed run ids (``imp``), the imp, const or opt run id of the stage
before, or ``None`` (``feed``); ``dirs`` holds ``imp_dir`` and ``const_dir``; ``knobs``
are ``KNOB=VALUE`` literals, parsed and type-checked by :mod:`pysuto.knobs` against the
defaults of the stage. The run id (``feed``: the feed run ids, one per line) goes to
``run_id_file``.

Like :mod:`pysuto.__main__`, this module is at the top of the import stack: it resolves
the case reference with :func:`pysuto.cases.load_case`, which the library never imports.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace

from pysuto.cases import load_case
from pysuto.config import load_config
from pysuto.knobs import parse_overrides, write_run_id
from pysuto.stages import (OPT_KNOBS, opt_defaults, run_const, run_imp, run_opt,
                           run_psut, run_uncprop)


def resolve_case(reference: str):
    """The :class:`pysuto.case.CaseSpec` a ``--case`` reference names (an alias of
    :func:`pysuto.cases.load_case` today, #187)."""
    return load_case(reference)


def run_spec(spec: dict) -> str:
    """Run the step ``spec`` describes in this process; return its run id."""
    step, label, data_dir = spec["step"], spec["label"], spec["data_dir"]
    case = resolve_case(spec["case"])
    if step == "feed":
        return "\n".join(case.stage1(data_dir).values())
    if spec.get("config") is not None:
        case = replace(case, acc_id=load_config(spec["config"]).pipeline.acc_id)
    dirs, upstream, pairs = spec["dirs"], spec["upstream"], spec["knobs"]
    if step in ("imp", "const"):
        defaults = getattr(case, step).knobs()
        knobs = parse_overrides(pairs, tuple(defaults), defaults)
        case = case.with_knobs(step, knobs)
        stage = run_imp if step == "imp" else run_const
        return stage(case, upstream, label, knobs, data_dir=data_dir, **dirs)
    if step == "opt":
        knobs = parse_overrides(pairs, OPT_KNOBS, opt_defaults())
        return run_opt(case, upstream, label, knobs, data_dir=data_dir, **dirs)
    if pairs:
        raise KeyError(f"the {step} step takes no knobs, got {pairs}")
    stage = run_uncprop if step == "uncprop" else run_psut
    return stage(case, upstream, label, data_dir=data_dir)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m pysuto._step <spec.json>", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        spec = json.load(f)
    write_run_id(spec["run_id_file"], run_spec(spec))
    return 0


if __name__ == "__main__":
    sys.exit(main())

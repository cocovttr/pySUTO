"""
tutorial
========
The tutorial of pySUTO (#188): the toy case and the ten notebooks that run it through
the six stages. ``python -m pysuto tutorial [DEST]`` copies the notebooks out of the
installed package.

* :mod:`pysuto.tutorial.toy` — the **toy case** (#59): a synthetic three-region orium
  case generated from a planted ground truth; the alias ``toy``.
* :mod:`pysuto.tutorial.toy_coproduct` — the toy whose smelter has a second Flow product
  (``Dust``), the co-product case (#130); the alias ``toy_coproduct``.
* :mod:`pysuto.tutorial.toy_ext` — the extras of chapters ``08_break_it`` and
  ``09_bridge`` (#61).

Import direction: ``tutorial`` sits at the top of the stack, beside ``pysuto.cases``, the
stage drivers and the ``python -m pysuto`` entry point. It imports the library; the
library never imports it (:func:`pysuto.case.resolve_case` reaches the toy aliases only
by name, at call time).
"""

from __future__ import annotations

import shutil
from pathlib import Path

#: The notebooks and their README, which ship as package data beside this module.
PACKAGE_DIR = Path(__file__).resolve().parent


def copy_tutorial(dest) -> list:
    """Copy the ten notebooks and ``README.md`` into ``dest``, creating it.

    Parameters
    ----------
    dest : str or path-like
        A folder that does not exist or is empty; the copies are writable.

    Returns
    -------
    list of pathlib.Path
        The files written, sorted.

    Raises
    ------
    FileExistsError
        ``dest`` exists and is not an empty directory; nothing is written.
    """
    dest = Path(dest)
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise FileExistsError(f"{dest} exists and is not an empty directory")
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    for src in sorted(PACKAGE_DIR.glob("*.ipynb")) + [PACKAGE_DIR / "README.md"]:
        target = dest / src.name
        shutil.copyfile(src, target)
        target.chmod(0o644)
        out.append(target)
    return out

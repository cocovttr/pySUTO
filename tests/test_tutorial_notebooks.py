"""test_tutorial_notebooks.py
===========================
The shipped tutorial notebooks (``src/pysuto/tutorial/00..10``) obey the style sheet's
hard rules (#60, #191). The check is static: it reads each notebook's JSON and executes
nothing; the executed outputs are the business of ``scripts/refresh_tutorial.py`` (#188).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

import pysuto.tutorial

TUTORIAL = Path(pysuto.tutorial.__file__).resolve().parent
NOTEBOOKS = sorted(TUTORIAL.glob("[0-9][0-9]_*.ipynb"))
MAX_BODY = 5                                       # lines of a function body
ANSWER_HOOKS = ("truth", "reveal")                 # the answer key, from chapter 07 on
HOME_OR_TEMP = re.compile(r"/home/|/Users/|/tmp/|/var/folders/|[A-Za-z]:\\\\Users")
EXERCISE = re.compile(r"\*\*Exercise \d+\.\d+\*\*")


def _source(cell: dict) -> str:
    src = cell["source"]
    return src if isinstance(src, str) else "".join(src)


def _code(cell: dict):
    """The cell's Python as a tree, or ``None`` when it holds only magic."""
    lines = _source(cell).splitlines()
    lines = [("" if ln.lstrip().startswith(("%", "!")) else ln) for ln in lines]
    text = "\n".join(lines)
    return ast.parse(text) if text.strip() else None


def _calls(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            yield f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def violations(path: Path, chapter: int | None = None) -> list:
    """Every style-sheet rule the notebook at ``path`` breaks, one string each;
    ``chapter`` defaults to the file name's two-digit prefix."""
    nb = json.loads(path.read_text(encoding="utf-8"))
    chapter = int(path.name[:2]) if chapter is None else chapter
    found = []
    spec = nb["metadata"].get("kernelspec", {})
    if spec.get("name") != "python3":
        found.append(f"kernelspec is {spec.get('name')!r}, not 'python3'")
    cells = nb["cells"]
    for i, cell in enumerate(cells):
        text = _source(cell)
        if "HOOK NEEDED" in text:
            found.append(f"cell {i}: HOOK NEEDED")
        blobs = [text] + [json.dumps(o) for o in cell.get("outputs", [])]
        if any(HOME_OR_TEMP.search(b) for b in blobs):
            found.append(f"cell {i}: a home or temp path in the source or an output")
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                found.append(f"cell {i}: an error output ({out.get('ename')})")
        if cell["cell_type"] != "code":
            continue
        tree = _code(cell)
        if tree is None:
            continue
        for node in ast.walk(tree):
            mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                    else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            if any(m == "scripts" or m.startswith("scripts.") for m in mods):
                found.append(f"cell {i}: imports from scripts/")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                doc = body[0].value if isinstance(body[0], ast.Expr) else None
                if isinstance(doc, ast.Constant) and isinstance(doc.value, str):
                    body = body[1:]                 # the docstring is not body
                if body:
                    n = body[-1].end_lineno - body[0].lineno + 1
                    if n > MAX_BODY:
                        found.append(f"cell {i}: {node.name} has a {n}-line body")
        if chapter < 7 and any(c in ANSWER_HOOKS for c in _calls(tree)):
            found.append(f"cell {i}: calls the answer key before chapter 07")
    for i, cell in enumerate(cells):
        if cell["cell_type"] == "markdown" and EXERCISE.search(_source(cell)):
            run = []                        # the code cells up to the next markdown cell
            for nxt in cells[i + 1:]:
                if nxt["cell_type"] != "code":
                    break
                run.append(nxt)
            tree = _code(run[-1]) if run else None
            last = tree.body[-1] if tree is not None and tree.body else None
            names = list(_calls(last)) if last is not None else []
            if not any(n.startswith("check_") for n in names):
                found.append(f"cell {i}: the exercise ends in no check_* call")
    return found


def test_the_eleven_notebooks_are_found():
    assert [p.name[:2] for p in NOTEBOOKS] == [f"{n:02d}" for n in range(11)]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_a_shipped_notebook_obeys_the_style_sheet(path):
    assert violations(path) == []


def _planted(tmp_path, chapter_file: str, source: str, name: str = "00_planted.ipynb"):
    nb = json.loads((TUTORIAL / chapter_file).read_text(encoding="utf-8"))
    nb["cells"].append({"cell_type": "code", "metadata": {}, "execution_count": None,
                        "outputs": [], "source": source})
    out = tmp_path / name
    out.write_text(json.dumps(nb), encoding="utf-8")
    return out


def test_reveal_in_chapter_03_fails(tmp_path):
    path = _planted(tmp_path, "03_constraints.ipynb", "toy.reveal(RUNS)",
                    "03_planted.ipynb")
    assert any("answer key" in v for v in violations(path))
    assert violations(_planted(tmp_path, "07_scoreboard.ipynb", "toy.reveal(RUNS)",
                               "07_planted.ipynb")) == []


def test_a_home_path_fails(tmp_path):
    path = _planted(tmp_path, "00_world.ipynb", "print('/home/someone/runs')")
    assert any("home or temp path" in v for v in violations(path))


def test_a_long_function_and_a_scripts_import_fail(tmp_path):
    body = "def f(x):\n" + "".join(f"    x = x + {k}\n" for k in range(6))
    path = _planted(tmp_path, "00_world.ipynb", body + "    return x")
    assert any("body" in v for v in violations(path))
    assert any("scripts/" in v for v in violations(
        _planted(tmp_path, "00_world.ipynb", "from scripts import acc")))

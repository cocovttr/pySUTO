# pySUTO tutorial

Notebooks on the toy case of the fictional metal orium. Use the conda environment `pysuto` and its Jupyter kernel `pysuto`, open `00_world.ipynb`, and run the chapters in order, each top to bottom.
`runs/` is scratch: the chapters write their run trees there, it is gitignored, and you may delete it at any time.
`pyproject.toml` is not in the repository yet (it is gitignored; #118 adds it), so on a fresh clone `pip install -e .` fails: set `PYTHONPATH=<clone>/src` before starting Jupyter.

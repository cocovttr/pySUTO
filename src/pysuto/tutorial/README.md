# pySUTO tutorial

Notebooks on the toy case of the fictional metal orium. Install the tutorial extra, copy the notebooks out of the package into a folder of your own, open `00_world.ipynb` with the `python3` kernel, and run the chapters in order, each top to bottom:

```
pip install "pysuto[tutorial]"
plotly_get_chrome -y              # once: Kaleido draws the chapter-06 Sankeys with Chrome
python -m pysuto tutorial pysuto-tutorial
cd pysuto-tutorial && jupyter lab 00_world.ipynb
```

The eleven chapters, in order: `00_world` (the ground truth), `01_datafeed` to `06_psut_piot` (one per stage), `07_scoreboard` (the chain against the truth), `08_break_it` (three experiments), `09_bridge` (from the toy to copper and the three seams you extend) and `10_your_case`, which writes a minimal case of your own outside the package and runs it with `python -m pysuto run --case ./my_case.py`. The copy also holds `params_template.csv`, the schema of a parameters file, which chapter 10 builds on.

The toy case the notebooks run is Python source in the package: `python -c "import pysuto.tutorial.toy as t; print(t.__file__)"` prints where it lives.
`runs/` is scratch: the chapters write their run trees there, next to the notebooks, and you may delete it at any time.

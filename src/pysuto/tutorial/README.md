# pySUTO tutorial

Notebooks on the toy case of the fictional metal orium. Install the tutorial extra, copy the notebooks out of the package into a folder of your own, open `00_world.ipynb` with the `python3` kernel, and run the chapters in order, each top to bottom:

```
pip install "pysuto[tutorial]"
python -m pysuto tutorial pysuto-tutorial
cd pysuto-tutorial && jupyter lab 00_world.ipynb
```

`runs/` is scratch: the chapters write their run trees there, next to the notebooks, and you may delete it at any time.

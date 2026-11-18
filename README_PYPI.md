# pySUTO

pySUTO (Python-based Supply-Use Table Optimiser) reconciles supply-use tables from
conflicting sources. Each source datum carries an uncertainty; a sigma-weighted quadratic
programme, solved with Clarabel, returns the flows that agree with the accounting
constraints at the smallest weighted distance from the data, and the posterior uncertainty
of every flow. It is built for material flow analysis and was developed on copper.

```
pip install pysuto
pip install "pysuto[tutorial]"
pysuto tutorial DEST
```

The second line adds Jupyter and Plotly; `pysuto tutorial DEST` copies the tutorial
notebooks into the directory `DEST`. Without a Chrome browser, run `plotly_get_chrome -y`
once: Kaleido needs it to write the Sankey figures. Python 3.9 or newer is required.

Documentation, the method and the source are in the GitHub repository:
https://github.com/florihu/pySUTO
